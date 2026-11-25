
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import Http404, HttpResponse
from django.db.models import Sum, Q
from django.db.models.functions import TruncMonth

from utils.jalali import jalali_to_gregorian, gregorian_to_jalali

from accounts.models import OrganizationMembership

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from .forms import (
    TransactionForm,
    OrganizationTransactionForm,
    RecurringTransactionForm,
)

from .models import (
    Transaction,
    OrganizationTransaction,
    RecurringTransaction,
)

from accounts.permissions import (
    get_user_organization,
    has_organization_role
)


# ==========================================
# Organization Permission Helper
# ==========================================

FINANCIAL_ROLES = ['admin', 'manager', 'accountant']

MANAGEMENT_ROLES = ['admin', 'manager']


def get_report_organization(user, organization_id):
    """
    دسترسی به گزارش مالی سازمان.
    فقط مدیر، مدیر اجرایی، حسابدار و مالک اجازه دارند.
    """

    organization = get_user_organization(
        user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        user,
        organization_id,
        FINANCIAL_ROLES
    ):
        raise Http404(
            "شما اجازه مشاهده گزارش مالی را ندارید."
        )

    return organization


def get_financial_organization(user, organization_id):
    """
    دسترسی به اطلاعات مالی سازمان
    فقط برای مدیر، حسابدار و مالک.
    Viewer اجازه ورود به این بخش را ندارد.
    """

    organization = get_user_organization(
        user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if not has_organization_role(
        user,
        organization_id,
        FINANCIAL_ROLES
    ):
        raise Http404(
            "شما اجازه دسترسی به اطلاعات مالی سازمان را ندارید."
        )

    return organization


def check_organization_role(user, organization_id, roles, error_message):
    """
    بررسی مستقیم نقش عضویت کاربر.
    مالک اصلی سازمان دسترسی مدیریتی دارد.
    """

    organization = get_user_organization(
        user,
        organization_id
    )

    if organization is None:
        raise Http404("سازمان موردنظر پیدا نشد.")

    if organization.owner_id == user.pk:
        return

    membership = OrganizationMembership.objects.filter(
        organization=organization,
        user=user
    ).first()

    if membership is None or membership.role not in roles:
        raise Http404(error_message)


# ==========================================
# Personal Transactions
# ==========================================

@login_required
def add_transaction(request):

    if request.method == 'POST':

        form = TransactionForm(request.POST)

        if form.is_valid():

            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()

            return redirect('home')

    else:

        form = TransactionForm()

        transaction_type = request.GET.get('type')

        if transaction_type in ['income', 'expense']:
            form.initial['transaction_type'] = transaction_type

    return render(
        request,
        'transactions/add_transaction.html',
        {'form': form}
    )


@login_required
def edit_transaction(request, pk):

    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user
    )

    if request.method == 'POST':

        form = TransactionForm(
            request.POST,
            instance=transaction
        )

        if form.is_valid():

            form.save()

            return redirect('home')

    else:

        form = TransactionForm(
            instance=transaction
        )

    return render(
        request,
        'transactions/add_transaction.html',
        {
            'form': form,
            'edit_mode': True
        }
    )


@login_required
def delete_transaction(request, pk):

    transaction = get_object_or_404(
        Transaction,
        pk=pk,
        user=request.user
    )

    if request.method == 'POST':

        transaction.delete()

        return redirect('home')

    return render(
        request,
        'transactions/confirm_delete.html',
        {'transaction': transaction}
    )


# ==========================================
# Organization Transactions
# ==========================================

@login_required
def organization_transaction_list(request, organization_id):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    transactions = OrganizationTransaction.objects.filter(
        organization=organization
    ).select_related('created_by')

    can_add = has_organization_role(
        request.user,
        organization_id,
        FINANCIAL_ROLES
    )

    can_edit = has_organization_role(
        request.user,
        organization_id,
        FINANCIAL_ROLES
    )

    can_delete = has_organization_role(
        request.user,
        organization_id,
        MANAGEMENT_ROLES
    )

    return render(
        request,
        'transactions/organization_transaction_list.html',
        {
            'organization': organization,
            'transactions': transactions,
            'can_add': can_add,
            'can_edit': can_edit,
            'can_delete': can_delete,
        }
    )


