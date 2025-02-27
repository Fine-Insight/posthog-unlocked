import json
import threading
import types
from contextlib import contextmanager
from functools import lru_cache
from time import perf_counter
from typing import Any, Dict, List, Optional, Sequence, Union

import posthoganalytics
import sqlparse
from clickhouse_driver import Client as SyncClient
from django.conf import settings as app_settings
from statshog.defaults.django import statsd

from posthog.clickhouse.client.connection import Workload, get_pool
from posthog.clickhouse.query_tagging import get_query_tag_value, get_query_tags
from posthog.errors import wrap_query_error
from posthog.settings import TEST
from posthog.utils import generate_short_id, patchable

InsertParams = Union[list, tuple, types.GeneratorType]
NonInsertParams = Dict[str, Any]
QueryArgs = Optional[Union[InsertParams, NonInsertParams]]

thread_local_storage = threading.local()

# As of CH 22.8 - more algorithms have been added on newer versions
CLICKHOUSE_SUPPORTED_JOIN_ALGORITHMS = [
    "default",
    "hash",
    "parallel_hash",
    "direct",
    "full_sorting_merge",
    "partial_merge",
    "auto",
]

is_invalid_algorithm = lambda algo: algo not in CLICKHOUSE_SUPPORTED_JOIN_ALGORITHMS


@lru_cache(maxsize=1)
def default_settings() -> Dict:
    from posthog.version_requirement import ServiceVersionRequirement

    # On CH 22.3 we need to disable optimize_move_to_prewhere due to a bug. This is verified fixed on 22.8 (LTS),
    # so we only disable on versions below that.
    # This is calculated once per deploy
    clickhouse_at_least_228, _ = ServiceVersionRequirement(
        service="clickhouse", supported_version=">=22.8.0"
    ).is_service_in_accepted_version()
    if clickhouse_at_least_228:
        return {}
    else:
        return {"optimize_move_to_prewhere": 0}


def extra_settings(query_id) -> Dict[str, Any]:
    join_algorithm = (
        posthoganalytics.get_feature_flag(
            "join-algorithm",
            str(query_id),
            only_evaluate_locally=True,
        )
        or "default"
    )

    # make sure the algorithm is supported - it's also possible to specify e.g. "algorithm1,algorithm2"
    if len(list(filter(is_invalid_algorithm, join_algorithm.split(",")))) > 0:
        join_algorithm = "default"

    return {"join_algorithm": join_algorithm}


def validated_client_query_id() -> Optional[str]:
    client_query_id = get_query_tag_value("client_query_id")
    client_query_team_id = get_query_tag_value("team_id")

    if client_query_id and not client_query_team_id:
        raise Exception("Query needs to have a team_id arg if you've passed client_query_id")
    random_id = generate_short_id()
    return f"{client_query_team_id}_{client_query_id}_{random_id}"


@patchable
def sync_execute(
    query,
    args=None,
    settings=None,
    with_column_types=False,
    flush=True,
    *,
    workload: Workload = Workload.ONLINE,
):
    if TEST and flush:
        try:
            from posthog.test.base import flush_persons_and_events

            flush_persons_and_events()
        except ModuleNotFoundError:  # when we run plugin server tests it tries to run above, ignore
            pass

    with get_pool(workload).get_client() as client:
        start_time = perf_counter()

        prepared_sql, prepared_args, tags = _prepare_query(client=client, query=query, args=args, workload=workload)

        query_id = validated_client_query_id()
        core_settings = {**default_settings(), **(settings or {}), **extra_settings(query_id)}
        tags["query_settings"] = core_settings
        settings = {**core_settings, "log_comment": json.dumps(tags, separators=(",", ":"))}
        try:
            result = client.execute(
                prepared_sql,
                params=prepared_args,
                settings=settings,
                with_column_types=with_column_types,
                query_id=query_id,
            )
        except Exception as err:
            err = wrap_query_error(err)
            statsd.incr("clickhouse_sync_execution_failure", tags={"failed": True, "reason": type(err).__name__})

            raise err
        finally:
            execution_time = perf_counter() - start_time

            statsd.timing("clickhouse_sync_execution_time", execution_time * 1000.0)

            if query_counter := getattr(thread_local_storage, "query_counter", None):
                query_counter.total_query_time += execution_time

            if app_settings.SHELL_PLUS_PRINT_SQL:
                print("Execution time: %.6fs" % (execution_time,))  # noqa T201
    return result


