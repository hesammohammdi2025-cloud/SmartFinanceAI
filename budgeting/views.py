from decimal import Decimal
from io import BytesIO
from pathlib import Path

import arabic_reshaper
from bidi.algorithm import get_display

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import Http404, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.conf import settings

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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

from .forms import BudgetForm, OrganizationBudgetForm
from .models import Budget, OrganizationBudget

from transactions.models import Transaction, OrganizationTransaction

from accounts.permissions import (
    get_user_organization,
    has_organization_role,
)


ZERO = Decimal("0.00")


# ==========================================
# Shared Helpers
# ==========================================

def get_organization_budget_spent(organization, budget, today=None):
    """
    محاسبه هزینه واقعی یک بودجه سازمانی.
    فقط تراکنش‌های هزینه‌ای تا تاریخ امروز محاسبه می‌شوند.
    """

    if today is None:
        today = timezone.localdate()

    spent = OrganizationTransaction.objects.filter(
        organization=organization,
        transaction_type="expense",
        category=budget.category,
        date__year=budget.year,
        date__month=budget.month,
        date__lte=today,
    ).aggregate(
        total=Sum("amount")
    )["total"]

    return spent or ZERO


def calculate_budget_values(budget, spent):
    """
    محاسبه درصد مصرف و مانده بودجه.
    """

    budget.spent = spent
    budget.remaining = budget.amount - spent

    budget.percentage = round(
        float(spent / budget.amount * 100), 1
    ) if budget.amount > ZERO else 0

    if spent >= budget.amount:
        budget.alert = "بودجه تمام شده یا از سقف آن عبور کرده‌ای!"

    elif budget.percentage >= 80:
        budget.alert = "هشدار: بیش از ۸۰٪ بودجه مصرف شده است."

    else:
        budget.alert = ""

    return budget


# ==========================================
# Personal Budget Views
# ==========================================

@login_required
def budget_list(request):

    today = timezone.localdate()

    budgets = Budget.objects.filter(
        user=request.user
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
        )["total"] or ZERO

        calculate_budget_values(budget, spent)

    return render(
        request,
        "budgeting/budget_list.html",
        {
            "budgets": budgets,
            "today": today,
        },
    )


@login_required
def budget_create(request):

    if request.method == "POST":

        form = BudgetForm(request.POST)

        if form.is_valid():

            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()

            messages.success(
                request,
                "بودجه با موفقیت ثبت شد."
            )

            return redirect("budgeting:budget_list")

    else:
        form = BudgetForm()

    return render(
        request,
        "budgeting/budget_form.html",
        {"form": form},
    )


# ==========================================
# Organization Budget List
# ==========================================

