
from django.contrib import admin

from .models import (
    Transaction,
    OrganizationTransaction,
    RecurringTransaction,
)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "user",
        "amount",
        "transaction_type",
        "category",
        "date",
    )

    list_filter = (
        "transaction_type",
        "category",
        "date",
    )

    search_fields = (
        "title",
        "user__username",
        "category",
    )

    date_hierarchy = "date"


@admin.register(OrganizationTransaction)
class OrganizationTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "organization",
        "created_by",
        "amount",
        "transaction_type",
        "is_salary",
        "recipient",
        "date",
    )

    list_filter = (
        "transaction_type",
        "is_salary",
        "organization",
        "date",
    )

    search_fields = (
        "title",
        "organization__name",
        "created_by__username",
        "recipient__username",
    )

    date_hierarchy = "date"


@admin.register(RecurringTransaction)
class RecurringTransactionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "user",
        "organization",
        "amount",
        "transaction_type",
        "frequency",
        "next_run_date",
        "is_active",
    )

    list_filter = (
        "frequency",
        "transaction_type",
        "is_active",
        "organization",
    )

    search_fields = (
        "title",
        "user__username",
        "organization__name",
        "created_by__username",
    )

    date_hierarchy = "next_run_date"

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_generated_date",
    )
