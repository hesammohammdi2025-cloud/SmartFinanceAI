
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from openpyxl import load_workbook

from accounts.models import Organization, OrganizationMembership
from transactions.models import OrganizationTransaction


User = get_user_model()


class OrganizationSalaryTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        # ساخت کاربران
        cls.owner = User.objects.create_user(
            username="org_owner",
            password="test-password-123"
        )

        cls.employee = User.objects.create_user(
            username="employee_one",
            password="test-password-123"
        )

        cls.other_employee = User.objects.create_user(
            username="employee_two",
            password="test-password-123"
        )

        cls.outsider = User.objects.create_user(
            username="outsider",
            password="test-password-123"
        )

        # ساخت سازمان
        cls.organization = Organization.objects.create(
            name="شرکت آزمایشی",
            owner=cls.owner
        )

        # عضویت کارکنان با نقش مشاهده‌گر
        OrganizationMembership.objects.create(
            organization=cls.organization,
            user=cls.employee,
            role="viewer"
        )

        OrganizationMembership.objects.create(
            organization=cls.organization,
            user=cls.other_employee,
            role="viewer"
        )

        # ایجاد حقوق پرداخت‌شده برای کارمند اول
        cls.own_salary = cls.create_salary(
            recipient=cls.employee,
            title="حقوق کارمند اول",
            amount="25000000",
            year=2026,
            month=5
        )

        # ایجاد حقوق پرداخت‌شده برای کارمند دوم
        cls.other_salary = cls.create_salary(
            recipient=cls.other_employee,
            title="حقوق کارمند دوم",
            amount="30000000",
            year=2026,
            month=5
        )

        # حقوق مربوط به ماه دیگری برای کارمند اول
        cls.old_salary = cls.create_salary(
            recipient=cls.employee,
            title="حقوق ماه قبل",
            amount="20000000",
            year=2026,
            month=4
        )

    @classmethod
    def create_salary(
        cls,
        recipient,
        title,
        amount,
        year,
        month
    ):

        paid_at = timezone.make_aware(
            datetime(year, month, 10, 12, 0)
        )

        return OrganizationTransaction.objects.create(
            organization=cls.organization,
            created_by=cls.owner,
            title=title,
            amount=Decimal(amount),
            transaction_type="expense",
            category="حقوق",
            date=date(year, month, 10),
            description="پرداخت حقوق آزمایشی",
            is_salary=True,
            recipient=recipient,
            paid_at=paid_at
        )

    def salary_url(self):
        return reverse(
            "viewer_salary_dashboard",
            kwargs={
                "organization_id": self.organization.pk
            }
        )

    def excel_url(self):
        return reverse(
            "viewer_salary_export_excel",
            kwargs={
                "organization_id": self.organization.pk
            }
        )

    def pdf_url(self):
        return reverse(
            "viewer_salary_export_pdf",
            kwargs={
                "organization_id": self.organization.pk
            }
        )

    # ---------------------------------
    # تست دسترسی کاربران واردنشده
    # ---------------------------------

    def test_unauthenticated_users_cannot_access_salary_pages(self):

        urls = [
            self.salary_url(),
            self.excel_url(),
            self.pdf_url(),
        ]

        for url in urls:
            response = self.client.get(url)

            self.assertEqual(response.status_code, 302)

    # ---------------------------------
    # تست عدم دسترسی افراد خارج سازمان
    # ---------------------------------

    def test_outsider_cannot_access_salary_dashboard(self):

        self.client.force_login(self.outsider)

        response = self.client.get(self.salary_url())

        self.assertEqual(response.status_code, 404)

    def test_outsider_cannot_export_excel(self):

        self.client.force_login(self.outsider)

        response = self.client.get(self.excel_url())

        self.assertEqual(response.status_code, 404)

    def test_outsider_cannot_export_pdf(self):

        self.client.force_login(self.outsider)

        response = self.client.get(self.pdf_url())

        self.assertEqual(response.status_code, 404)

    # ---------------------------------
    # تست مشاهده فقط حقوق شخصی
    # ---------------------------------

    def test_employee_sees_only_own_salary(self):

        self.client.force_login(self.employee)

        response = self.client.get(self.salary_url())

        self.assertEqual(response.status_code, 200)

        salaries = list(response.context["salaries"])

        salary_ids = [salary.pk for salary in salaries]

        self.assertIn(self.own_salary.pk, salary_ids)

        self.assertNotIn(self.other_salary.pk, salary_ids)

    def test_other_employee_salary_is_not_in_dashboard_html(self):

        self.client.force_login(self.employee)

        response = self.client.get(self.salary_url())

        self.assertEqual(response.status_code, 200)

        self.assertContains(response, "حقوق کارمند اول")

        self.assertNotContains(response, "حقوق کارمند دوم")

    # ---------------------------------
    # تست فیلتر سال و ماه
    # ---------------------------------

    def test_salary_dashboard_year_month_filter(self):

        self.client.force_login(self.employee)

        response = self.client.get(
            self.salary_url(),
            {
                "year": "2026",
                "month": "5",
            }
        )

        self.assertEqual(response.status_code, 200)

        salaries = list(response.context["salaries"])

        salary_ids = [salary.pk for salary in salaries]

        self.assertIn(self.own_salary.pk, salary_ids)

        self.assertNotIn(self.old_salary.pk, salary_ids)

        self.assertNotIn(self.other_salary.pk, salary_ids)

    # ---------------------------------
    # تست خروجی Excel
    # ---------------------------------

    def test_employee_excel_contains_only_own_salary(self):

        self.client.force_login(self.employee)

        response = self.client.get(
            self.excel_url(),
            {
                "year": "2026",
                "month": "5",
            }
        )

        self.assertEqual(response.status_code, 200)

        workbook = load_workbook(
            BytesIO(response.content)
        )

        worksheet = workbook.active

        exported_values = []

        for row in worksheet.iter_rows(values_only=True):
            exported_values.extend(
                str(value)
                for value in row
                if value is not None
            )

        exported_text = " ".join(exported_values)

        self.assertIn("حقوق کارمند اول", exported_text)

        self.assertNotIn("حقوق کارمند دوم", exported_text)

        self.assertNotIn("حقوق ماه قبل", exported_text)

    # ---------------------------------
    # تست خروجی PDF و کنترل دسترسی
    # ---------------------------------

    def test_employee_can_access_own_salary_pdf(self):

        self.client.force_login(self.employee)

        response = self.client.get(
            self.pdf_url(),
            {
                "year": "2026",
                "month": "5",
            }
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response["Content-Type"],
            "application/pdf"
        )