@login_required
def organization_budget_list(request, organization_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager", "accountant"]
    ):
        raise Http404("شما اجازه مشاهده بودجه سازمان را ندارید.")

    today = timezone.localdate()

    all_budgets = OrganizationBudget.objects.filter(
        organization=organization
    )

    # --------------------------------------
    # Filters
    # --------------------------------------

    selected_year = request.GET.get("year", "")
    selected_month = request.GET.get("month", "")
    selected_category = request.GET.get("category", "")

    budgets = all_budgets

    if selected_year:
        budgets = budgets.filter(year=selected_year)

    if selected_month:
        budgets = budgets.filter(month=selected_month)

    if selected_category:
        budgets = budgets.filter(category=selected_category)

    # --------------------------------------
    # Filter Options
    # --------------------------------------

    years = (
        all_budgets.order_by()
        .values_list("year", flat=True)
        .distinct()
    )

    categories = (
        all_budgets.order_by("category")
        .values_list("category", flat=True)
        .distinct()
    )

    months = [
        (1, "فروردین"),
        (2, "اردیبهشت"),
        (3, "خرداد"),
        (4, "تیر"),
        (5, "مرداد"),
        (6, "شهریور"),
        (7, "مهر"),
        (8, "آبان"),
        (9, "آذر"),
        (10, "دی"),
        (11, "بهمن"),
        (12, "اسفند"),
    ]

    # --------------------------------------
    # Calculate Budget Expenses
    # --------------------------------------

    budgets = list(budgets)

    for budget in budgets:

        spent = get_organization_budget_spent(
            organization,
            budget,
            today,
        )

        calculate_budget_values(budget, spent)

        if spent >= budget.amount:
            budget.alert = (
                "هشدار: بودجه این دسته‌بندی تمام شده "
                "یا از سقف آن عبور کرده است."
            )

        elif budget.percentage >= 80:
            budget.alert = (
                "هشدار: بیش از ۸۰٪ بودجه این دسته‌بندی مصرف شده است."
            )

    # --------------------------------------
    # Organization Budget Summary
    # --------------------------------------

    total_budget = sum(
        (budget.amount for budget in budgets),
        ZERO,
    )

    total_spent = sum(
        (budget.spent for budget in budgets),
        ZERO,
    )

    total_remaining = total_budget - total_spent

    total_percentage = round(
        float(total_spent / total_budget * 100), 1
    ) if total_budget > ZERO else 0

    if total_budget > ZERO and total_percentage >= 100:

        overall_alert = (
            "هشدار: مجموع هزینه‌ها به سقف کل بودجه رسیده "
            "یا از آن عبور کرده است."
        )

        overall_status = "تجاوز از بودجه"

    elif total_percentage >= 80:

        overall_alert = (
            "هشدار: بیش از ۸۰ درصد کل بودجه سازمان مصرف شده است."
        )

        overall_status = "نزدیک به سقف بودجه"

    else:

        overall_alert = "وضعیت کلی بودجه سازمان مناسب است."

        overall_status = "وضعیت مناسب"

    # --------------------------------------
    # Chart Data
    # --------------------------------------

    chart_labels = [
        f"{budget.category} - {budget.month}/{budget.year}"
        for budget in budgets
    ]

    chart_budget_data = [
        float(budget.amount)
        for budget in budgets
    ]

    chart_spent_data = [
        float(budget.spent)
        for budget in budgets
    ]

    # --------------------------------------
    # Permissions
    # --------------------------------------

    can_manage = has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager"]
    )

    can_export = has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager", "accountant"]
    )

    # --------------------------------------
    # Render
    # --------------------------------------

    return render(
        request,
        "budgeting/organization_budget_list.html",
        {
            "organization": organization,
            "budgets": budgets,
            "can_manage": can_manage,
            "can_export": can_export,

            "years": years,
            "months": months,
            "categories": categories,
            "selected_year": selected_year,
            "selected_month": selected_month,
            "selected_category": selected_category,

            "chart_labels": chart_labels,
            "chart_budget_data": chart_budget_data,
            "chart_spent_data": chart_spent_data,

            "total_budget": total_budget,
            "total_spent": total_spent,
            "total_remaining": total_remaining,
            "total_percentage": total_percentage,
            "overall_alert": overall_alert,
            "overall_status": overall_status,
        },
    )


# ==========================================
# Create Organization Budget
# ==========================================

@login_required
def organization_budget_create(request, organization_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager"]
    ):

        messages.error(
            request,
            "شما اجازه ثبت بودجه سازمانی را ندارید."
        )

        return redirect(
            "budgeting:organization_budget_list",
            organization_id=organization.id
        )

    if request.method == "POST":

        form = OrganizationBudgetForm(
            request.POST,
            organization=organization
        )

        if form.is_valid():

            budget = form.save(commit=False)

            budget.organization = organization
            budget.created_by = request.user

            budget.save()

            messages.success(
                request,
                "بودجه سازمانی با موفقیت ثبت شد."
            )

            return redirect(
                "budgeting:organization_budget_list",
                organization_id=organization.id
            )

    else:

        form = OrganizationBudgetForm(
            organization=organization
        )

    return render(
        request,
        "budgeting/organization_budget_form.html",
        {
            "form": form,
            "organization": organization,
        },
    )


# ==========================================
# Edit Organization Budget
# ==========================================

@login_required
def organization_budget_edit(request, organization_id, budget_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager"]
    ):
        raise Http404("اجازه ویرایش بودجه را ندارید.")

    budget = get_object_or_404(
        OrganizationBudget,
        pk=budget_id,
        organization=organization
    )

    if request.method == "POST":

        form = OrganizationBudgetForm(
            request.POST,
            instance=budget,
            organization=organization
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "بودجه سازمان با موفقیت ویرایش شد."
            )

            return redirect(
                "budgeting:organization_budget_list",
                organization_id=organization.id
            )

    else:

        form = OrganizationBudgetForm(
            instance=budget,
            organization=organization
        )

    return render(
        request,
        "budgeting/organization_budget_form.html",
        {
            "form": form,
            "organization": organization,
            "is_edit": True,
        },
    )


