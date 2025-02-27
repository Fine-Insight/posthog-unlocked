from posthog.settings.base_variables import TEST
from posthog.settings.utils import get_from_env, str_to_bool

USE_PRECALCULATED_CH_COHORT_PEOPLE = not TEST
CALCULATE_X_COHORTS_PARALLEL = get_from_env("CALCULATE_X_COHORTS_PARALLEL", 5, type_cast=int)

ACTION_EVENT_MAPPING_INTERVAL_SECONDS = get_from_env("ACTION_EVENT_MAPPING_INTERVAL_SECONDS", 300, type_cast=int)

ASYNC_EVENT_PROPERTY_USAGE = get_from_env("ASYNC_EVENT_PROPERTY_USAGE", True, type_cast=str_to_bool)
EVENT_PROPERTY_USAGE_INTERVAL_CRON = get_from_env(
    "ASYNC_EVENT_PROPERTY_USAGE_INTERVAL_CRON",
    "0 */6 * * *",
)

# Schedule to syncronize insight cache states on. Follows crontab syntax.
SYNC_INSIGHT_CACHE_STATES_SCHEDULE = get_from_env(
    "SYNC_INSIGHT_CACHE_STATES_SCHEDULE",
    # Defaults to 5AM UTC on Saturday
    "0 5 * * SAT",
)


UPDATE_CACHED_DASHBOARD_ITEMS_INTERVAL_SECONDS = get_from_env(
    "UPDATE_CACHED_DASHBOARD_ITEMS_INTERVAL_SECONDS", 90, type_cast=int
)

COUNT_TILES_WITH_NO_FILTERS_HASH_INTERVAL_SECONDS = get_from_env(
    "COUNT_TILES_WITH_NO_FILTERS_HASH_INTERVAL_SECONDS", 1800, type_cast=int
)

BILLING_USAGE_CACHING_TTL = get_from_env("BILLING_USAGE_CACHING_TTL", 12 * 60 * 60, type_cast=int)

CACHED_RESULTS_TTL = 7 * 24 * 60 * 60  # how long to keep cached results for
SESSION_RECORDING_TTL = 30  # how long to keep session recording cache. Relatively short because cached result is used throughout the duration a session recording loads.

# Schedule to run asynchronous data deletion on. Follows crontab syntax.
# Use empty string to prevent this
CLEAR_CLICKHOUSE_REMOVED_DATA_SCHEDULE_CRON = get_from_env(
    "CLEAR_CLICKHOUSE_REMOVED_DATA_SCHEDULE_CRON",
    # Defaults to 5AM UTC on Sunday
    "0 5 * * SUN",
)
