import json
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Optional,
    Tuple,
    TypedDict,
    Union,
)

import structlog
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models, transaction
from django.db.models.query import QuerySet
from django.db.models.query_utils import Q
from django.dispatch import receiver
from django.utils import timezone
from rest_framework import exceptions

from posthog.cloud_utils import is_cloud
from posthog.constants import MAX_SLUG_LENGTH, AvailableFeature
from posthog.email import is_email_available
from posthog.models.utils import LowercaseSlugField, UUIDModel, create_with_slug, sane_repr
from posthog.redis import get_client
from posthog.utils import absolute_uri

if TYPE_CHECKING:
    from posthog.models import Team, User


logger = structlog.get_logger(__name__)

INVITE_DAYS_VALIDITY = 3  # number of days for which team invites are valid


class OrganizationUsageInfo(TypedDict):
    usage: Optional[int]
    limit: Optional[int]


class OrganizationManager(models.Manager):
    def create(self, *args: Any, **kwargs: Any):
        return create_with_slug(super().create, *args, **kwargs)

    def bootstrap(
        self, user: Optional["User"], *, team_fields: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Tuple["Organization", Optional["OrganizationMembership"], "Team"]:
        """Instead of doing the legwork of creating an organization yourself, delegate the details with bootstrap."""
        from .team import Team  # Avoiding circular import

        with transaction.atomic():
            organization = Organization.objects.create(**kwargs)
            team = Team.objects.create(organization=organization, **(team_fields or {}))
            organization_membership: Optional[OrganizationMembership] = None
            if user is not None:
                organization_membership = OrganizationMembership.objects.create(
                    organization=organization, user=user, level=OrganizationMembership.Level.OWNER
                )
                user.current_organization = organization
                user.current_team = team
                user.save()

        return organization, organization_membership, team


class Organization(UUIDModel):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["for_internal_metrics"],
                condition=Q(for_internal_metrics=True),
                name="single_for_internal_metrics",
            )
        ]

    class PluginsAccessLevel(models.IntegerChoices):
        # None means the organization can't use plugins at all. They're hidden. Cloud default.
        NONE = 0, "none"
        # Config means the organization can only enable/disable/configure globally managed plugins.
        # This prevents config orgs from running untrusted code, which the next levels can do.
        CONFIG = 3, "config"
        # Install means the organization has config capabilities + can install own editor/GitHub/GitLab/npm plugins.
        # The plugin repository is off limits, as repository installations are managed by root orgs to avoid confusion.
        INSTALL = 6, "install"
        # Root means the organization has unrestricted plugins access on the instance. Self-hosted default.
        # This includes installing plugins from the repository and managing plugin installations for all other orgs.
        ROOT = 9, "root"

    members: models.ManyToManyField = models.ManyToManyField(
        "posthog.User",
        through="posthog.OrganizationMembership",
        related_name="organizations",
        related_query_name="organization",
    )
    name: models.CharField = models.CharField(max_length=64)
    slug: LowercaseSlugField = LowercaseSlugField(unique=True, max_length=MAX_SLUG_LENGTH)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
    plugins_access_level: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=PluginsAccessLevel.CONFIG,
        choices=PluginsAccessLevel.choices,
    )
    for_internal_metrics: models.BooleanField = models.BooleanField(default=False)
    is_member_join_email_enabled: models.BooleanField = models.BooleanField(default=True)

    # Managed by Billing
    customer_id: models.CharField = models.CharField(max_length=200, null=True, blank=True)
    available_features = ArrayField(models.CharField(max_length=64, blank=False), blank=True, default=list)
    # Managed by Billing, cached here for usage controls
    # Like {
    #   'events': { 'usage': 10000, 'limit': 20000 },
    #   'recordings': { 'usage': 10000, 'limit': 20000 }
    # }
    # Also currently indicates if the organization is on billing V2 or not
    usage: models.JSONField = models.JSONField(null=True, blank=True)

    # DEPRECATED attributes (should be removed on next major version)
    setup_section_2_completed: models.BooleanField = models.BooleanField(default=True)
    personalization: models.JSONField = models.JSONField(default=dict, null=False, blank=True)
    domain_whitelist: ArrayField = ArrayField(
        models.CharField(max_length=256, blank=False), blank=True, default=list
    )  # DEPRECATED in favor of `OrganizationDomain` model; previously used to allow self-serve account creation based on social login (#5111)

    objects: OrganizationManager = OrganizationManager()

    def __str__(self):
        return self.name

    __repr__ = sane_repr("name")

    @property
    def _billing_plan_details(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Obtains details on the billing plan for the organization.
        Returns a tuple with (billing_plan_key, billing_realm)
        """
        try:
            from ee.models.license import License
        except ImportError:
            License = None  # type: ignore
        # Demo gets all features
        if settings.DEMO or "generate_demo_data" in sys.argv[1:2]:
            return (License.ENTERPRISE_PLAN, "demo")
        # If on Cloud, grab the organization's price
        if hasattr(self, "billing"):
            if self.billing is None:  # type: ignore
                return (None, None)
            return (self.billing.get_plan_key(), "cloud")  # type: ignore
        # Otherwise, try to find a valid license on this instance
        if License is not None:
            license = License.objects.first_valid()
            if license:
                return (license.plan, "ee")
        return (None, None)

    @property
    def billing_plan(self) -> Optional[str]:
        return self._billing_plan_details[0]

    def update_available_features(self) -> List[Union[AvailableFeature, str]]:
        """Updates field `available_features`. Does not `save()`."""
        # TODO BW: Get available features from billing service

        if self.has_billing_v2_setup:
            # Usage indicates billing V2 - we don't update billing as that is done
            # whenever the billing service is called
            return self.available_features

        plan, realm = self._billing_plan_details
        if not plan:
            self.available_features = []
        elif realm in ("ee", "demo"):
            try:
                from ee.models.license import License
            except ImportError:
                License = None  # type: ignore
            self.available_features = License.PLANS.get(plan, [])
        else:
            self.available_features = self.billing.available_features  # type: ignore
        return self.available_features

    def is_feature_available(self, feature: Union[AvailableFeature, str]) -> bool:
        return feature in self.available_features

    def get_usage_for_feature(self, feature: str) -> Optional[int]:
        if not self.usage:
            return None
        return self.usage.get(feature, {}).get("usage", None)

    def get_limit_for_feature(self, feature: str) -> Optional[int]:
        if not self.usage:
            return None
        return self.usage.get(feature, {}).get("limit", None)

    @property
    def has_billing_v2_setup(self):
        if hasattr(self, "billing") and self.billing.stripe_subscription_id:  # type: ignore
            return False

        return self.usage is not None

    @property
    def active_invites(self) -> QuerySet:
        return self.invites.filter(created_at__gte=timezone.now() - timezone.timedelta(days=INVITE_DAYS_VALIDITY))

    def get_analytics_metadata(self):
        return {
            "member_count": self.members.count(),
            "project_count": self.teams.count(),
            "person_count": sum(team.person_set.count() for team in self.teams.all()),
            "name": self.name,
        }


@receiver(models.signals.pre_save, sender=Organization)
def organization_about_to_be_created(sender, instance: Organization, raw, using, **kwargs):
    if instance._state.adding:
        instance.update_available_features()
        if not is_cloud():
            instance.plugins_access_level = Organization.PluginsAccessLevel.ROOT


@receiver(models.signals.post_save, sender=Organization)
def ensure_available_features_sync(sender, instance: Organization, **kwargs):
    updated_fields = kwargs.get("update_fields") or []
    if "available_features" in updated_fields:
        logger.info("Notifying plugin-server to reset available features cache.", {"organization_id": instance.id})
        get_client().publish("reset-available-features-cache", json.dumps({"organization_id": str(instance.id)}))


class OrganizationMembership(UUIDModel):
    class Level(models.IntegerChoices):
        """Keep in sync with TeamMembership.Level (only difference being projects not having an Owner)."""

        MEMBER = 1, "member"
        ADMIN = 8, "administrator"
        OWNER = 15, "owner"

    organization: models.ForeignKey = models.ForeignKey(
        "posthog.Organization", on_delete=models.CASCADE, related_name="memberships", related_query_name="membership"
    )
    user: models.ForeignKey = models.ForeignKey(
        "posthog.User",
        on_delete=models.CASCADE,
        related_name="organization_memberships",
        related_query_name="organization_membership",
    )
    level: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        default=Level.MEMBER, choices=Level.choices
    )
    joined_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organization_id", "user_id"], name="unique_organization_membership"),
            models.UniqueConstraint(
                fields=["organization_id"], condition=models.Q(level=15), name="only_one_owner_per_organization"
            ),
        ]

    def __str__(self):
        return str(self.Level(self.level))

    def validate_update(
        self, membership_being_updated: "OrganizationMembership", new_level: Optional[Level] = None
    ) -> None:
        if new_level is not None:
            if membership_being_updated.id == self.id:
                raise exceptions.PermissionDenied("You can't change your own access level.")
            if new_level == OrganizationMembership.Level.OWNER:
                if self.level != OrganizationMembership.Level.OWNER:
                    raise exceptions.PermissionDenied(
                        "You can only pass on organization ownership if you're its owner."
                    )
                self.level = OrganizationMembership.Level.ADMIN
                self.save()
            elif new_level > self.level:
                raise exceptions.PermissionDenied(
                    "You can only change access level of others to lower or equal to your current one."
                )
        if membership_being_updated.id != self.id:
            if membership_being_updated.organization_id != self.organization_id:
                raise exceptions.PermissionDenied("You both need to belong to the same organization.")
            if self.level < OrganizationMembership.Level.ADMIN:
                raise exceptions.PermissionDenied("You can only edit others if you are an admin.")
            if membership_being_updated.level > self.level:
                raise exceptions.PermissionDenied("You can only edit others with level lower or equal to you.")

    __repr__ = sane_repr("organization", "user", "level")


class OrganizationInvite(UUIDModel):
    organization: models.ForeignKey = models.ForeignKey(
        "posthog.Organization", on_delete=models.CASCADE, related_name="invites", related_query_name="invite"
    )
    target_email: models.EmailField = models.EmailField(null=True, db_index=True)
    first_name: models.CharField = models.CharField(max_length=30, blank=True, default="")
    created_by: models.ForeignKey = models.ForeignKey(
        "posthog.User",
        on_delete=models.SET_NULL,
        related_name="organization_invites",
        related_query_name="organization_invite",
        null=True,
    )
    emailing_attempt_made: models.BooleanField = models.BooleanField(default=False)
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
    message: models.TextField = models.TextField(blank=True, null=True)

    def validate(self, *, user: Optional["User"] = None, email: Optional[str] = None) -> None:
        _email = email or getattr(user, "email", None)

        if _email and _email != self.target_email:
            raise exceptions.ValidationError(
                "This invite is intended for another email address.",
                code="invalid_recipient",
            )

        if self.is_expired():
            raise exceptions.ValidationError(
                "This invite has expired. Please ask your admin for a new one.", code="expired"
            )

        if OrganizationMembership.objects.filter(organization=self.organization, user=user).exists():
            raise exceptions.ValidationError(
                "You already are a member of this organization.", code="user_already_member"
            )

        if OrganizationMembership.objects.filter(
            organization=self.organization, user__email=self.target_email
        ).exists():
            raise exceptions.ValidationError(
                "Another user with this email address already belongs to this organization.",
                code="existing_email_address",
            )

    def use(self, user: "User", *, prevalidated: bool = False) -> None:
        if not prevalidated:
            self.validate(user=user)
        user.join(organization=self.organization)
        if is_email_available(with_absolute_urls=True) and self.organization.is_member_join_email_enabled:
            from posthog.tasks.email import send_member_join

            send_member_join.apply_async(kwargs={"invitee_uuid": user.uuid, "organization_id": self.organization_id})
        OrganizationInvite.objects.filter(target_email__iexact=self.target_email).delete()

    def is_expired(self) -> bool:
        """Check if invite is older than INVITE_DAYS_VALIDITY days."""
        return self.created_at < timezone.now() - timezone.timedelta(INVITE_DAYS_VALIDITY)

    def __str__(self):
        return absolute_uri(f"/signup/{self.id}")

    __repr__ = sane_repr("organization", "target_email", "created_by")


@receiver(models.signals.pre_delete, sender=OrganizationMembership)
def ensure_organization_membership_consistency(sender, instance: OrganizationMembership, **kwargs):
    save_user = False
    if instance.user.current_organization == instance.organization:
        # reset current_organization if it's the removed organization
        instance.user.current_organization = None
        save_user = True
    if instance.user.current_team is not None and instance.user.current_team.organization == instance.organization:
        # reset current_team if it belongs to the removed organization
        instance.user.current_team = None
        save_user = True
    if save_user:
        instance.user.save()
