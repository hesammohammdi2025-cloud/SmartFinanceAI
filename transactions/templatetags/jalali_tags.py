
from django import template
from utils.jalali import gregorian_to_jalali

register = template.Library()


@register.filter
def jalali_date(value):
    if not value:
        return ""

    try:
        return gregorian_to_jalali(value)
    except (ValueError, TypeError):
        return value


@register.filter
def jalali_datetime(value):
    if not value:
        return ""

    try:
        from django.utils import timezone

        if timezone.is_aware(value):
            value = timezone.localtime(value)

        return (
            gregorian_to_jalali(value.date())
            + " "
            + value.strftime("%H:%M")
        )
    except (ValueError, TypeError, AttributeError):
        return value