def query_with_columns(
    query: str,
    args: Optional[QueryArgs] = None,
    columns_to_remove: Optional[Sequence[str]] = None,
    columns_to_rename: Optional[Dict[str, str]] = None,
    *,
    workload: Workload = Workload.ONLINE,
) -> List[Dict]:
    if columns_to_remove is None:
        columns_to_remove = []
    if columns_to_rename is None:
        columns_to_rename = {}
    metrics, types = sync_execute(query, args, with_column_types=True, workload=workload)
    type_names = [key for key, _type in types]

    rows = []
    for row in metrics:
        result = {}
        for type_name, value in zip(type_names, row):
            if type_name not in columns_to_remove:
                result[columns_to_rename.get(type_name, type_name)] = value

        rows.append(result)

    return rows


@patchable
def _prepare_query(client: SyncClient, query: str, args: QueryArgs, workload: Workload = Workload.ONLINE):
    """
    Given a string query with placeholders we do one of two things:

        1. for a insert query we just format, and remove comments
        2. for non-insert queries, we return the sql with placeholders
        evaluated with the contents of `args`

    We also return `tags` which contains some detail around the context
    within which the query was executed e.g. the django view name

    NOTE: `client.execute` would normally handle substitution, but
    because we want to strip the comments to make it easier to copy
    and past queries from the `system.query_log` easily with metabase
    (metabase doesn't show new lines, so with comments, you can't get
    a working query without exporting to csv or similar), we need to
    do it manually.

    We only want to try to substitue for SELECT queries, which
    clickhouse_driver at this moment in time decides based on the
    below predicate.
    """
    prepared_args: Any = QueryArgs
    if isinstance(args, (list, tuple, types.GeneratorType)):
        # If we get one of these it means we have an insert, let the clickhouse
        # client handle substitution here.
        rendered_sql = query
        prepared_args = args
    elif not args:
        # If `args` is not truthy then make prepared_args `None`, which the
        # clickhouse client uses to signal no substitution is desired. Expected
        # args balue are `None` or `{}` for instance
        rendered_sql = query
        prepared_args = None
    else:
        # Else perform the substitution so we can perform operations on the raw
        # non-templated SQL
        rendered_sql = client.substitute_params(query, args)
        prepared_args = None

    formatted_sql = sqlparse.format(rendered_sql, strip_comments=True)
    annotated_sql, tags = _annotate_tagged_query(formatted_sql, workload)

    if app_settings.SHELL_PLUS_PRINT_SQL:
        print()  # noqa T201
        print(format_sql(formatted_sql))  # noqa T201

    return annotated_sql, prepared_args, tags


def _annotate_tagged_query(query, workload):
    """
    Adds in a /* */ so we can look in clickhouses `system.query_log`
    to easily marry up to the generating code.
    """
    tags = {**get_query_tags(), "workload": str(workload)}
    # Annotate the query with information on the request/task
    if "kind" in tags:
        user_id = f" user_id:{tags['user_id']}" if "user_id" in tags else ""
        query = f"/*{user_id} {tags.get('kind')}:{tags.get('id', '').replace('/', '_')} */ {query}"

    return query, tags


def format_sql(rendered_sql, colorize=True):
    formatted_sql = sqlparse.format(rendered_sql, reindent_aligned=True)
    if colorize:
        try:
            import pygments.formatters
            import pygments.lexers

            return pygments.highlight(
                formatted_sql, pygments.lexers.get_lexer_by_name("sql"), pygments.formatters.TerminalFormatter()
            )
        except:
            pass

    return formatted_sql


@contextmanager
def clickhouse_query_counter(query_counter):
    thread_local_storage.query_counter = query_counter
    yield
    thread_local_storage.query_counter = None
