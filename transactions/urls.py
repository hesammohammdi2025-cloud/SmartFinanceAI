
from django.urls import path
from . import views


urlpatterns = [

    # ==========================================
    # Personal Transactions
    # ==========================================

    path(
        'add/',
        views.add_transaction,
        name='add_transaction'
    ),

    path(
        '<int:pk>/edit/',
        views.edit_transaction,
        name='edit_transaction'
    ),

    path(
        '<int:pk>/delete/',
        views.delete_transaction,
        name='delete_transaction'
    ),


    # ==========================================
    # Organization Transactions
    # ==========================================

    path(
        'organizations/<int:organization_id>/transactions/',
        views.organization_transaction_list,
        name='organization_transaction_list'
    ),

    path(
        'organizations/<int:organization_id>/transactions/add/',
        views.organization_transaction_add,
        name='organization_transaction_add'
    ),

    path(
        'organizations/<int:organization_id>/transactions/<int:pk>/edit/',
        views.organization_transaction_edit,
        name='organization_transaction_edit'
    ),

    path(
        'organizations/<int:organization_id>/transactions/<int:pk>/delete/',
        views.organization_transaction_delete,
        name='organization_transaction_delete'
    ),


    # ==========================================
    # Organization Dashboard
    # ==========================================

    path(
        'organizations/<int:organization_id>/dashboard/',
        views.organization_dashboard,
        name='organization_dashboard'
    ),


    # ==========================================
    # Organization Reports
    # ==========================================

    path(
        'organizations/<int:organization_id>/reports/',
        views.organization_report,
        name='organization_report'
    ),

    path(
        'organizations/<int:organization_id>/reports/excel/',
        views.organization_report_excel,
        name='organization_report_excel'
    ),


    # ==========================================
    # Personal Recurring Transactions
    # ==========================================

    path(
        'recurring/',
        views.recurring_transaction_list,
        name='recurring_transaction_list'
    ),

    path(
        'recurring/add/',
        views.recurring_transaction_create,
        name='recurring_transaction_create'
    ),

    path(
        'recurring/<int:pk>/edit/',
        views.recurring_transaction_edit,
        name='recurring_transaction_edit'
    ),

    path(
        'recurring/<int:pk>/delete/',
        views.recurring_transaction_delete,
        name='recurring_transaction_delete'
    ),

    path(
        'recurring/<int:pk>/toggle/',
        views.recurring_transaction_toggle,
        name='recurring_transaction_toggle'
    ),


    # ==========================================
    # Organization Recurring Transactions
    # ==========================================

    path(
        'organizations/<int:organization_id>/recurring/',
        views.organization_recurring_transaction_list,
        name='organization_recurring_transaction_list'
    ),

    path(
        'organizations/<int:organization_id>/recurring/add/',
        views.organization_recurring_transaction_create,
        name='organization_recurring_transaction_create'
    ),

    path(
        'organizations/<int:organization_id>/recurring/<int:pk>/edit/',
        views.organization_recurring_transaction_edit,
        name='organization_recurring_transaction_edit'
    ),

    path(
        'organizations/<int:organization_id>/recurring/<int:pk>/delete/',
        views.organization_recurring_transaction_delete,
        name='organization_recurring_transaction_delete'
    ),

    path(
        'organizations/<int:organization_id>/recurring/<int:pk>/toggle/',
        views.organization_recurring_transaction_toggle,
        name='organization_recurring_transaction_toggle'
    ),

]
