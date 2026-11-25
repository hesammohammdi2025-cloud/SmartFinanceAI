
from decimal import Decimal

from django.db.models import Sum, Count, Q
from django.utils import timezone

from transactions.models import Transaction


ZERO = Decimal("0.00")


def get_personal_transactions(user):
    """دریافت تراکنش‌های شخصی کاربر؛ بدون تراکنش سازمانی."""

    return Transaction.objects.filter(user=user)


def get_financial_totals(user, start_date=None, end_date=None):
    """
    محاسبه یکپارچه درآمد، هزینه و مانده مالی شخصی.

    واحد تمام مبالغ: تومان
    """

    transactions = get_personal_transactions(user)

    if start_date:
        transactions = transactions.filter(date__gte=start_date)

    if end_date:
        transactions = transactions.filter(date__lte=end_date)

    result = transactions.aggregate(
        total_income=Sum(
            "amount",
            filter=Q(transaction_type="income"),
        ),
        total_expenses=Sum(
            "amount",
            filter=Q(transaction_type="expense"),
        ),
        transaction_count=Count("id"),
    )

    income = result["total_income"] or ZERO
    expenses = result["total_expenses"] or ZERO

    return {
        "income": income,
        "expenses": expenses,
        "balance": income - expenses,
        "transaction_count": result["transaction_count"],
    }


def get_monthly_financial_totals(user, year=None, month=None):
    """محاسبه اطلاعات مالی یک ماه مشخص."""

    today = timezone.localdate()

    year = year or today.year
    month = month or today.month

    return get_financial_totals(
        user=user,
        start_date=today.replace(
            year=year,
            month=month,
            day=1,
        ),
        end_date=(
            today
            if year == today.year and month == today.month
            else None
        ),
    )


def get_expense_income_ratio(income, expenses):
    """محاسبه نسبت هزینه به درآمد به درصد."""

    if income <= ZERO:
        return None

    return (expenses / income) * Decimal("100")