@login_required
def organization_transaction_add(request, organization_id):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        FINANCIAL_ROLES,
        "شما اجازه ثبت تراکنش ندارید."
    )

    if request.method == 'POST':

        form = OrganizationTransactionForm(
            request.POST,
            organization=organization
        )

        if form.is_valid():

            transaction = form.save(commit=False)

            transaction.organization = organization
            transaction.created_by = request.user

            transaction.save()

            return redirect(
                'organization_transaction_list',
                organization_id=organization.id
            )

    else:

        form = OrganizationTransactionForm(
            organization=organization
        )

        transaction_type = request.GET.get('type')

        if transaction_type in ['income', 'expense']:
            form.initial['transaction_type'] = transaction_type

    return render(
        request,
        'transactions/organization_transaction_form.html',
        {
            'form': form,
            'organization': organization,
            'edit_mode': False,
        }
    )


@login_required
def organization_transaction_edit(request, organization_id, pk):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        FINANCIAL_ROLES,
        "شما اجازه ویرایش تراکنش ندارید."
    )

    transaction = get_object_or_404(
        OrganizationTransaction,
        pk=pk,
        organization=organization
    )

    if request.method == 'POST':

        form = OrganizationTransactionForm(
            request.POST,
            instance=transaction,
            organization=organization
        )

        if form.is_valid():

            form.save()

            return redirect(
                'organization_transaction_list',
                organization_id=organization.id
            )

    else:

        form = OrganizationTransactionForm(
            instance=transaction,
            organization=organization
        )

    return render(
        request,
        'transactions/organization_transaction_form.html',
        {
            'form': form,
            'organization': organization,
            'edit_mode': True,
            'transaction': transaction,
        }
    )



@login_required
def organization_transaction_delete(request, organization_id, pk):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        MANAGEMENT_ROLES,
        "شما اجازه حذف تراکنش ندارید."
    )

    transaction = get_object_or_404(
        OrganizationTransaction,
        pk=pk,
        organization=organization
    )

    if request.method == 'POST':

        transaction.delete()

        return redirect(
            'organization_transaction_list',
            organization_id=organization.id
        )

    return render(
        request,
        'transactions/organization_transaction_confirm_delete.html',
        {
            'organization': organization,
            'transaction': transaction,
        }
    )


# ==========================================
# Organization Financial Dashboard
# ==========================================

@login_required
def organization_dashboard(request, organization_id):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    transactions = OrganizationTransaction.objects.filter(
        organization=organization
    )

    summary = transactions.aggregate(
        total_income=Sum(
            'amount',
            filter=Q(transaction_type='income')
        ),
        total_expenses=Sum(
            'amount',
            filter=Q(transaction_type='expense')
        )
    )

    total_income = summary['total_income'] or 0
    total_expenses = summary['total_expenses'] or 0

    balance = total_income - total_expenses

    transaction_count = transactions.count()

    latest_transactions = transactions.select_related(
        'created_by'
    )[:5]

    monthly_data = (
        transactions
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(
            income=Sum(
                'amount',
                filter=Q(transaction_type='income')
            ),
            expenses=Sum(
                'amount',
                filter=Q(transaction_type='expense')
            )
        )
        .order_by('month')
    )

    monthly_labels = []
    monthly_income = []
    monthly_expenses = []

    for item in monthly_data:

        monthly_labels.append(
        gregorian_to_jalali(item['month'])[:7]
        )

        monthly_income.append(
            float(item['income'] or 0)
        )

        monthly_expenses.append(
            float(item['expenses'] or 0)
        )

    context = {
        'organization': organization,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': balance,
        'transaction_count': transaction_count,
        'latest_transactions': latest_transactions,
        'monthly_labels': monthly_labels,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
    }

    return render(
        request,
        'transactions/organization_dashboard.html',
        context
    )


# ==========================================
# Organization Reports - Shared Filter
# ==========================================

