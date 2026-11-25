
from datetime import datetime

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q


from django.utils import timezone
from datetime import date


from .models import (
    Transaction,
    OrganizationTransaction,
    RecurringTransaction,
)

from accounts.models import OrganizationMembership

from utils.jalali import (
    jalali_to_gregorian,
    gregorian_to_jalali,
)


User = get_user_model()


# ==========================================
# Jalali Date Field
# ==========================================

class JalaliDateField(forms.Field):

    widget = forms.TextInput

    def __init__(self, *args, **kwargs):

        kwargs.setdefault(
            "widget",
            forms.TextInput(attrs={
                "class": "jalali-date-input",
                "placeholder": "مثلاً 1405/08/22",
                "autocomplete": "off",
                "dir": "ltr",
            })
        )

        super().__init__(*args, **kwargs)

    def to_python(self, value):

        if not value:
            return None

        try:

            value = value.strip().replace("/", "-")
            value = " ".join(value.split())

            return jalali_to_gregorian(value)

        except (ValueError, TypeError):

            raise ValidationError(
                "تاریخ شمسی معتبر نیست. نمونه: 1405/08/22"
            )

    def prepare_value(self, value):

        if not value:
            return ""

        if isinstance(value, str):
            try:
                value = date.fromisoformat(value)
            except ValueError:
                return value

        return gregorian_to_jalali(value)


# ==========================================
# Jalali DateTime Field
# ==========================================

class JalaliDateTimeField(forms.Field):

    widget = forms.TextInput

    def __init__(self, *args, **kwargs):

        kwargs.setdefault(
            "widget",
            forms.TextInput(attrs={
                "class": "jalali-datetime-input",
                "placeholder": "1405/08/22 14:30",
                "autocomplete": "off",
                "dir": "ltr",
            })
        )

        super().__init__(*args, **kwargs)

    def to_python(self, value):

        if not value:
            return None

        try:

            value = " ".join(
                value.strip().replace("T", " ").split()
            )

            date_part, time_part = value.split()

            gregorian_date = jalali_to_gregorian(
                date_part.replace("/", "-")
            )

            parsed_time = datetime.strptime(
                time_part,
                "%H:%M"
            ).time()

            result = datetime.combine(
                gregorian_date,
                parsed_time
            )

            if settings.USE_TZ:

                result = timezone.make_aware(
                    result,
                    timezone.get_current_timezone()
                )

            return result

        except (ValueError, TypeError):

            raise ValidationError(
                "تاریخ و ساعت معتبر نیست. نمونه: 1405/08/22 14:30"
            )

    def prepare_value(self, value):

        if not value:
            return ""

        # تبدیل رشته به datetime در صورت نیاز
        if isinstance(value, str):

            try:
                value = datetime.fromisoformat(
                    value.strip().replace(" ", "T", 1)
                )

            except ValueError:
                return value

        # فقط datetime را به توابع timezone ارسال می‌کنیم
        if not isinstance(value, datetime):
            return value

        if settings.USE_TZ and timezone.is_aware(value):

            value = timezone.localtime(value)

        jalali_date = gregorian_to_jalali(
            value.date()
        )

        return f"{jalali_date} {value.strftime('%H:%M')}"


# ==========================================
# Personal Transaction Form
# ==========================================

class TransactionForm(forms.ModelForm):

    date = JalaliDateField(
        label="تاریخ تراکنش"
    )

    class Meta:

        model = Transaction

        fields = [
            "title",
            "amount",
            "transaction_type",
            "category",
            "date",
            "description",
        ]

        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3}
            ),
        }


# ==========================================
# Organization Transaction Form
# ==========================================

