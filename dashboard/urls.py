from django.urls import path
from . import views

urlpatterns = [
    path(
        "",
        views.home,
        name="home"
    ),

    path(
        "organizations/<int:organization_id>/salary/",
        views.viewer_salary_dashboard,
        name="viewer_salary_dashboard"
    ),

    path(
        "organizations/<int:organization_id>/salary/export/excel/",
        views.viewer_salary_export_excel,
        name="viewer_salary_export_excel"
    ),

    path(
    "organizations/<int:organization_id>/salary/export/pdf/",
    views.viewer_salary_export_pdf,
    name="viewer_salary_export_pdf"
   ),
]