def get_organization_report_data(request, organization):

    transactions = OrganizationTransaction.objects.filter(
        organization=organization
    ).select_related('created_by')

    start_date_value = request.GET.get('start_date', '').strip()
    end_date_value = request.GET.get('end_date', '').strip()
    transaction_type = request.GET.get('type', '')

    start_date = None
    end_date = None

    error_message = None

    # تبدیل تاریخ شروع شمسی به میلادی
    if start_date_value:

        try:
            start_date = jalali_to_gregorian(
                start_date_value.replace('/', '-')
            )

        except (ValueError, TypeError):
            error_message = 'تاریخ شروع معتبر نیست.'

    # تبدیل تاریخ پایان شمسی به میلادی
    if end_date_value and error_message is None:

        try:
            end_date = jalali_to_gregorian(
                end_date_value.replace('/', '-')
            )

        except (ValueError, TypeError):
            error_message = 'تاریخ پایان معتبر نیست.'

    # بررسی ترتیب تاریخ‌ها
    if (
        error_message is None
        and start_date
        and end_date
        and start_date > end_date
    ):

        error_message = 'تاریخ شروع نباید بعد از تاریخ پایان باشد.'

    # اعمال فیلتر تاریخ فقط در صورت معتبر بودن ورودی‌ها
    if error_message is None:

        if start_date:

            transactions = transactions.filter(
                date__gte=start_date
            )

        if end_date:

            transactions = transactions.filter(
                date__lte=end_date
            )

    # فیلتر نوع تراکنش
    if transaction_type in ['income', 'expense']:

        transactions = transactions.filter(
            transaction_type=transaction_type
        )

    elif transaction_type:

        transaction_type = ''
        error_message = 'نوع تراکنش معتبر نیست.'

    transactions = transactions.order_by(
        '-date',
        '-created_at'
    )

    summary = transactions.aggregate(
        total_income=Sum(
            'amount',
            filter=Q(transaction_type='income')
        ),
        total_expenses=Sum(
            'amount',
            filter=Q(transaction_type='expense')
        )
    )

    total_income = summary['total_income'] or 0
    total_expenses = summary['total_expenses'] or 0

    return {
        'transactions': transactions,
        'total_income': total_income,
        'total_expenses': total_expenses,
        'balance': total_income - total_expenses,
        'start_date': start_date_value,
        'end_date': end_date_value,
        'selected_type': transaction_type,
        'error_message': error_message,
    }


# ==========================================
# Organization Financial Report
# ==========================================

@login_required
def organization_report(request, organization_id):

    organization = get_report_organization(
        request.user,
        organization_id
    )

    report_data = get_organization_report_data(
        request,
        organization
    )

    context = {
        'organization': organization,
        **report_data,
        'export_query': request.GET.urlencode(),
    }

    return render(
        request,
        'transactions/organization_report.html',
        context
    )


# ==========================================
# Export Organization Report to Excel
# ==========================================

