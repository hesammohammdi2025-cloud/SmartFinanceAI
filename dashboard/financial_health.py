
from decimal import Decimal

from django.utils import timezone

from .financial_analysis import analyze_monthly_expenses
from .financial_metrics import get_financial_totals


def calculate_financial_health(user, analysis=None):
    """
    محاسبه سلامت مالی شخصی کاربر.

    - استفاده از هسته مرکزی محاسبات مالی
    - امکان دریافت تحلیل محاسبه‌شده قبلی
    - جلوگیری از محاسبه تکراری تحلیل ماهانه
    - محاسبه امتیاز سلامت مالی بین صفر تا صد

    تمام مبالغ بر اساس تومان فرض شده‌اند.
    محاسبات فقط شامل تراکنش‌های شخصی تا تاریخ امروز هستند.
    """

    today = timezone.localdate()

    # --------------------------------------
    # Central Financial Metrics
    # --------------------------------------

    financial_totals = get_financial_totals(
        user,
        end_date=today,
    )

    income = financial_totals["income"]
    expenses = financial_totals["expenses"]
    balance = financial_totals["balance"]

    transaction_count = financial_totals["transaction_count"]

    result = {
        "score": None,
        "status": "اطلاعات ناکافی",
        "income": float(income),
        "expenses": float(expenses),
        "balance": float(balance),
        "reasons": [],
    }

    # --------------------------------------
    # Transaction Availability
    # --------------------------------------

    if transaction_count == 0:
        result["reasons"].append(
            "برای ارزیابی، ابتدا درآمدها و هزینه‌هایت را ثبت کن."
        )
        return result

    # --------------------------------------
    # Financial Score
    # --------------------------------------

    score = 50

    # --------------------------------------
    # Income and Expense Ratio
    # --------------------------------------

    if income > 0:

        expense_ratio = expenses / income

        if expense_ratio <= Decimal("0.5"):
            score += 30

            result["reasons"].append(
                "هزینه‌ها حداکثر نصف درآمد ثبت‌شده هستند."
            )

        elif expense_ratio <= Decimal("0.7"):
            score += 20

            result["reasons"].append(
                "نسبت هزینه به درآمد در محدوده متوسط است."
            )

        elif expense_ratio <= Decimal("0.9"):
            score += 10

            result["reasons"].append(
                "بخش زیادی از درآمد صرف هزینه‌ها می‌شود."
            )

        elif expense_ratio <= Decimal("1"):
            result["reasons"].append(
                "تقریباً تمام درآمد صرف هزینه‌ها می‌شود."
            )

        else:
            score -= 25

            result["reasons"].append(
                "هزینه‌های ثبت‌شده از درآمد بیشتر هستند."
            )

    else:
        score -= 10

        result["reasons"].append(
            "درآمدی ثبت نشده است؛ برای ارزیابی دقیق‌تر، "
            "اطلاعات درآمد را نیز وارد کن."
        )

    # --------------------------------------
    # Financial Balance
    # --------------------------------------

    if balance > 0:
        score += 10

        result["reasons"].append(
            "موجودی خالص بر اساس تراکنش‌ها مثبت است."
        )

    elif balance == 0:
        result["reasons"].append(
            "درآمد و هزینه ثبت‌شده برابر هستند."
        )

    else:
        result["reasons"].append(
            "برای متعادل کردن دخل‌وخرج، هزینه‌ها را بررسی کن."
        )

    # --------------------------------------
    # Monthly Expense Trend
    # --------------------------------------

    if analysis is None:
        analysis = analyze_monthly_expenses(user)

    change = analysis.get("change")

    if change is not None:

        if change < 0:
            score += 10

            result["reasons"].append(
                "هزینه‌ها نسبت به ماه قبل کاهش یافته‌اند."
            )

        elif change > 0:
            score -= 5

            result["reasons"].append(
                "هزینه‌ها نسبت به ماه قبل افزایش یافته‌اند."
            )

        else:
            result["reasons"].append(
                "هزینه‌ها نسبت به ماه قبل ثابت مانده‌اند."
            )

    else:
        result["reasons"].append(
            "اطلاعات کافی برای ارزیابی روند تغییرات هزینه وجود ندارد."
        )

    # --------------------------------------
    # Score Range
    # --------------------------------------

    score = max(0, min(100, score))

    # --------------------------------------
    # Financial Health Status
    # --------------------------------------

    if score >= 80:
        status = "خوب"

    elif score >= 60:
        status = "نسبتاً خوب"

    elif score >= 40:
        status = "نیازمند توجه"

    else:
        status = "نیازمند بررسی جدی"

    result["score"] = score
    result["status"] = status

    return result
