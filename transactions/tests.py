
from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import Organization, OrganizationMembership
from transactions.models import (
    OrganizationTransaction,
    RecurringTransaction,
)


User = get_user_model()


class OrganizationTransactionPermissionTests(TestCase):

    @classmethod
    def setUpTestData(cls):

        # کاربران
        cls.owner = User.objects.create_user(
            username="org_owner",
            password="TestPassword123"
        )

        cls.admin = User.objects.create_user(
            username="org_admin",
            password="TestPassword123"
        )

        cls.manager = User.objects.create_user(
            username="org_manager",
            password="TestPassword123"
        )

        cls.accountant = User.objects.create_user(
            username="org_accountant",
            password="TestPassword123"
        )

        cls.viewer = User.objects.create_user(
            username="org_viewer",
            password="TestPassword123"
        )

        cls.outsider = User.objects.create_user(
            username="org_outsider",
            password="TestPassword123"
        )

        # سازمان
        cls.organization = Organization.objects.create(
            name="Test Organization",
            owner=cls.owner
        )

        # عضویت کاربران
        for user, role in [
            (cls.admin, "admin"),
            (cls.manager, "manager"),
            (cls.accountant, "accountant"),
            (cls.viewer, "viewer"),
        ]:
            OrganizationMembership.objects.create(
                organization=cls.organization,
                user=user,
                role=role
            )

        # تراکنش سازمانی
        cls.transaction = OrganizationTransaction.objects.create(
            organization=cls.organization,
            created_by=cls.owner,
            title="Test Income",
            amount=Decimal("100000"),
            transaction_type="income",
            category="Test",
            date=date(2026, 5, 10),
            description="Test transaction"
        )

        # برنامه تراکنش تکرارشونده سازمان
        cls.recurring = RecurringTransaction.objects.create(
            user=None,
            organization=cls.organization,
            created_by=cls.owner,
            title="Monthly Expense",
            amount=Decimal("50000"),
            transaction_type="expense",
            category="Office",
            frequency="monthly",
            start_date=date(2026, 5, 1),
            next_run_date=date(2026, 5, 1),
        )

    def login_as(self, user):
        self.client.force_login(user)

    def organization_url(self, name, **kwargs):
        return reverse(name, kwargs={
            "organization_id": self.organization.id,
            **kwargs
        })

    # ==========================================
    # Financial Read Access
    # ==========================================

    def test_viewer_cannot_access_financial_pages(self):

        self.login_as(self.viewer)

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_report_excel"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    def test_accountant_can_access_financial_pages(self):

        self.login_as(self.accountant)

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_report_excel"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_manager_can_access_financial_pages(self):

        self.login_as(self.manager)

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_report_excel"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_admin_can_access_financial_pages(self):

        self.login_as(self.admin)

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_report_excel"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_owner_can_access_financial_pages(self):

        self.login_as(self.owner)

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_report_excel"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    # ==========================================
    # Transaction Add / Edit
    # ==========================================

    def test_accountant_can_open_transaction_add_page(self):

        self.login_as(self.accountant)

        response = self.client.get(
            self.organization_url(
                "organization_transaction_add"
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_open_transaction_add_page(self):

        self.login_as(self.viewer)

        response = self.client.get(
            self.organization_url(
                "organization_transaction_add"
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_accountant_can_open_transaction_edit_page(self):

        self.login_as(self.accountant)

        response = self.client.get(
            self.organization_url(
                "organization_transaction_edit",
                pk=self.transaction.pk
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_edit_transaction(self):

        self.login_as(self.viewer)

        response = self.client.get(
            self.organization_url(
                "organization_transaction_edit",
                pk=self.transaction.pk
            )
        )

        self.assertEqual(response.status_code, 404)

    # ==========================================
    # Transaction Delete
    # ==========================================

    def test_accountant_cannot_delete_transaction(self):

        self.login_as(self.accountant)

        response = self.client.post(
            self.organization_url(
                "organization_transaction_delete",
                pk=self.transaction.pk
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            OrganizationTransaction.objects.filter(
                pk=self.transaction.pk
            ).exists()
        )

    def test_manager_can_delete_transaction(self):

        self.login_as(self.manager)

        response = self.client.post(
            self.organization_url(
                "organization_transaction_delete",
                pk=self.transaction.pk
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            OrganizationTransaction.objects.filter(
                pk=self.transaction.pk
            ).exists()
        )

    def test_viewer_cannot_delete_transaction(self):

        self.login_as(self.viewer)

        response = self.client.post(
            self.organization_url(
                "organization_transaction_delete",
                pk=self.transaction.pk
            )
        )

        self.assertEqual(response.status_code, 404)

    # ==========================================
    # Organization Recurring Transactions
    # ==========================================

    def test_accountant_can_view_recurring_transactions(self):

        self.login_as(self.accountant)

        response = self.client.get(
            self.organization_url(
                "organization_recurring_transaction_list"
            )
        )

        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_view_recurring_transactions(self):

        self.login_as(self.viewer)

        response = self.client.get(
            self.organization_url(
                "organization_recurring_transaction_list"
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_accountant_cannot_delete_recurring_transaction(self):

        self.login_as(self.accountant)

        response = self.client.post(
            self.organization_url(
                "organization_recurring_transaction_delete",
                pk=self.recurring.pk
            )
        )

        self.assertEqual(response.status_code, 404)

        self.assertTrue(
            RecurringTransaction.objects.filter(
                pk=self.recurring.pk
            ).exists()
        )

    def test_manager_can_delete_recurring_transaction(self):

        self.login_as(self.manager)

        response = self.client.post(
            self.organization_url(
                "organization_recurring_transaction_delete",
                pk=self.recurring.pk
            )
        )

        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            RecurringTransaction.objects.filter(
                pk=self.recurring.pk
            ).exists()
        )

    def test_accountant_cannot_toggle_recurring_transaction(self):

        self.login_as(self.accountant)

        response = self.client.post(
            self.organization_url(
                "organization_recurring_transaction_toggle",
                pk=self.recurring.pk
            )
        )

        self.assertEqual(response.status_code, 404)

        self.recurring.refresh_from_db()
        self.assertTrue(self.recurring.is_active)

    def test_manager_can_toggle_recurring_transaction(self):

        self.login_as(self.manager)

        response = self.client.post(
            self.organization_url(
                "organization_recurring_transaction_toggle",
                pk=self.recurring.pk
            )
        )

        self.assertEqual(response.status_code, 302)

        self.recurring.refresh_from_db()
        self.assertFalse(self.recurring.is_active)

    # ==========================================
    # Outsider Access
    # ==========================================

    def test_outsider_cannot_access_organization_pages(self):

        self.login_as(self.outsider)

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_transaction_add"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_report_excel"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    # ==========================================
    # Unauthenticated Access
    # ==========================================

    def test_unauthenticated_user_is_redirected(self):

        urls = [
            self.organization_url(
                "organization_transaction_list"
            ),
            self.organization_url(
                "organization_dashboard"
            ),
            self.organization_url(
                "organization_report"
            ),
            self.organization_url(
                "organization_recurring_transaction_list"
            ),
        ]

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