@login_required
def organization_report_excel(request, organization_id):

    organization = get_report_organization(
        request.user,
        organization_id
    )

    report_data = get_organization_report_data(
        request,
        organization
    )

    if report_data['error_message']:

        return HttpResponse(
            report_data['error_message'],
            status=400,
            content_type='text/plain; charset=utf-8'
        )

    workbook = Workbook()

    sheet = workbook.active
    sheet.title = "گزارش مالی"

    sheet.merge_cells('A1:G1')

    sheet['A1'] = (
        f"گزارش مالی سازمان {organization.name}"
    )

    sheet['A1'].font = Font(
        bold=True,
        size=16,
        color="FFFFFF"
    )

    sheet['A1'].fill = PatternFill(
        fill_type="solid",
        fgColor="0F766E"
    )

    sheet['A1'].alignment = Alignment(
        horizontal="center"
    )

    sheet['A3'] = "مجموع درآمد"
    sheet['B3'] = float(report_data['total_income'])

    sheet['C3'] = "مجموع هزینه"
    sheet['D3'] = float(report_data['total_expenses'])

    sheet['E3'] = "مانده خالص"
    sheet['F3'] = float(report_data['balance'])

    for cell in sheet[3]:

        cell.font = Font(bold=True)

        cell.alignment = Alignment(
            horizontal="center"
        )

    headers = [
        "عنوان تراکنش",
        "مبلغ",
        "نوع تراکنش",
        "دسته‌بندی",
        "تاریخ",
        "ثبت‌کننده",
        "توضیحات",
    ]

    header_row = 5

    for column, header in enumerate(
        headers,
        start=1
    ):

        cell = sheet.cell(
            row=header_row,
            column=column,
            value=header
        )

        cell.font = Font(
            bold=True,
            color="FFFFFF"
        )

        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1E293B"
        )

        cell.alignment = Alignment(
            horizontal="center"
        )

    for row_number, transaction in enumerate(
        report_data['transactions'],
        start=header_row + 1
    ):

        row_data = [
            transaction.title,
            float(transaction.amount),
            (
                "درآمد"
                if transaction.transaction_type == "income"
                else "هزینه"
            ),
            transaction.category,
            transaction.date,
            (
                transaction.created_by.username
                if transaction.created_by else ""
            ),
            transaction.description,
        ]

        for column, value in enumerate(
            row_data,
            start=1
        ):

            cell = sheet.cell(
                row=row_number,
                column=column,
                value=value
            )

            cell.alignment = Alignment(
                horizontal="right",
                vertical="center"
            )

            if column == 2:
                cell.number_format = '#,##0.00'

            if column == 5:
                cell.number_format = 'yyyy-mm-dd'

    column_widths = [
        25, 18, 18, 20, 16, 20, 40
    ]

    for index, width in enumerate(
        column_widths,
        start=1
    ):

        sheet.column_dimensions[
            get_column_letter(index)
        ].width = width

    sheet.freeze_panes = 'A6'

    sheet.auto_filter.ref = (
        f"A5:G{max(sheet.max_row, 5)}"
    )

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.sheet'
        )
    )

    response['Content-Disposition'] = (
        f'attachment; filename="organization_{organization.id}_report.xlsx"'
    )

    workbook.save(response)

    return response


# ==========================================
# Personal Recurring Transactions
# ==========================================

@login_required
def recurring_transaction_list(request):

    recurring_transactions = RecurringTransaction.objects.filter(
        user=request.user
    )

    return render(
        request,
        'transactions/recurring_transaction_list.html',
        {
            'recurring_transactions': recurring_transactions,
            'organization': None,
            'can_add': True,
            'can_edit': True,
            'can_delete': True,
        }
    )


@login_required
def recurring_transaction_create(request):

    if request.method == 'POST':

        form = RecurringTransactionForm(request.POST)

        if form.is_valid():

            recurring = form.save(commit=False)

            recurring.user = request.user
            recurring.organization = None
            recurring.created_by = request.user
            recurring.next_run_date = recurring.start_date

            recurring.save()

            return redirect(
                'recurring_transaction_list'
            )

    else:

        form = RecurringTransactionForm()

    return render(
        request,
        'transactions/recurring_transaction_form.html',
        {
            'form': form,
            'organization': None,
            'edit_mode': False,
        }
    )


@login_required
def recurring_transaction_edit(request, pk):

    recurring = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        user=request.user,
        organization__isnull=True
    )

    if request.method == 'POST':

        form = RecurringTransactionForm(
            request.POST,
            instance=recurring
        )

        if form.is_valid():

            updated = form.save(commit=False)

            if recurring.last_generated_date is None:

                updated.next_run_date = updated.start_date

            updated.save()

            return redirect(
                'recurring_transaction_list'
            )

    else:

        form = RecurringTransactionForm(
            instance=recurring
        )

    return render(
        request,
        'transactions/recurring_transaction_form.html',
        {
            'form': form,
            'organization': None,
            'edit_mode': True,
            'recurring': recurring,
        }
    )


@login_required
@require_POST
def recurring_transaction_delete(request, pk):

    recurring = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        user=request.user,
        organization__isnull=True
    )

    recurring.delete()

    return redirect(
        'recurring_transaction_list'
    )