class OrganizationTransactionForm(forms.ModelForm):

    date = JalaliDateField(
        label="تاریخ تراکنش"
    )

    paid_at = JalaliDateTimeField(
        label="تاریخ و ساعت پرداخت واقعی",
        required=False,
    )

    class Meta:

        model = OrganizationTransaction

        fields = [
            "title",
            "amount",
            "transaction_type",
            "category",
            "date",
            "description",
            "is_salary",
            "recipient",
            "paid_at",
        ]

        labels = {
            "title": "عنوان تراکنش",
            "amount": "مبلغ",
            "transaction_type": "نوع تراکنش",
            "category": "دسته‌بندی",
            "date": "تاریخ تراکنش",
            "description": "توضیحات",
            "is_salary": "این هزینه بابت پرداخت حقوق است",
            "recipient": "کارمند دریافت‌کننده حقوق",
            "paid_at": "تاریخ و ساعت پرداخت واقعی",
        }

        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3}
            ),

            "is_salary": forms.CheckboxInput(),
        }

    def __init__(self, *args, organization=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.organization = organization

        if organization is not None:

            member_ids = OrganizationMembership.objects.filter(
                organization=organization
            ).values_list(
                "user_id",
                flat=True
            )

            self.fields["recipient"].queryset = User.objects.filter(
                Q(pk__in=member_ids) |
                Q(pk=organization.owner_id)
            ).distinct().order_by("username")

        else:

            self.fields["recipient"].queryset = User.objects.none()

        self.fields["recipient"].required = False

        self.fields["paid_at"].required = False

        self.fields["recipient"].empty_label = "انتخاب کارمند"

    def clean(self):

        cleaned_data = super().clean()

        transaction_type = cleaned_data.get("transaction_type")

        is_salary = cleaned_data.get("is_salary")

        recipient = cleaned_data.get("recipient")

        paid_at = cleaned_data.get("paid_at")

        if is_salary:

            if transaction_type != "expense":

                self.add_error(
                    "transaction_type",
                    "پرداخت حقوق فقط باید از نوع هزینه باشد."
                )

            if recipient is None:

                self.add_error(
                    "recipient",
                    "برای پرداخت حقوق باید کارمند دریافت‌کننده را انتخاب کنید."
                )

            if paid_at is None:

                self.add_error(
                    "paid_at",
                    "تاریخ و ساعت پرداخت حقوق الزامی است."
                )

            if recipient is not None and self.organization is not None:

                is_member = (
                    recipient.pk == self.organization.owner_id
                    or OrganizationMembership.objects.filter(
                        organization=self.organization,
                        user=recipient
                    ).exists()
                )

                if not is_member:

                    self.add_error(
                        "recipient",
                        "این کاربر عضو سازمان موردنظر نیست."
                    )

        else:

            cleaned_data["recipient"] = None

            cleaned_data["paid_at"] = None

        return cleaned_data


# ==========================================
# Recurring Transaction Form
# ==========================================

class RecurringTransactionForm(forms.ModelForm):

    start_date = JalaliDateField(
        label="تاریخ شروع"
    )

    end_date = JalaliDateField(
        label="تاریخ پایان",
        required=False,
    )

    class Meta:

        model = RecurringTransaction

        fields = [
            "title",
            "amount",
            "transaction_type",
            "category",
            "description",
            "frequency",
            "start_date",
            "end_date",
        ]

        labels = {
            "title": "عنوان تراکنش",
            "amount": "مبلغ",
            "transaction_type": "نوع تراکنش",
            "category": "دسته‌بندی",
            "description": "توضیحات",
            "frequency": "دوره تکرار",
            "start_date": "تاریخ شروع",
            "end_date": "تاریخ پایان",
        }

        widgets = {

            "title": forms.TextInput(
                attrs={
                    "placeholder": "مثلاً اجاره ماهانه"
                }
            ),

            "amount": forms.NumberInput(
                attrs={
                    "placeholder": "مبلغ تراکنش",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "توضیحات اختیاری",
                }
            ),
        }

    def clean(self):

        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")

        end_date = cleaned_data.get("end_date")

        if start_date and end_date and end_date < start_date:

            self.add_error(
                "end_date",
                "تاریخ پایان نمی‌تواند قبل از تاریخ شروع باشد."
            )

        return cleaned_data
