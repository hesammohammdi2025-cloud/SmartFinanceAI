
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Organization(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="نام سازمان"
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_organizations",
        verbose_name="مدیر اصلی"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "سازمان"
        verbose_name_plural = "سازمان‌ها"

    def __str__(self):
        return self.name


class OrganizationMembership(models.Model):

    ROLE_CHOICES = [
        ("admin", "مدیر سازمان"),
        ("manager", "مدیر"),
        ("accountant", "حسابدار"),
        ("viewer", "مشاهده‌گر"),
        ("employee", "کارمند ساده"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships"
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="viewer"
    )

    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_member"
            )
        ]
        verbose_name = "عضویت سازمان"
        verbose_name_plural = "عضویت‌های سازمان"

    def __str__(self):
        return f"{self.user} - {self.organization} - {self.role}"


class OrganizationInvitation(models.Model):

    ROLE_CHOICES = [
        ("manager", "مدیر"),
        ("accountant", "حسابدار"),
        ("viewer", "مشاهده‌گر"),
        ("employee", "کارمند ساده"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations"
    )

    email = models.EmailField()

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="viewer"
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sent_organization_invitations"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField()

    accepted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    revoked_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "دعوت‌نامه سازمان"
        verbose_name_plural = "دعوت‌نامه‌های سازمان"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def __str__(self):
        return f"{self.email} - {self.organization.name}"
