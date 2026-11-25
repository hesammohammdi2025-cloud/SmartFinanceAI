
from django.contrib import admin
from .models import Budget


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "category",
        "amount",
        "year",
        "month",
    )

    list_filter = (
        "year",
        "month",
        "category",
    )

    search_fields = (
        "user__username",
        "category",
    )

    ordering = ("-year", "-month")
