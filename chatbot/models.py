
from django.conf import settings
from django.db import models
from django.utils import timezone

from accounts.models import Organization


class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "کاربر"),
        ("assistant", "دستیار"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class PendingOrganizationTransactionDeletion(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_transaction_deletions",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="pending_transaction_deletions",
    )

    # برای سازگاری با درخواست‌های حذف قدیمی
    transaction_id = models.PositiveBigIntegerField()

    # برای سازگاری با درخواست‌های حذف قدیمی
    transaction_ids = models.JSONField(
        default=list,
        blank=True,
    )

    # اطلاعات خلاصه درخواست جدید
    preview_count = models.PositiveIntegerField(default=0)
    total_amount = models.CharField(
        max_length=100,
        default="0",
    )

    token = models.UUIDField(
        unique=True,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "درخواست موقت حذف تراکنش"
        verbose_name_plural = "درخواست‌های موقت حذف تراکنش"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_confirmed(self):
        return self.confirmed_at is not None

    def __str__(self):
        return (
            f"درخواست حذف تراکنش‌ها "
            f"در سازمان {self.organization_id}"
        )


class PendingOrganizationTransactionDeletionItem(models.Model):
    pending_deletion = models.ForeignKey(
        PendingOrganizationTransactionDeletion,
        on_delete=models.CASCADE,
        related_name="items",
    )

    # شناسه تراکنش سازمانی؛ عمداً ForeignKey نیست
    # تا حذف تراکنش باعث حذف سابقه درخواست نشود.
    transaction_id = models.PositiveBigIntegerField(
        db_index=True,
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "تراکنش انتخاب‌شده برای حذف"
        verbose_name_plural = "تراکنش‌های انتخاب‌شده برای حذف"

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "pending_deletion",
                    "transaction_id",
                ],
                name="unique_pending_org_deletion_item",
            ),
        ]

    def __str__(self):
        return (
            f"تراکنش {self.transaction_id} "
            f"در درخواست {self.pending_deletion_id}"
        )
