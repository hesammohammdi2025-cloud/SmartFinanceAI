
import jdatetime
from datetime import date, datetime


def jalali_to_gregorian(value):
    """
    Convert Jalali date string (YYYY-MM-DD)
    to Python Gregorian date.
    """
    if not value:
        return None

    try:
        year, month, day = map(int, value.split("-"))
        return jdatetime.date(
            year, month, day
        ).togregorian()
    except (ValueError, TypeError):
        raise ValueError("تاریخ شمسی واردشده معتبر نیست.")


def gregorian_to_jalali(value):
    if not value:
        return ""

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            try:
                value = date.fromisoformat(value)
            except ValueError:
                return value

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        value = jdatetime.date.fromgregorian(date=value)

    return value.strftime("%Y/%m/%d")