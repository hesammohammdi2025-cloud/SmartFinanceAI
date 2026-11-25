
from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from .models import Budget
from transactions.models import Transaction


ZERO = Decimal("0.00")


def get_budget_status(user):
    """
    محاسبه وضعیت بودجه‌های شخصی کاربر در ماه جاری.

    فقط تراکنش‌های شخصی کاربر تا تاریخ امروز
    در محاسبه هزینه‌ها لحاظ می‌شوند.
    """

    today = timezone.localdate()

    budgets = Budget.objects.filter(
        user=user,
        year=today.year,
        month=today.month,
    )

    results = []

    for budget in budgets:

        spent = Transaction.objects.filter(
            user=user,
            transaction_type="expense",
            category=budget.category,
            date__year=budget.year,
            date__month=budget.month,
            date__lte=today,
        ).aggregate(
            total=Sum("amount")
        )["total"] or ZERO

        remaining = budget.amount - spent

        percentage = (
            float(spent / budget.amount * 100)
            if budget.amount > ZERO
            else 0
        )

        if percentage >= 100:
            alert = "از سقف بودجه عبور کرده‌ای!"
        elif percentage >= 80:
            alert = "بیش از ۸۰٪ بودجه مصرف شده است."
        else:
            alert = ""

        results.append({
            "category": budget.category,
            "amount": budget.amount,
            "spent": spent,
            "remaining": remaining,
            "percentage": round(percentage, 1),
            "alert": alert,
        })

    return results


def get_budget_summary(user):
    """
    محاسبه خلاصه بودجه شخصی کاربر در ماه جاری.
    """

    today = timezone.localdate()

    budgets = Budget.objects.filter(
        user=user,
        year=today.year,
        month=today.month,
    )

    total_budget = budgets.aggregate(
        total=Sum("amount")
    )["total"] or ZERO

    budget_statuses = get_budget_status(user)

    total_spent = sum(
        (
            item["spent"]
            for item in budget_statuses
        ),
        ZERO,
    )

    remaining = total_budget - total_spent

    percentage = (
        float(total_spent / total_budget * 100)
        if total_budget > ZERO
        else 0
    )

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": remaining,
        "percentage": round(percentage, 1),
    }
