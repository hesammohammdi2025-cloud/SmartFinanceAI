
import pandas as pd

from decimal import Decimal
from pathlib import Path
from io import BytesIO
from html import escape

from django.shortcuts import render
from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse

from transactions.models import Transaction, OrganizationTransaction

from .prediction import predict_next_month
from .financial_health import calculate_financial_health
from .financial_analysis import analyze_monthly_expenses
from .financial_recommendations import generate_financial_recommendations
from .financial_metrics import get_financial_totals

from budgeting.utils import get_budget_status, get_budget_summary
from budgeting.models import Budget

from accounts.permissions import (
    get_user_organization,
    get_organization_role,
)

from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

from utils.jalali import gregorian_to_jalali


def get_limited_member_organization(user, organization_id):
    """
    دریافت سازمان فقط برای مشاهده‌گر و کارمند ساده.

    این نقش‌ها فقط مجاز به مشاهده حقوق شخصی خود هستند.
    """

    organization = get_user_organization(
        user,
        organization_id,
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    role = get_organization_role(
        user,
        organization_id,
    )

    if role not in ("viewer", "employee"):
        raise Http404("شما اجازه دسترسی به این بخش را ندارید.")

    return organization


@login_required
def home(request):
    """
    داشبورد مالی شخصی کاربر.

    تمام محاسبات مالی اصلی از هسته مرکزی دریافت می‌شوند.
    فقط تراکنش‌های شخصی کاربر تا تاریخ امروز محاسبه می‌شوند.
    """

    today = timezone.localdate()

    transactions = Transaction.objects.filter(
        user=request.user,
        date__lte=today,
    )

    financial_totals = get_financial_totals(
        request.user,
        end_date=today,
    )

    income = float(financial_totals["income"])
    expenses = float(financial_totals["expenses"])
    balance = float(financial_totals["balance"])

    records = list(
        transactions.values(
            "title",
            "amount",
            "transaction_type",
            "category",
            "date",
        )
    )

    df = pd.DataFrame(records)

    expense_labels = []
    expense_values = []

    expense_df = pd.DataFrame()
    category_totals = pd.Series(dtype=float)

    if not df.empty:

        df["amount"] = pd.to_numeric(
            df["amount"],
            errors="coerce",
        ).fillna(0)

        expense_df = df[
            df["transaction_type"] == "expense"
        ].copy()

        if not expense_df.empty:

            category_totals = (
                expense_df.groupby("category")["amount"]
                .sum()
                .sort_values(ascending=False)
            )

            expense_labels = category_totals.index.tolist()

            expense_values = [
                float(value)
                for value in category_totals.tolist()
            ]

    prediction_result = {
        "success": False,
        "message": "برای پیش‌بینی، حداقل ۳ ماه داده ماهانه لازم است.",
        "predicted_expense": None,
    }

    monthly_chart_labels = []
    monthly_chart_values = []
    prediction_chart_values = []

    monthly_expenses = pd.Series(dtype=float)

    if not expense_df.empty:

        monthly_df = expense_df.copy()

        monthly_df["date"] = pd.to_datetime(
            monthly_df["date"]
        )

        monthly_expenses = (
            monthly_df
            .set_index("date")["amount"]
            .resample("MS")
            .sum()
        )

        if not monthly_expenses.empty:

            full_months = pd.date_range(
                start=monthly_expenses.index.min(),
                end=pd.Timestamp(
                    today.replace(day=1)
                ),
                freq="MS",
            )

            monthly_expenses = monthly_expenses.reindex(
                full_months,
                fill_value=0,
            )

            prediction_result = predict_next_month(
                monthly_expenses.tolist()
            )

            monthly_chart_labels = [
                gregorian_to_jalali(
                    date.to_pydatetime()
                )
                for date in monthly_expenses.index
            ]

            monthly_chart_values = [
                float(value)
                for value in monthly_expenses.tolist()
            ]

            if prediction_result["success"]:

                next_month = (
                    monthly_expenses.index[-1]
                    + pd.DateOffset(months=1)
                )

                monthly_chart_labels.append(
                    gregorian_to_jalali(
                        next_month.to_pydatetime()
                    )
                )

                prediction_chart_values = (
                    [None] * (len(monthly_chart_labels) - 1)
                    + [
                        prediction_result["predicted_expense"]
                    ]
                )

            else:

                prediction_chart_values = (
                    [None] * len(monthly_chart_labels)
                )

    insights = []

    if df.empty:

        insights.append(
            "هنوز تراکنشی ثبت نکرده‌اید. "
            "برای شروع، درآمدها و هزینه‌های خود را ثبت کنید."
        )

    else:

        if income == 0 and expenses == 0:

            insights.append(
                "هنوز مبلغ درآمد یا هزینه‌ای برای تحلیل وجود ندارد."
            )

        elif expenses > income:

            insights.append(
                "هشدار: مجموع هزینه‌های شما از درآمدتان بیشتر است."
            )

        elif income > expenses:

            insights.append(
                "وضعیت فعلی مالی شما مثبت است؛ "
                "درآمد ثبت‌شده بیشتر از هزینه‌هاست."
            )

        else:

            insights.append(
                "مجموع درآمد و هزینه‌های ثبت‌شده برابر است."
            )

        if not expense_df.empty:

            top_category = category_totals.index[0]
            top_amount = float(category_totals.iloc[0])

            insights.append(
                f"بیشترین هزینه شما مربوط به دسته "
                f"«{top_category}» با مبلغ "
                f"{top_amount:,.2f} است."
            )

        if income > 0:

            expense_ratio = (
                expenses / income
            ) * 100

            insights.append(
                f"هزینه‌های ثبت‌شده شما برابر با "
                f"{expense_ratio:.1f} درصد درآمد ثبت‌شده است."
            )

        if len(monthly_expenses) >= 2:

            last_month_expense = float(
                monthly_expenses.iloc[-1]
            )

            previous_month_expense = float(
                monthly_expenses.iloc[-2]
            )

            if previous_month_expense > 0:

                change_percent = (
                    (
                        last_month_expense
                        - previous_month_expense
                    )
                    / previous_month_expense
                ) * 100

                if change_percent > 0:

                    insights.append(
                        f"هشدار هوشمند: هزینه‌های آخرین ماه ثبت‌شده "
                        f"{change_percent:.1f} درصد بیشتر از ماه قبل است. "
                        "دسته‌های پرهزینه را بررسی کنید."
                    )

                elif change_percent < 0:

                    insights.append(
                        f"خبر خوب: هزینه‌های آخرین ماه ثبت‌شده "
                        f"{abs(change_percent):.1f} درصد کمتر از ماه قبل است."
                    )

                else:

                    insights.append(
                        "هزینه‌های آخرین ماه ثبت‌شده با ماه قبل برابر است."
                    )

            elif last_month_expense > 0:

                insights.append(
                    "در ماه قبل هزینه‌ای ثبت نشده بود؛ "
                    "بنابراین مقایسه درصدی امکان‌پذیر نیست."
                )

    budget_chart_labels = []
    budget_chart_values = []
    budget_spent_values = []

    budgets = Budget.objects.filter(
        user=request.user,
        year=today.year,
        month=today.month,
    )

    for budget in budgets:

        spent = Transaction.objects.filter(
            user=request.user,
            transaction_type="expense",
            category=budget.category,
            date__year=budget.year,
            date__month=budget.month,
            date__lte=today,
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        budget_chart_labels.append(
            budget.category
        )

        budget_chart_values.append(
            float(budget.amount)
        )

        budget_spent_values.append(
            float(spent)
        )

    # محاسبه تحلیل جامع مالی فقط یک بار
    financial_analysis = analyze_monthly_expenses(
        request.user
    )

    # استفاده از همان تحلیل برای تولید پیشنهادها
    financial_recommendations = (
        generate_financial_recommendations(
            request.user,
            analysis=financial_analysis,
        )
    )

    # استفاده از همان تحلیل برای محاسبه سلامت مالی
    financial_health = calculate_financial_health(
        request.user,
        analysis=financial_analysis,
    )

    monthly_analysis = financial_analysis.get(
        "months",
        [],
    )

    expense_categories = financial_analysis.get(
        "categories",
        [],
    )

    financial_anomalies = financial_analysis.get(
        "anomalies",
        [],
    )

    context = {
        "income": income,
        "expenses": expenses,
        "balance": balance,

        "transactions": transactions.order_by("-date")[:5],

        "chart_labels": ["درآمد", "هزینه"],
        "chart_values": [income, expenses],

        "expense_labels": expense_labels,
        "expense_values": expense_values,

        "insights": insights,

        "prediction": prediction_result,

        "monthly_chart_labels": monthly_chart_labels,
        "monthly_chart_values": monthly_chart_values,
        "prediction_chart_values": prediction_chart_values,

        "financial_health": financial_health,

        "budget_statuses": get_budget_status(
            request.user
        ),

        "budget_summary": get_budget_summary(
            request.user
        ),

        "budget_chart_labels": budget_chart_labels,
        "budget_chart_values": budget_chart_values,
        "budget_spent_values": budget_spent_values,

        "financial_analysis": financial_analysis,
        "monthly_analysis": monthly_analysis,
        "expense_categories": expense_categories,
        "financial_anomalies": financial_anomalies,

        "financial_recommendations": financial_recommendations,
    }

    return render(
        request,
        "dashboard/home.html",
        context,
    )


@login_required
def viewer_salary_dashboard(request, organization_id):

    organization = get_limited_member_organization(
        request.user,
        organization_id,
    )

    salaries = OrganizationTransaction.objects.filter(
        organization=organization,
        recipient=request.user,
        is_salary=True,
        transaction_type="expense",
        paid_at__isnull=False,
    ).order_by("-paid_at")

    today = timezone.localdate()

    selected_year = request.GET.get(
        "year",
        str(today.year),
    )

    selected_month = request.GET.get(
        "month",
        "",
    )

    try:
        selected_year = int(selected_year)

        if selected_year < 1900 or selected_year > 2100:
            selected_year = today.year

    except (TypeError, ValueError):
        selected_year = today.year

    salaries = salaries.filter(
        paid_at__year=selected_year
    )

    if selected_month:

        try:
            selected_month = int(selected_month)

            if 1 <= selected_month <= 12:

                salaries = salaries.filter(
                    paid_at__month=selected_month
                )

            else:
                selected_month = ""

        except (TypeError, ValueError):
            selected_month = ""

    total_salary = salaries.aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    context = {
        "organization": organization,
        "salaries": salaries,
        "total_salary": total_salary,
        "selected_year": selected_year,
        "selected_month": selected_month,
        "years": range(
            today.year,
            today.year - 6,
            -1,
        ),
        "months": range(1, 13),
    }

    return render(
        request,
        "dashboard/viewer_salary_dashboard.html",
        context,
    )


@login_required
def viewer_salary_export_excel(request, organization_id):

    organization = get_limited_member_organization(
        request.user,
        organization_id,
    )

    salaries = OrganizationTransaction.objects.filter(
        organization=organization,
        recipient=request.user,
        is_salary=True,
        transaction_type="expense",
        paid_at__isnull=False,
    ).order_by("-paid_at")

    today = timezone.localdate()

    try:
        selected_year = int(
            request.GET.get("year", today.year)
        )

        if selected_year < 1900 or selected_year > 2100:
            selected_year = today.year

    except (TypeError, ValueError):
        selected_year = today.year

    salaries = salaries.filter(
        paid_at__year=selected_year
    )

    selected_month = request.GET.get(
        "month",
        "",
    )

    if selected_month:

        try:
            selected_month = int(selected_month)

            if 1 <= selected_month <= 12:

                salaries = salaries.filter(
                    paid_at__month=selected_month
                )

        except (TypeError, ValueError):
            pass

    workbook = Workbook()

    sheet = workbook.active
    sheet.title = "حقوق دریافتی"

    headers = [
        "عنوان پرداخت",
        "مبلغ",
        "تاریخ پرداخت",
        "ساعت پرداخت",
        "توضیحات",
    ]

    sheet.append(headers)

    for cell in sheet[1]:

        cell.font = Font(bold=True)

        cell.alignment = Alignment(
            horizontal="center"
        )

    for salary in salaries:

        paid_at = timezone.localtime(
            salary.paid_at
        )

        sheet.append([
            salary.title,
            float(salary.amount),
            gregorian_to_jalali(paid_at),
            paid_at.strftime("%H:%M"),
            salary.description or "",
        ])

    for column in sheet.columns:

        max_length = max(
            len(str(cell.value or ""))
            for cell in column
        )

        sheet.column_dimensions[
            column[0].column_letter
        ].width = min(
            max_length + 4,
            40,
        )

    response = HttpResponse(
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

    response["Content-Disposition"] = (
        f'attachment; filename="salary_{organization_id}_{selected_year}.xlsx"'
    )

    workbook.save(response)

    return response


@login_required
def viewer_salary_export_pdf(request, organization_id):

    import arabic_reshaper

    from bidi.algorithm import get_display

    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import (
        getSampleStyleSheet,
        ParagraphStyle,
    )
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )

    organization = get_limited_member_organization(
        request.user,
        organization_id,
    )

    salaries = OrganizationTransaction.objects.filter(
        organization=organization,
        recipient=request.user,
        is_salary=True,
        transaction_type="expense",
        paid_at__isnull=False,
    )

    today = timezone.localdate()

    try:
        selected_year = int(
            request.GET.get("year", today.year)
        )

        if selected_year < 1900 or selected_year > 2100:
            selected_year = today.year

    except (TypeError, ValueError):
        selected_year = today.year

    salaries = salaries.filter(
        paid_at__year=selected_year
    )

    selected_month = request.GET.get(
        "month",
        "",
    )

    if selected_month:

        try:
            selected_month = int(selected_month)

            if 1 <= selected_month <= 12:

                salaries = salaries.filter(
                    paid_at__month=selected_month
                )

            else:
                selected_month = ""

        except (TypeError, ValueError):
            selected_month = ""

    salaries = list(
        salaries.order_by("-paid_at")
    )

    total_salary = sum(
        (
            salary.amount
            for salary in salaries
        ),
        Decimal("0.00"),
    )

    font_paths = [
        Path(settings.BASE_DIR)
        / "static"
        / "fonts"
        / "Vazirmatn-Regular.ttf",

        Path(r"C:\Windows\Fonts\tahoma.ttf"),
    ]

    font_path = next(
        (
            path
            for path in font_paths
            if path.exists()
        ),
        None,
    )

    if font_path is None:

        return HttpResponse(
            "فونت فارسی پیدا نشد. فایل Vazirmatn-Regular.ttf "
            "را در مسیر static/fonts قرار دهید.",
            status=500,
        )

    font_name = "SalaryPersianFont"

    if font_name not in pdfmetrics.getRegisteredFontNames():

        pdfmetrics.registerFont(
            TTFont(
                font_name,
                str(font_path),
            )
        )

    def rtl(value):

        text_value = str(value)

        reshaped = arabic_reshaper.reshape(
            text_value
        )

        displayed = get_display(
            reshaped
        )

        return escape(
            displayed,
            quote=False,
        )

    def safe_paragraph(value, style):

        return Paragraph(
            rtl(value),
            style,
        )

    buffer = BytesIO()

    pdf = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SalaryTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    normal_style = ParagraphStyle(
        "SalaryNormal",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=17,
        alignment=TA_RIGHT,
    )

    header_style = ParagraphStyle(
        "SalaryHeader",
        parent=normal_style,
        fontSize=9,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    cell_style = ParagraphStyle(
        "SalaryCell",
        parent=normal_style,
        fontSize=9,
        leading=14,
        alignment=TA_RIGHT,
    )

    story = []

    story.append(
        safe_paragraph(
            "گزارش حقوق دریافتی",
            title_style,
        )
    )

    story.append(
        Spacer(1, 6 * mm)
    )

    story.append(
        safe_paragraph(
            f"نام سازمان: {organization.name}",
            normal_style,
        )
    )

    recipient_name = (
        request.user.get_full_name()
        or request.user.get_username()
    )

    story.append(
        safe_paragraph(
            f"نام دریافت‌کننده: {recipient_name}",
            normal_style,
        )
    )

    story.append(
        safe_paragraph(
            f"سال گزارش: {selected_year}",
            normal_style,
        )
    )

    if selected_month:

        story.append(
            safe_paragraph(
                f"ماه گزارش: {selected_month}",
                normal_style,
            )
        )

    else:

        story.append(
            safe_paragraph(
                "ماه گزارش: همه ماه‌ها",
                normal_style,
            )
        )

    generated_at_datetime = timezone.localtime()

    generated_at = (
        gregorian_to_jalali(generated_at_datetime)
        + " "
        + generated_at_datetime.strftime("%H:%M")
    )

    story.append(
        safe_paragraph(
            f"زمان تهیه گزارش: {generated_at}",
            normal_style,
        )
    )

    story.append(
        Spacer(1, 7 * mm)
    )

    story.append(
        safe_paragraph(
            f"تعداد پرداخت‌ها: {len(salaries)}",
            normal_style,
        )
    )

    story.append(
        safe_paragraph(
            f"مجموع حقوق دریافتی: {total_salary:,.2f}",
            normal_style,
        )
    )

    story.append(
        Spacer(1, 7 * mm)
    )

    table_data = [
        [
            safe_paragraph("توضیحات", header_style),
            safe_paragraph("ساعت پرداخت", header_style),
            safe_paragraph("تاریخ پرداخت", header_style),
            safe_paragraph("مبلغ", header_style),
            safe_paragraph("عنوان پرداخت", header_style),
        ]
    ]

    for salary in salaries:

        paid_at = timezone.localtime(
            salary.paid_at
        )

        table_data.append([
            safe_paragraph(
                salary.description or "-",
                cell_style,
            ),

            safe_paragraph(
                paid_at.strftime("%H:%M"),
                cell_style,
            ),

            safe_paragraph(
                gregorian_to_jalali(paid_at),
                cell_style,
            ),

            safe_paragraph(
                f"{salary.amount:,.2f}",
                cell_style,
            ),

            safe_paragraph(
                salary.title,
                cell_style,
            ),
        ])

    if not salaries:

        table_data.append([
            safe_paragraph(
                "در دوره انتخاب‌شده پرداخت حقوقی ثبت نشده است.",
                cell_style,
            ),
            "",
            "",
            "",
            "",
        ])

    salary_table = Table(
        table_data,
        colWidths=[
            65 * mm,
            30 * mm,
            35 * mm,
            40 * mm,
            65 * mm,
        ],
        repeatRows=1,
    )

    salary_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#2563eb"),
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey,
            ),
            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "RIGHT",
            ),
            (
                "PADDING",
                (0, 0),
                (-1, -1),
                8,
            ),
            (
                "ROWBACKGROUNDS",
                (0, 1),
                (-1, -1),
                [
                    colors.white,
                    colors.HexColor("#eff6ff"),
                ],
            ),
        ])
    )

    story.append(salary_table)

    pdf.build(story)

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="salary_{organization.id}_{selected_year}.pdf"'
    )

    return response
