
from django import forms

from .models import Budget, OrganizationBudget


# ==========================================
# Shared Choices
# ==========================================

CATEGORY_CHOICES = [
    ("غذا", "غذا"),
    ("حمل‌ونقل", "حمل‌ونقل"),
    ("خرید", "خرید"),
    ("قبوض", "قبوض"),
    ("تفریح", "تفریح"),
    ("سلامت", "سلامت"),
    ("سایر", "سایر"),
]


MONTH_CHOICES = [
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


# ==========================================
# Personal Budget Form
# ==========================================

class BudgetForm(forms.ModelForm):

    class Meta:
        model = Budget
        fields = ["category", "amount", "year", "month"]

        labels = {
            "category": "دسته‌بندی هزینه",
            "amount": "مبلغ بودجه",
            "year": "سال",
            "month": "ماه",
        }

        widgets = {
            "category": forms.Select(
                choices=CATEGORY_CHOICES,
                attrs={"class": "form-control"},
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "مثلاً 5000000",
                }
            ),

            "year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "2020",
                    "max": "2100",
                }
            ),

            "month": forms.Select(
                choices=MONTH_CHOICES,
                attrs={"class": "form-control"},
            ),
        }


# ==========================================
# Organization Budget Form
# ==========================================

class OrganizationBudgetForm(forms.ModelForm):

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.organization = organization

    def clean(self):

        cleaned_data = super().clean()

        category = cleaned_data.get("category")
        year = cleaned_data.get("year")
        month = cleaned_data.get("month")

        if self.organization and category and year and month:

            budgets = OrganizationBudget.objects.filter(
                organization=self.organization,
                category=category,
                year=year,
                month=month,
            )

            # هنگام ویرایش، بودجه فعلی را از بررسی خارج می‌کنیم
            if self.instance.pk:
                budgets = budgets.exclude(
                    pk=self.instance.pk
                )

            if budgets.exists():
                raise forms.ValidationError(
                    "برای این دسته‌بندی در این ماه و سال، "
                    "قبلاً بودجه ثبت شده است."
                )

        return cleaned_data

    class Meta:
        model = OrganizationBudget
        fields = ["category", "amount", "year", "month"]

        labels = {
            "category": "دسته‌بندی هزینه",
            "amount": "مبلغ بودجه سازمان",
            "year": "سال",
            "month": "ماه",
        }

        widgets = {
            "category": forms.Select(
                choices=CATEGORY_CHOICES,
                attrs={"class": "form-control"},
            ),

            "amount": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "مثلاً 50000000",
                }
            ),

            "year": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "2020",
                    "max": "2100",
                }
            ),

            "month": forms.Select(
                choices=MONTH_CHOICES,
                attrs={"class": "form-control"},
            ),
        }
