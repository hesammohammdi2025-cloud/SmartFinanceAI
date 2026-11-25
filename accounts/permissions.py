
from django.db.models import Q

from .models import Organization, OrganizationMembership


LIMITED_ROLES = ("viewer", "employee")

MANAGEMENT_ROLES = (
    "admin",
    "manager",
    "accountant",
)


def get_user_organization(user, organization_id):
    """
    دریافت سازمان فقط در صورتی که کاربر
    مالک یا عضو آن سازمان باشد.
    """

    if not user.is_authenticated:
        return None

    return Organization.objects.filter(
        pk=organization_id,
        is_active=True
    ).filter(
        Q(owner=user) |
        Q(members__user=user)
    ).distinct().first()


def get_organization_role(user, organization_id):
    """
    دریافت نقش کاربر در سازمان.

    مالک اصلی سازمان معادل admin در نظر گرفته می‌شود.
    """

    organization = get_user_organization(
        user,
        organization_id
    )

    if organization is None:
        return None

    if organization.owner_id == user.pk:
        return "admin"

    membership = OrganizationMembership.objects.filter(
        organization=organization,
        user=user
    ).only("role").first()

    if membership is None:
        return None

    return membership.role


def is_limited_organization_member(user, organization_id):
    """
    بررسی اینکه کاربر نقش مشاهده‌گر یا کارمند ساده دارد.
    """

    role = get_organization_role(
        user,
        organization_id
    )

    return role in LIMITED_ROLES


def has_organization_role(user, organization_id, allowed_roles):
    """
    بررسی سطح دسترسی کاربر در سازمان.

    مالک اصلی سازمان معادل admin است.
    """

    if not user.is_authenticated:
        return False

    organization = get_user_organization(
        user,
        organization_id
    )

    if organization is None:
        return False

    allowed_roles = set(allowed_roles)

    # مالک اصلی سازمان نقش admin دارد.
    if organization.owner_id == user.pk:
        return "admin" in allowed_roles

    return OrganizationMembership.objects.filter(
        organization=organization,
        user=user,
        role__in=allowed_roles
    ).exists()
