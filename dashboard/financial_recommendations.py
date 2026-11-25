
from django.utils import timezone

from .financial_analysis import analyze_monthly_expenses
from .financial_metrics import get_financial_totals


def generate_financial_recommendations(user, analysis=None):
    """
    تولید پیشنهادهای مالی شخصی‌سازی‌شده
    بر اساس اطلاعات واقعی تراکنش‌های شخصی کاربر.

    در صورت دریافت analysis، تحلیل مالی مجدداً محاسبه نمی‌شود.

    واحد مبالغ: تومان
    """

    recommendations = []

    today = timezone.localdate()

    financial_totals = get_financial_totals(
        user,
        end_date=today,
    )

    total_income = financial_totals["income"]
    total_expenses = financial_totals["expenses"]
    balance = financial_totals["balance"]
    transaction_count = financial_totals["transaction_count"]

    if transaction_count == 0:
        return [
            "هنوز تراکنشی ثبت نکرده‌ای. "
            "ابتدا درآمدها و هزینه‌هایت را ثبت کن "
            "تا بتوانیم وضعیت مالی را تحلیل کنیم."
        ]

    if analysis is None:
        analysis = analyze_monthly_expenses(user)

    average_income = analysis["average_income"]
    average_expenses = analysis["average_expenses"]

    categories = analysis["categories"]
    anomalies = analysis["anomalies"]

    comparison_period = analysis.get("comparison_period") or {}

    expense_comparison_available = comparison_period.get(
        "expense_comparison_available",
        False,
    )

    income_comparison_available = comparison_period.get(
        "income_comparison_available",
        False,
    )

    # 1. بررسی تعادل درآمد و هزینه

    if total_expenses > total_income:
        recommendations.append(
            "هشدار: مجموع هزینه‌های ثبت‌شده از درآمد بیشتر است. "
            "پیشنهاد می‌شود هزینه‌های ضروری و غیرضروری را جداگانه بررسی کنی."
        )

    elif total_income > total_expenses:
        recommendations.append(
            "وضعیت درآمد و هزینه مثبت است. "
            "می‌توانی بخشی از موجودی باقی‌مانده را "
            "برای اهداف مالی آینده کنار بگذاری."
        )

    else:
        recommendations.append(
            "درآمد و هزینه‌های ثبت‌شده برابر هستند. "
            "برای ایجاد پس‌انداز، بهتر است مخارج قابل‌کاهش را بررسی کنی."
        )

    # 2. بررسی نسبت هزینه به درآمد

    if total_income > 0:

        expense_ratio = (
            total_expenses / total_income
        ) * 100

        if expense_ratio > 90:
            recommendations.append(
                f"حدود {expense_ratio:.1f}٪ از درآمد ثبت‌شده "
                "صرف هزینه شده است. بررسی مخارج غیرضروری می‌تواند مفید باشد."
            )

        elif expense_ratio > 70:
            recommendations.append(
                f"نسبت هزینه به درآمد حدود {expense_ratio:.1f}٪ است. "
                "بهتر است برای هزینه‌های آینده حاشیه مالی در نظر بگیری."
            )

        else:
            recommendations.append(
                f"نسبت هزینه به درآمد حدود {expense_ratio:.1f}٪ است. "
                "در حال حاضر فاصله مناسبی میان درآمد و هزینه‌های ثبت‌شده وجود دارد."
            )

    else:
        recommendations.append(
            "برای محاسبه نسبت هزینه به درآمد، ابتدا باید درآمد ثبت شود."
        )

    # 3. بررسی دسته‌های پرهزینه

    if categories:

        top_category = categories[0]

        recommendations.append(
            f"بیشترین هزینه مربوط به دسته "
            f"«{top_category['category']}» است. "
            f"مبلغ ثبت‌شده: {top_category['amount']:,.2f}"
        )

        for category in categories[:3]:

            if category["percentage"] >= 40:
                recommendations.append(
                    f"دسته «{category['category']}» "
                    f"حدود {category['percentage']:.1f}٪ "
                    "از کل هزینه‌ها را تشکیل می‌دهد. "
                    "بررسی این بخش می‌تواند به مدیریت بهتر مخارج کمک کند."
                )

    else:
        recommendations.append(
            "هنوز هزینه‌ای برای تحلیل دسته‌بندی‌ها ثبت نشده است."
        )

    # 4. بررسی تغییرات هزینه ماهانه

    expense_change = analysis["change"]

    if expense_change is not None:

        if expense_change > 0:
            recommendations.append(
                f"هزینه‌ها نسبت به ماه قبل "
                f"{expense_change:.2f}٪ افزایش داشته‌اند. "
                "بررسی علت این افزایش پیشنهاد می‌شود."
            )

        elif expense_change < 0:
            recommendations.append(
                f"هزینه‌ها نسبت به ماه قبل "
                f"{abs(expense_change):.2f}٪ کاهش داشته‌اند."
            )

        else:
            recommendations.append(
                "هزینه‌ها نسبت به ماه قبل تغییری نداشته‌اند."
            )

    elif not expense_comparison_available:
        recommendations.append(
            "برای مقایسه هزینه‌ها، باید در هر دو بازه "
            "تراکنش هزینه‌ای ثبت شده باشد."
        )

    else:
        recommendations.append(
            "اطلاعات کافی برای محاسبه درصد تغییر هزینه‌ها وجود ندارد؛ "
            "ممکن است هزینه‌های بازه قبلی صفر بوده باشد."
        )

    # 5. بررسی تغییرات درآمد ماهانه

    income_change = analysis["income_change"]

    if income_change is not None:

        if income_change > 0:
            recommendations.append(
                f"درآمد نسبت به ماه قبل "
                f"{income_change:.2f}٪ افزایش داشته است."
            )

        elif income_change < 0:
            recommendations.append(
                f"درآمد نسبت به ماه قبل "
                f"{abs(income_change):.2f}٪ کاهش داشته است. "
                "بهتر است هزینه‌های آینده را با توجه به درآمد فعلی برنامه‌ریزی کنی."
            )

        else:
            recommendations.append(
                "درآمد نسبت به ماه قبل تغییری نداشته است."
            )

    elif not income_comparison_available:
        recommendations.append(
            "برای مقایسه درآمد، باید در هر دو بازه "
            "تراکنش درآمدی ثبت شده باشد."
        )

    else:
        recommendations.append(
            "اطلاعات کافی برای محاسبه درصد تغییر درآمد وجود ندارد؛ "
            "ممکن است درآمد بازه قبلی صفر بوده باشد."
        )

    # 6. بررسی هزینه‌های غیرعادی

    if anomalies:

        for anomaly in anomalies:
            recommendations.append(
                f"توجه: در ماه {anomaly['month']} "
                f"هزینه‌ای به مبلغ {anomaly['expense']:,.2f} ثبت شده "
                "که بالاتر از میانگین هزینه‌های ماهانه است. "
                "بهتر است تراکنش‌های آن ماه را بررسی کنی."
            )

    else:
        recommendations.append(
            "بر اساس معیار آماری فعلی، "
            "ماه دارای هزینه غیرعادی شناسایی نشده است."
        )

    # 7. نمایش میانگین درآمد و هزینه

    if average_income > 0:
        recommendations.append(
            f"میانگین درآمد ماهانه: {average_income:,.2f}\n"
            f"میانگین هزینه ماهانه: {average_expenses:,.2f}"
        )

    # 8. نمایش موجودی خالص

    recommendations.append(
        f"موجودی خالص بر اساس تراکنش‌های ثبت‌شده: "
        f"{balance:,.2f}"
    )

    return recommendations