# ==========================================
# Delete Organization Budget
# ==========================================

@login_required
@require_POST
def organization_budget_delete(request, organization_id, budget_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager"]
    ):
        raise Http404("اجازه حذف بودجه را ندارید.")

    budget = get_object_or_404(
        OrganizationBudget,
        pk=budget_id,
        organization=organization
    )

    budget.delete()

    messages.success(
        request,
        "بودجه سازمان با موفقیت حذف شد."
    )

    return redirect(
        "budgeting:organization_budget_list",
        organization_id=organization.id
    )


# ==========================================
# Organization Budget PDF Report
# ==========================================

@login_required
def organization_budget_pdf(request, organization_id):

    # --------------------------------------
    # Organization Access
    # --------------------------------------

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        request.user,
        organization.id,
        ["admin", "manager", "accountant"]
    ):
        raise Http404("اجازه دریافت گزارش بودجه را ندارید.")

    today = timezone.localdate()

    # --------------------------------------
    # Font Configuration
    # --------------------------------------

    font_paths = [
        Path(settings.BASE_DIR) / "static" / "fonts" / "Vazirmatn-Regular.ttf",
        Path(r"C:\Windows\Fonts\tahoma.ttf"),
    ]

    font_path = next(
        (path for path in font_paths if path.exists()),
        None
    )

    if font_path is None:
        return HttpResponse(
            "فونت فارسی پیدا نشد. فایل Vazirmatn-Regular.ttf را در مسیر "
            "static/fonts پروژه قرار دهید.",
            status=500
        )

    if "PersianFont" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(
            TTFont("PersianFont", str(font_path))
        )

    # --------------------------------------
    # Persian Text Helper
    # --------------------------------------

    def rtl(value):

        text = str(value)

        reshaped_text = arabic_reshaper.reshape(text)

        return get_display(reshaped_text)

    # --------------------------------------
    # Filters
    # --------------------------------------

    selected_year = request.GET.get("year", "")
    selected_month = request.GET.get("month", "")
    selected_category = request.GET.get("category", "")

    budgets = OrganizationBudget.objects.filter(
        organization=organization
    )

    if selected_year:
        budgets = budgets.filter(year=selected_year)

    if selected_month:
        budgets = budgets.filter(month=selected_month)

    if selected_category:
        budgets = budgets.filter(category=selected_category)

    budgets = list(
        budgets.order_by("year", "month", "category")
    )

    # --------------------------------------
    # Calculate Expenses
    # --------------------------------------

    total_budget = ZERO
    total_spent = ZERO

    for budget in budgets:

        spent = get_organization_budget_spent(
            organization,
            budget,
            today,
        )

        calculate_budget_values(budget, spent)

        if budget.percentage >= 100:
            budget.status = "عبور از بودجه"

        elif budget.percentage >= 80:
            budget.status = "نزدیک به سقف"

        else:
            budget.status = "مناسب"

        total_budget += budget.amount
        total_spent += spent

    total_remaining = total_budget - total_spent

    total_percentage = round(
        float(total_spent / total_budget * 100), 1
    ) if total_budget > ZERO else 0

    # --------------------------------------
    # Overall Status
    # --------------------------------------

    if total_budget == ZERO:

        overall_status = "بودجه‌ای ثبت نشده است."

    elif total_percentage >= 100:

        overall_status = (
            "هشدار: هزینه‌ها به سقف بودجه رسیده "
            "یا از آن عبور کرده‌اند."
        )

    elif total_percentage >= 80:

        overall_status = (
            "هشدار: بیش از ۸۰ درصد بودجه مصرف شده است."
        )

    else:

        overall_status = "وضعیت کلی بودجه مناسب است."

    # --------------------------------------
    # Create PDF
    # --------------------------------------

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
        "PersianTitle",
        parent=styles["Title"],
        fontName="PersianFont",
        fontSize=18,
        leading=26,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
    )

    normal_style = ParagraphStyle(
        "PersianNormal",
        parent=styles["Normal"],
        fontName="PersianFont",
        fontSize=10,
        leading=17,
        alignment=TA_RIGHT,
    )

    header_style = ParagraphStyle(
        "PersianHeader",
        parent=normal_style,
        fontSize=9,
        textColor=colors.white,
        alignment=TA_CENTER,
    )

    cell_style = ParagraphStyle(
        "PersianCell",
        parent=normal_style,
        fontSize=8,
        leading=12,
        alignment=TA_RIGHT,
    )

    story = []

    # --------------------------------------
    # Report Header
    # --------------------------------------

    organization_name = getattr(
        organization,
        "name",
        str(organization)
    )

    story.append(
        Paragraph(
            rtl("گزارش بودجه سازمان"),
            title_style
        )
    )

    story.append(Spacer(1, 5 * mm))

    story.append(
        Paragraph(
            rtl(f"نام سازمان: {organization_name}"),
            normal_style
        )
    )

    generated_at = timezone.localtime().strftime(
        "%Y-%m-%d %H:%M"
    )

    story.append(
        Paragraph(
            rtl(f"زمان تهیه گزارش: {generated_at}"),
            normal_style
        )
    )

    if selected_year:
        story.append(
            Paragraph(
                rtl(f"سال انتخاب‌شده: {selected_year}"),
                normal_style
            )
        )

    if selected_month:
        story.append(
            Paragraph(
                rtl(f"ماه انتخاب‌شده: {selected_month}"),
                normal_style
            )
        )

    if selected_category:
        story.append(
            Paragraph(
                rtl(f"دسته‌بندی: {selected_category}"),
                normal_style
            )
        )

    story.append(Spacer(1, 7 * mm))

    # --------------------------------------
    # Summary
    # --------------------------------------

    story.append(
        Paragraph(
            rtl("خلاصه وضعیت بودجه"),
            normal_style
        )
    )

    summary_data = [
        [
            Paragraph(rtl("وضعیت"), header_style),
            Paragraph(rtl("درصد مصرف"), header_style),
            Paragraph(rtl("مانده بودجه"), header_style),
            Paragraph(rtl("هزینه واقعی"), header_style),
            Paragraph(rtl("کل بودجه"), header_style),
        ],
        [
            Paragraph(rtl(overall_status), cell_style),
            Paragraph(f"{total_percentage}%", cell_style),
            Paragraph(f"{total_remaining:,.2f}", cell_style),
            Paragraph(f"{total_spent:,.2f}", cell_style),
            Paragraph(f"{total_budget:,.2f}", cell_style),
        ],
    ]

    summary_table = Table(
        summary_data,
        colWidths=[
            65 * mm,
            35 * mm,
            40 * mm,
            40 * mm,
            40 * mm,
        ],
    )

    summary_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eff6ff")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 8),
        ])
    )

    story.append(summary_table)

    story.append(Spacer(1, 10 * mm))

    # --------------------------------------
    # Budget Details
    # --------------------------------------

    story.append(
        Paragraph(
            rtl("جزئیات بودجه دسته‌بندی‌ها"),
            normal_style
        )
    )

    table_data = [
        [
            Paragraph(rtl("وضعیت"), header_style),
            Paragraph(rtl("درصد مصرف"), header_style),
            Paragraph(rtl("مانده"), header_style),
            Paragraph(rtl("هزینه واقعی"), header_style),
            Paragraph(rtl("بودجه تعیین‌شده"), header_style),
            Paragraph(rtl("دوره"), header_style),
            Paragraph(rtl("دسته‌بندی"), header_style),
        ]
    ]

    for budget in budgets:

        period = f"{budget.month}/{budget.year}"

        table_data.append([
            Paragraph(rtl(budget.status), cell_style),
            Paragraph(f"{budget.percentage}%", cell_style),
            Paragraph(f"{budget.remaining:,.2f}", cell_style),
            Paragraph(f"{budget.spent:,.2f}", cell_style),
            Paragraph(f"{budget.amount:,.2f}", cell_style),
            Paragraph(period, cell_style),
            Paragraph(rtl(budget.category), cell_style),
        ])

    if not budgets:
        table_data.append([
            Paragraph(
                rtl("برای فیلترهای انتخاب‌شده بودجه‌ای ثبت نشده است."),
                cell_style
            ),
            "", "", "", "", "", ""
        ])

    details_table = Table(
        table_data,
        colWidths=[
            35 * mm,
            25 * mm,
            35 * mm,
            35 * mm,
            35 * mm,
            25 * mm,
            45 * mm,
        ],
        repeatRows=1,
    )

    details_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f766e")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("PADDING", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [
                colors.white,
                colors.HexColor("#f1f5f9"),
            ]),
        ])
    )

    story.append(details_table)

    # --------------------------------------
    # Build PDF
    # --------------------------------------

    pdf.build(story)

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="organization_budget_{organization.id}.pdf"'
    )

    return response