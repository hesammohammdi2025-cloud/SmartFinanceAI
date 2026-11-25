
from django.urls import path
from . import views

app_name = "budgeting"

urlpatterns = [
    # Personal budgets
    path(
        "",
        views.budget_list,
        name="budget_list"
    ),
    path(
        "create/",
        views.budget_create,
        name="budget_create"
    ),

    # Organization budgets
    path(
        "organizations/<int:organization_id>/",
        views.organization_budget_list,
        name="organization_budget_list"
    ),
    path(
        "organizations/<int:organization_id>/create/",
        views.organization_budget_create,
        name="organization_budget_create"
    ),
    path(
    "organizations/<int:organization_id>/<int:budget_id>/edit/",
    views.organization_budget_edit,
    name="organization_budget_edit"
    ),

    path(
    "organizations/<int:organization_id>/<int:budget_id>/delete/",
    views.organization_budget_delete,
    name="organization_budget_delete"
    ),
    path(
    "organizations/<int:organization_id>/pdf/",
    views.organization_budget_pdf,
    name="organization_budget_pdf"
    ),
]
