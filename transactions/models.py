
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db.models import Q

from accounts.models import Organization


class Transaction(models.Model):

    TYPE_CHOICES = [
        ("income", "درآمد"),
        ("expense", "هزینه"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="transactions"
    )

    title = models.CharField(max_length=200)

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    category = models.CharField(max_length=100)

    date = models.DateField()

    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"


class OrganizationTransaction(models.Model):

    TYPE_CHOICES = [
        ("income", "درآمد"),
        ("expense", "هزینه"),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="financial_transactions",
        verbose_name="سازمان"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_organization_transactions",
        verbose_name="ثبت‌کننده"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="عنوان تراکنش"
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="مبلغ"
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="نوع تراکنش"
    )

    category = models.CharField(
        max_length=100,
        verbose_name="دسته‌بندی"
    )

    date = models.DateField(
        verbose_name="تاریخ"
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )

    # مشخص‌کردن پرداخت حقوق
    is_salary = models.BooleanField(
        default=False,
        verbose_name="پرداخت حقوق"
    )

    # کارمند دریافت‌کننده حقوق
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="salary_payments_received",
        null=True,
        blank=True,
        verbose_name="دریافت‌کننده پرداخت"
    )

    # تاریخ و ساعت واقعی پرداخت
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="زمان پرداخت"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["-date", "-created_at"]

        verbose_name = "تراکنش سازمانی"

        verbose_name_plural = "تراکنش‌های سازمانی"

    def __str__(self):
        return f"{self.title} - {self.amount}"


class RecurringTransaction(models.Model):

    TYPE_CHOICES = [
        ("income", "درآمد"),
        ("expense", "هزینه"),
    ]

    FREQUENCY_CHOICES = [
        ("daily", "روزانه"),
        ("weekly", "هفتگی"),
        ("monthly", "ماهانه"),
        ("yearly", "سالانه"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recurring_transactions",
        null=True,
        blank=True,
        verbose_name="کاربر"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="recurring_transactions",
        null=True,
        blank=True,
        verbose_name="سازمان"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_recurring_transactions",
        verbose_name="ایجادکننده"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="عنوان"
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="مبلغ"
    )

    transaction_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="نوع تراکنش"
    )

    category = models.CharField(
        max_length=100,
        verbose_name="دسته‌بندی"
    )

    description = models.TextField(
        blank=True,
        verbose_name="توضیحات"
    )

    frequency = models.CharField(
        max_length=10,
        choices=FREQUENCY_CHOICES,
        verbose_name="دوره تکرار"
    )

    start_date = models.DateField(
        verbose_name="تاریخ شروع"
    )

    next_run_date = models.DateField(
        verbose_name="تاریخ اجرای بعدی"
    )

    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاریخ پایان"
    )

    last_generated_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="آخرین تاریخ ثبت‌شده"
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:

        ordering = ["next_run_date", "-created_at"]

        verbose_name = "تراکنش تکرارشونده"

        verbose_name_plural = "تراکنش‌های تکرارشونده"

        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(user__isnull=False, organization__isnull=True)
                    |
                    Q(user__isnull=True, organization__isnull=False)
                ),
                name="recurring_transaction_one_owner"
            ),
        ]

        indexes = [
            models.Index(
                fields=["is_active", "next_run_date"],
                name="recurring_active_date_idx"
            ),
            models.Index(
                fields=["user", "next_run_date"],
                name="recurring_user_date_idx"
            ),
            models.Index(
                fields=["organization", "next_run_date"],
                name="recurring_org_date_idx"
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.amount}"
