
from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from accounts.models import Organization


class Budget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="budgets"
    )

    category = models.CharField(
        max_length=100,
        verbose_name="دسته‌بندی هزینه"
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="مبلغ بودجه"
    )

    year = models.PositiveSmallIntegerField(
        verbose_name="سال"
    )

    month = models.PositiveSmallIntegerField(
        verbose_name="ماه"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category", "year", "month"],
                name="unique_user_category_monthly_budget"
            ),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12),
                name="budget_month_between_1_and_12"
            ),
        ]
        verbose_name = "بودجه"
        verbose_name_plural = "بودجه‌ها"

    def __str__(self):
        return (
            f"{self.user} - {self.category} - "
            f"{self.year}/{self.month:02d}"
        )


class OrganizationBudget(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="budgets"
    )

    category = models.CharField(
        max_length=100,
        verbose_name="دسته‌بندی هزینه"
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        verbose_name="مبلغ بودجه"
    )

    year = models.PositiveSmallIntegerField(
        verbose_name="سال"
    )

    month = models.PositiveSmallIntegerField(
        verbose_name="ماه"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_organization_budgets"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-year", "-month", "category"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "category", "year", "month"],
                name="unique_org_category_monthly_budget"
            ),
            models.CheckConstraint(
                condition=models.Q(month__gte=1, month__lte=12),
                name="org_budget_month_between_1_and_12"
            ),
        ]
        verbose_name = "بودجه سازمانی"
        verbose_name_plural = "بودجه‌های سازمانی"

    def __str__(self):
        return (
            f"{self.organization} - {self.category} - "
            f"{self.year}/{self.month:02d}"
        )
