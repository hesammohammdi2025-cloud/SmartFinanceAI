
import pandas as pd

from datetime import timedelta

from django.utils import timezone

from transactions.models import Transaction

from utils.jalali import gregorian_to_jalali
from dashboard.financial_metrics import get_financial_totals


def analyze_monthly_expenses(user):
    """
    تحلیل جامع درآمد و هزینه شخصی کاربر.

    - محاسبه مجموع درآمد و هزینه با هسته مرکزی
    - محاسبه مانده مالی
    - میانگین ماهانه بر اساس ماه‌های کامل
    - مقایسه مستقل درآمد و هزینه در بازه‌های هم‌اندازه
    - تحلیل دسته‌بندی هزینه‌ها
    - تشخیص هزینه‌های غیرعادی

    واحد مبالغ: تومان
    """

    today = timezone.localdate()
    current_start = today.replace(day=1)

    financial_totals = get_financial_totals(
        user,
        end_date=today,
    )

    total_income = financial_totals["income"]
    total_expenses = financial_totals["expenses"]
    balance = financial_totals["balance"]

    transactions = Transaction.objects.filter(
        user=user,
        date__lte=today,
    ).values(
        "date",
        "amount",
        "transaction_type",
        "category",
    )

    df = pd.DataFrame(list(transactions))

    if df.empty:
        return {
            "message": "هنوز تراکنشی برای تحلیل ثبت نشده است.",
            "months": [],
            "change": None,
            "income_change": None,
            "total_income": float(total_income),
            "total_expenses": float(total_expenses),
            "balance": float(balance),
            "average_income": 0.0,
            "average_expenses": 0.0,
            "categories": [],
            "anomalies": [],
            "comparison_period": None,
        }

    # --------------------------------------
    # Data Preparation
    # --------------------------------------

    df["date"] = pd.to_datetime(df["date"])

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce",
    ).fillna(0)

    income_df = df[
        df["transaction_type"] == "income"
    ].copy()

    expense_df = df[
        df["transaction_type"] == "expense"
    ].copy()

    # --------------------------------------
    # Monthly Income and Expenses
    # --------------------------------------

    monthly_income = (
        income_df.set_index("date")["amount"]
        .resample("MS")
        .sum()
    )

    monthly_expenses = (
        expense_df.set_index("date")["amount"]
        .resample("MS")
        .sum()
    )

    monthly = pd.DataFrame({
        "income": monthly_income,
        "expense": monthly_expenses,
    }).fillna(0)

    first_month = monthly.index.min()

    current_month_timestamp = pd.Timestamp(
        current_start
    )

    full_index = pd.date_range(
        start=first_month,
        end=current_month_timestamp,
        freq="MS",
    )

    monthly = monthly.reindex(
        full_index,
        fill_value=0,
    )

    monthly["balance"] = (
        monthly["income"] - monthly["expense"]
    )

    # --------------------------------------
    # Complete Months
    # --------------------------------------

    complete_monthly = monthly[
        monthly.index < current_month_timestamp
    ].copy()

    first_transaction_date = df["date"].min()

    first_month = (
        first_transaction_date
        .to_period("M")
        .to_timestamp()
    )

    if first_transaction_date.day > 1:
        complete_monthly = complete_monthly[
            complete_monthly.index != first_month
        ]

    # --------------------------------------
    # Monthly Averages
    # --------------------------------------

    if not complete_monthly.empty:
        average_income = float(
            complete_monthly["income"].mean()
        )

        average_expenses = float(
            complete_monthly["expense"].mean()
        )
    else:
        average_income = 0.0
        average_expenses = 0.0

    # --------------------------------------
    # Monthly Output
    # --------------------------------------

    months = []

    for month, row in monthly.iterrows():
        jalali_month = gregorian_to_jalali(
            month.to_pydatetime()
        )

        months.append({
            "month": jalali_month[:7],
            "income": round(float(row["income"]), 2),
            "expense": round(float(row["expense"]), 2),
            "balance": round(float(row["balance"]), 2),
        })

    # --------------------------------------
    # Comparable Periods
    # --------------------------------------

    previous_month_end = (
        current_start - timedelta(days=1)
    )

    previous_start = previous_month_end.replace(day=1)

    comparison_end = min(
        today.day,
        previous_month_end.day,
    )

    previous_period_end = previous_start.replace(
        day=comparison_end
    )

    transaction_dates = df["date"].dt.date

    current_period = df[
        (transaction_dates >= current_start)
        & (transaction_dates <= today)
    ]

    previous_period = df[
        (transaction_dates >= previous_start)
        & (transaction_dates <= previous_period_end)
    ]

    # --------------------------------------
    # Comparison Data
    # --------------------------------------

    current_expense = float(
        current_period.loc[
            current_period["transaction_type"] == "expense",
            "amount",
        ].sum()
    )

    previous_expense = float(
        previous_period.loc[
            previous_period["transaction_type"] == "expense",
            "amount",
        ].sum()
    )

    current_income = float(
        current_period.loc[
            current_period["transaction_type"] == "income",
            "amount",
        ].sum()
    )

    previous_income = float(
        previous_period.loc[
            previous_period["transaction_type"] == "income",
            "amount",
        ].sum()
    )

    # --------------------------------------
    # Independent Comparison Availability
    # --------------------------------------

    current_expense_exists = (
        current_period["transaction_type"] == "expense"
    ).any()

    previous_expense_exists = (
        previous_period["transaction_type"] == "expense"
    ).any()

    current_income_exists = (
        current_period["transaction_type"] == "income"
    ).any()

    previous_income_exists = (
        previous_period["transaction_type"] == "income"
    ).any()

    expense_comparison_available = (
        current_expense_exists
        and previous_expense_exists
    )

    income_comparison_available = (
        current_income_exists
        and previous_income_exists
    )

    comparison_available = (
        not current_period.empty
        and not previous_period.empty
    )

    # --------------------------------------
    # Expense Change
    # --------------------------------------

    if (
        expense_comparison_available
        and previous_expense > 0
    ):
        change = round(
            (
                (current_expense - previous_expense)
                / previous_expense
            ) * 100,
            2,
        )
    else:
        change = None

    # --------------------------------------
    # Income Change
    # --------------------------------------

    if (
        income_comparison_available
        and previous_income > 0
    ):
        income_change = round(
            (
                (current_income - previous_income)
                / previous_income
            ) * 100,
            2,
        )
    else:
        income_change = None

    comparison_period = {
        "current_start": gregorian_to_jalali(current_start),
        "current_end": gregorian_to_jalali(today),
        "previous_start": gregorian_to_jalali(previous_start),
        "previous_end": gregorian_to_jalali(previous_period_end),

        "current_expense": round(current_expense, 2),
        "previous_expense": round(previous_expense, 2),

        "current_income": round(current_income, 2),
        "previous_income": round(previous_income, 2),

        "comparison_available": comparison_available,
        "expense_comparison_available": expense_comparison_available,
        "income_comparison_available": income_comparison_available,
    }

    # --------------------------------------
    # Expense Categories
    # --------------------------------------

    categories = (
        expense_df.groupby("category")["amount"]
        .sum()
        .sort_values(ascending=False)
    )

    category_results = []

    analyzed_expenses = float(
        expense_df["amount"].sum()
    )

    for category, amount in categories.items():
        percentage = (
            float(amount) / analyzed_expenses * 100
            if analyzed_expenses > 0
            else 0
        )

        category_results.append({
            "category": str(category),
            "amount": round(float(amount), 2),
            "percentage": round(percentage, 2),
        })

    # --------------------------------------
    # Unusual Expenses
    # --------------------------------------

    anomalies = []

    if len(complete_monthly) >= 3:
        mean_expense = float(
            complete_monthly["expense"].mean()
        )

        std_expense = float(
            complete_monthly["expense"].std()
        )

        if std_expense > 0:
            unusual_months = complete_monthly[
                complete_monthly["expense"]
                > mean_expense + (2 * std_expense)
            ]

            for month, row in unusual_months.iterrows():
                anomalies.append({
                    "month": gregorian_to_jalali(
                        month.to_pydatetime()
                    )[:7],

                    "expense": round(
                        float(row["expense"]), 2
                    ),

                    "average": round(mean_expense, 2),

                    "message": (
                        "هزینه این ماه به‌طور قابل‌توجهی "
                        "بیشتر از میانگین ماه‌های کامل بوده است."
                    ),
                })

    # --------------------------------------
    # Final Result
    # --------------------------------------

    return {
        "message": "تحلیل جامع درآمد و هزینه انجام شد.",

        "total_income": round(float(total_income), 2),
        "total_expenses": round(float(total_expenses), 2),
        "balance": round(float(balance), 2),

        "average_income": round(average_income, 2),
        "average_expenses": round(average_expenses, 2),

        "change": change,
        "income_change": income_change,

        "comparison_period": comparison_period,

        "months": months,
        "categories": category_results,
        "anomalies": anomalies,
    }