@login_required
@require_POST
def recurring_transaction_toggle(request, pk):

    recurring = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        user=request.user,
        organization__isnull=True
    )

    recurring.is_active = not recurring.is_active

    recurring.save(
        update_fields=['is_active', 'updated_at']
    )

    return redirect(
        'recurring_transaction_list'
    )


# ==========================================
# Organization Recurring Transactions
# ==========================================

@login_required
def organization_recurring_transaction_list(
    request,
    organization_id
):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    recurring_transactions = RecurringTransaction.objects.filter(
        organization=organization
    ).select_related('created_by')

    can_add = has_organization_role(
        request.user,
        organization_id,
        FINANCIAL_ROLES
    )

    can_edit = has_organization_role(
        request.user,
        organization_id,
        FINANCIAL_ROLES
    )

    can_delete = has_organization_role(
        request.user,
        organization_id,
        MANAGEMENT_ROLES
    )

    return render(
        request,
        'transactions/recurring_transaction_list.html',
        {
            'recurring_transactions': recurring_transactions,
            'organization': organization,
            'can_add': can_add,
            'can_edit': can_edit,
            'can_delete': can_delete,
        }
    )


@login_required
def organization_recurring_transaction_create(
    request,
    organization_id
):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        FINANCIAL_ROLES,
        "شما اجازه ایجاد برنامه تراکنش را ندارید."
    )

    if request.method == 'POST':

        form = RecurringTransactionForm(request.POST)

        if form.is_valid():

            recurring = form.save(commit=False)

            recurring.user = None
            recurring.organization = organization
            recurring.created_by = request.user
            recurring.next_run_date = recurring.start_date

            recurring.save()

            return redirect(
                'organization_recurring_transaction_list',
                organization_id=organization.id
            )

    else:

        form = RecurringTransactionForm()

    return render(
        request,
        'transactions/recurring_transaction_form.html',
        {
            'form': form,
            'organization': organization,
            'edit_mode': False,
        }
    )


@login_required
def organization_recurring_transaction_edit(
    request,
    organization_id,
    pk
):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        FINANCIAL_ROLES,
        "شما اجازه ویرایش برنامه تراکنش را ندارید."
    )

    recurring = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        organization=organization,
        user__isnull=True
    )

    if request.method == 'POST':

        form = RecurringTransactionForm(
            request.POST,
            instance=recurring
        )

        if form.is_valid():

            updated = form.save(commit=False)

            if recurring.last_generated_date is None:

                updated.next_run_date = updated.start_date

            updated.save()

            return redirect(
                'organization_recurring_transaction_list',
                organization_id=organization.id
            )

    else:

        form = RecurringTransactionForm(
            instance=recurring
        )

    return render(
        request,
        'transactions/recurring_transaction_form.html',
        {
            'form': form,
            'organization': organization,
            'edit_mode': True,
            'recurring': recurring,
        }
    )


@login_required
@require_POST
def organization_recurring_transaction_delete(
    request,
    organization_id,
    pk
):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        MANAGEMENT_ROLES,
        "شما اجازه حذف برنامه را ندارید."
    )

    recurring = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        organization=organization,
        user__isnull=True
    )

    recurring.delete()

    return redirect(
        'organization_recurring_transaction_list',
        organization_id=organization.id
    )


@login_required
@require_POST
def organization_recurring_transaction_toggle(
    request,
    organization_id,
    pk
):

    organization = get_financial_organization(
        request.user,
        organization_id
    )

    check_organization_role(
        request.user,
        organization.id,
        MANAGEMENT_ROLES,
        "شما اجازه تغییر وضعیت برنامه را ندارید."
    )

    recurring = get_object_or_404(
        RecurringTransaction,
        pk=pk,
        organization=organization,
        user__isnull=True
    )

    recurring.is_active = not recurring.is_active

    recurring.save(
        update_fields=['is_active', 'updated_at']
    )

    return redirect(
        'organization_recurring_transaction_list',
        organization_id=organization.id
    )
