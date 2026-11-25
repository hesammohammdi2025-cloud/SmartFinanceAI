
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import models, transaction
from django.db.models import Count, Q, F
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from .forms import SignUpForm
from .models import (
    Organization,
    OrganizationMembership,
    OrganizationInvitation,
)
from .permissions import (
    get_user_organization,
    get_organization_role,
    has_organization_role,
)

from communications.models import Conversation, Message


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(
                request,
                user,
                backend="django.contrib.auth.backends.ModelBackend"
            )
            return redirect("home")

    else:
        form = SignUpForm()

    return render(
        request,
        "registration/signup.html",
        {"form": form}
    )


# ---------------------------------------
# Organization Creation Permission
# ---------------------------------------

def _can_create_organization(user):
    """
    کاربر فقط زمانی می‌تواند سازمان جدید ایجاد کند
    که عضو هیچ سازمان فعالی نباشد و دعوت‌نامه فعال نداشته باشد.
    """

    if not user.is_authenticated:
        return False

    already_in_organization = Organization.objects.filter(
        is_active=True
    ).filter(
        models.Q(owner=user) |
        models.Q(members__user=user)
    ).exists()

    if already_in_organization:
        return False

    user_email = (user.email or "").strip()

    has_pending_invitation = (
        OrganizationInvitation.objects.filter(
            email__iexact=user_email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            organization__is_active=True
        ).exists()
        if user_email else False
    )

    return not has_pending_invitation


# ---------------------------------------
# Organization List
# ---------------------------------------

@login_required
def organization_list(request):

    organizations = Organization.objects.filter(
        is_active=True
    ).filter(
        models.Q(owner=request.user) |
        models.Q(members__user=request.user)
    ).distinct().annotate(

        # پیام‌های خوانده‌نشده کارمند برای مدیر
        unread_employee_messages=Count(
            "communications__messages",
            filter=(
                Q(communications__messages__is_read=False) &
                Q(
                    communications__messages__sender_id=
                    F("communications__employee_id")
                )
            ),
            distinct=True
        ),

        # پاسخ‌های خوانده‌نشده مدیر برای کارمند
        unread_manager_messages=Count(
            "communications__messages",
            filter=(
                Q(communications__messages__is_read=False) &
                ~Q(
                    communications__messages__sender_id=
                    F("communications__employee_id")
                )
            ),
            distinct=True
        )
    )

    for organization in organizations:

        role = get_organization_role(
            request.user,
            organization.id
        )

        # نقش‌های محدود
        organization.is_limited_member = role in (
            "viewer",
            "employee"
        )

        # مدیریت اعضا و دعوت‌نامه‌ها فقط برای Admin و Owner
        organization.can_manage = has_organization_role(
            request.user,
            organization.id,
            ["admin"]
        )

        # دسترسی به بخش‌های مالی سازمان
        organization.can_view_finances = has_organization_role(
            request.user,
            organization.id,
            ["admin", "manager", "accountant"]
        )

        # مدیریت بودجه فقط برای مدیر و مالک
        organization.can_manage_budgets = has_organization_role(
            request.user,
            organization.id,
            ["admin", "manager"]
        )

        # مشاهده فهرست بودجه برای مدیر، مالک و حسابدار
        organization.can_view_budgets = has_organization_role(
            request.user,
            organization.id,
            ["admin", "manager", "accountant"]
        )

        # حقوق شخصی فقط برای Viewer و Employee
        organization.can_view_salary = (
            role in ("viewer", "employee")
        )

        # ارتباط با مدیر برای Viewer و Employee
        organization.can_contact_manager = (
            role in ("viewer", "employee")
        )

        # تعداد پیام‌های خوانده‌نشده متناسب با نقش
        if role in ("viewer", "employee"):
            organization.unread_messages_count = (
                organization.unread_manager_messages
            )

        elif role in ("admin", "manager"):
            organization.unread_messages_count = (
                organization.unread_employee_messages
            )

        else:
            organization.unread_messages_count = 0

    user_email = (request.user.email or "").strip()

    pending_invitations = (
        OrganizationInvitation.objects.filter(
            email__iexact=user_email,
            accepted_at__isnull=True,
            revoked_at__isnull=True,
            expires_at__gt=timezone.now(),
            organization__is_active=True
        ).select_related(
            "organization",
            "invited_by"
        ).order_by("-created_at")
        if user_email
        else OrganizationInvitation.objects.none()
    )

    return render(
        request,
        "accounts/organization_list.html",
        {
            "organizations": organizations,
            "pending_invitations": pending_invitations,
            "can_create_organization": _can_create_organization(
                request.user
            ),
        }
    )


# ---------------------------------------
# Create Organization
# ---------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def organization_create(request):

    if not _can_create_organization(request.user):
        messages.error(
            request,
            "شما عضو یک سازمان هستید یا دعوت‌نامه فعالی دارید؛ "
            "امکان ایجاد سازمان جدید برای شما وجود ندارد."
        )
        return redirect("accounts:organization_list")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()

        if not name:
            messages.error(
                request,
                "نام سازمان را وارد کنید."
            )

        elif len(name) > 200:
            messages.error(
                request,
                "نام سازمان نباید بیشتر از ۲۰۰ کاراکتر باشد."
            )

        else:
            with transaction.atomic():

                organization = Organization.objects.create(
                    name=name,
                    owner=request.user
                )

                OrganizationMembership.objects.create(
                    organization=organization,
                    user=request.user,
                    role="admin"
                )

            messages.success(
                request,
                "سازمان با موفقیت ایجاد شد."
            )

            return redirect("accounts:organization_list")

    return render(
        request,
        "accounts/organization_create.html"
    )


# ---------------------------------------
# Organization Invitation
# ---------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def organization_invite(request, organization_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        messages.error(
            request,
            "سازمان موردنظر پیدا نشد یا اجازه دسترسی ندارید."
        )
        return redirect("accounts:organization_list")

    if not has_organization_role(
        request.user,
        organization_id,
        ["admin"]
    ):
        messages.error(
            request,
            "فقط مدیر سازمان اجازه دعوت عضو را دارد."
        )
        return redirect("accounts:organization_list")

    if request.method == "POST":

        email = request.POST.get("email", "").strip().lower()
        role = request.POST.get("role", "viewer")

        allowed_roles = [
            "manager",
            "accountant",
            "viewer",
            "employee",
        ]

        if not email:
            messages.error(
                request,
                "ایمیل را وارد کنید."
            )

        elif role not in allowed_roles:
            messages.error(
                request,
                "نقش انتخاب‌شده معتبر نیست."
            )

        elif (
            request.user.email
            and email == request.user.email.strip().lower()
        ):
            messages.error(
                request,
                "شما مالک این سازمان هستید و نیازی به دعوت خودتان ندارید."
            )

        else:

            User = get_user_model()

            invited_user = User.objects.filter(
                email__iexact=email
            ).first()

            if invited_user:

                existing_membership = OrganizationMembership.objects.filter(
                    organization=organization,
                    user=invited_user
                ).exists()

                if existing_membership:
                    messages.error(
                        request,
                        "این کاربر هم‌اکنون عضو سازمان است."
                    )
                    return redirect(
                        "accounts:organization_invite",
                        organization_id=organization.id
                    )

            existing_invitation = OrganizationInvitation.objects.filter(
                organization=organization,
                email__iexact=email,
                accepted_at__isnull=True,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now()
            ).exists()

            if existing_invitation:
                messages.error(
                    request,
                    "برای این ایمیل قبلاً دعوت‌نامه فعال صادر شده است."
                )

            else:

                invitation = OrganizationInvitation.objects.create(
                    organization=organization,
                    email=email,
                    role=role,
                    invited_by=request.user,
                    expires_at=timezone.now() + timedelta(days=7)
                )

                invitation_path = reverse(
                    "accounts:accept_invitation",
                    kwargs={"token": invitation.token}
                )

                invitation_link = request.build_absolute_uri(
                    invitation_path
                )

                try:

                    send_mail(
                        subject=f"دعوت به عضویت در {organization.name}",
                        message=(
                            f"شما به سازمان {organization.name} دعوت شده‌اید.\n\n"
                            f"نقش شما: {invitation.get_role_display()}\n\n"
                            f"برای پذیرش دعوت، پس از ورود به حساب کاربری "
                            f"خود، این لینک را باز کنید:\n"
                            f"{invitation_link}\n\n"
                            f"این دعوت‌نامه تا ۷ روز اعتبار دارد."
                        ),
                        from_email=getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            None
                        ),
                        recipient_list=[email],
                        fail_silently=False
                    )

                    messages.success(
                        request,
                        "دعوت‌نامه با موفقیت ارسال شد."
                    )

                except Exception:

                    invitation.delete()

                    messages.error(
                        request,
                        "ارسال ایمیل ناموفق بود. تنظیمات ایمیل را بررسی کنید."
                    )

                return redirect(
                    "accounts:organization_invite",
                    organization_id=organization.id
                )

    return render(
        request,
        "accounts/organization_invite.html",
        {"organization": organization}
    )


# ---------------------------------------
# Accept Organization Invitation
# ---------------------------------------

@login_required
@require_http_methods(["GET", "POST"])
def accept_invitation(request, token):

    with transaction.atomic():

        invitation = get_object_or_404(
            OrganizationInvitation.objects.select_for_update().select_related(
                "organization"
            ),
            token=token
        )

        if invitation.accepted_at is not None:
            messages.error(
                request,
                "این دعوت‌نامه قبلاً استفاده شده است."
            )
            return redirect("accounts:organization_list")

        if invitation.revoked_at is not None:
            messages.error(
                request,
                "این دعوت‌نامه توسط مدیر سازمان لغو شده است."
            )
            return redirect("accounts:organization_list")

        if invitation.is_expired:
            messages.error(
                request,
                "اعتبار این دعوت‌نامه به پایان رسیده است."
            )
            return redirect("accounts:organization_list")

        if not invitation.organization.is_active:
            messages.error(
                request,
                "این سازمان غیرفعال است."
            )
            return redirect("accounts:organization_list")

        user_email = (request.user.email or "").strip().lower()

        if user_email != invitation.email.strip().lower():
            messages.error(
                request,
                "این دعوت‌نامه برای ایمیل حساب کاربری شما صادر نشده است."
            )
            return redirect("accounts:organization_list")

        if OrganizationMembership.objects.filter(
            organization=invitation.organization,
            user=request.user
        ).exists():
            messages.error(
                request,
                "شما قبلاً عضو این سازمان هستید."
            )
            return redirect("accounts:organization_list")

        if request.method == "POST":

            OrganizationMembership.objects.create(
                organization=invitation.organization,
                user=request.user,
                role=invitation.role
            )

            invitation.accepted_at = timezone.now()
            invitation.save(update_fields=["accepted_at"])

            messages.success(
                request,
                "با موفقیت به سازمان پیوستید."
            )

            return redirect("accounts:organization_list")

    return render(
        request,
        "accounts/accept_invitation.html",
        {"invitation": invitation}
    )


# ---------------------------------------
# Organization Members Management
# ---------------------------------------

@login_required
def organization_members(request, organization_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        messages.error(
            request,
            "سازمان موردنظر پیدا نشد یا اجازه دسترسی ندارید."
        )
        return redirect("accounts:organization_list")

    # فقط Admin، مالک اصلی و Manager اجازه مشاهده فهرست اعضا را دارند.
    role = get_organization_role(
        request.user,
        organization_id
    )

    if role not in ("admin", "manager"):
        messages.error(
            request,
            "شما اجازه مشاهده فهرست اعضای سازمان را ندارید."
        )
        return redirect("accounts:organization_list")

    memberships = OrganizationMembership.objects.filter(
        organization=organization
    ).select_related("user").order_by("joined_at")

    return render(
        request,
        "accounts/organization_members.html",
        {
            "organization": organization,
            "memberships": memberships,
            "is_admin": role == "admin",
            "is_manager": role == "manager",
            "is_owner": organization.owner_id == request.user.pk,
        }
    )


@login_required
@require_POST
def organization_member_update_role(
    request,
    organization_id,
    membership_id
):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        messages.error(
            request,
            "دسترسی به سازمان امکان‌پذیر نیست."
        )
        return redirect("accounts:organization_list")

    if not has_organization_role(
        request.user,
        organization_id,
        ["admin"]
    ):
        messages.error(
            request,
            "اجازه تغییر نقش اعضا را ندارید."
        )
        return redirect(
            "accounts:organization_members",
            organization_id=organization_id
        )

    membership = get_object_or_404(
        OrganizationMembership.objects.select_related("user"),
        pk=membership_id,
        organization=organization
    )

    if membership.user_id == organization.owner_id:
        messages.error(
            request,
            "نقش مالک اصلی سازمان قابل تغییر نیست."
        )
        return redirect(
            "accounts:organization_members",
            organization_id=organization_id
        )

    if (
        membership.role == "admin"
        and organization.owner_id != request.user.pk
    ):
        messages.error(
            request,
            "فقط مالک اصلی سازمان می‌تواند نقش مدیر دیگر را تغییر دهد."
        )
        return redirect(
            "accounts:organization_members",
            organization_id=organization_id
        )

    new_role = request.POST.get("role", "").strip()

    allowed_roles = [
        "manager",
        "accountant",
        "viewer",
        "employee",
    ]

    if new_role not in allowed_roles:
        messages.error(
            request,
            "نقش انتخاب‌شده معتبر نیست."
        )

    else:
        membership.role = new_role
        membership.save(update_fields=["role"])

        messages.success(
            request,
            "نقش عضو با موفقیت تغییر کرد."
        )

    return redirect(
        "accounts:organization_members",
        organization_id=organization_id
    )


@login_required
@require_POST
def organization_member_remove(
    request,
    organization_id,
    membership_id
):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        messages.error(
            request,
            "دسترسی به سازمان امکان‌پذیر نیست."
        )
        return redirect("accounts:organization_list")

    if not has_organization_role(
        request.user,
        organization_id,
        ["admin"]
    ):
        messages.error(
            request,
            "اجازه حذف اعضا را ندارید."
        )
        return redirect(
            "accounts:organization_members",
            organization_id=organization_id
        )

    membership = get_object_or_404(
        OrganizationMembership.objects.select_related("user"),
        pk=membership_id,
        organization=organization
    )

    if membership.user_id == organization.owner_id:
        messages.error(
            request,
            "مالک اصلی سازمان قابل حذف نیست."
        )

    elif (
        membership.role == "admin"
        and organization.owner_id != request.user.pk
    ):
        messages.error(
            request,
            "فقط مالک اصلی سازمان می‌تواند مدیر دیگر را حذف کند."
        )

    else:
        membership.delete()

        messages.success(
            request,
            "عضو با موفقیت از سازمان حذف شد."
        )

    return redirect(
        "accounts:organization_members",
        organization_id=organization_id
    )


# ---------------------------------------
# Organization Invitations Management
# ---------------------------------------

@login_required
def organization_invitations(request, organization_id):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        messages.error(
            request,
            "سازمان موردنظر پیدا نشد یا اجازه دسترسی ندارید."
        )
        return redirect("accounts:organization_list")

    if not has_organization_role(
        request.user,
        organization_id,
        ["admin"]
    ):
        messages.error(
            request,
            "فقط مدیر سازمان اجازه مشاهده دعوت‌نامه‌ها را دارد."
        )
        return redirect("accounts:organization_list")

    invitations = OrganizationInvitation.objects.filter(
        organization=organization
    ).select_related(
        "invited_by"
    ).order_by("-created_at")

    return render(
        request,
        "accounts/organization_invitations.html",
        {
            "organization": organization,
            "invitations": invitations,
        }
    )


@login_required
@require_POST
def organization_invitation_cancel(
    request,
    organization_id,
    invitation_id
):

    organization = get_user_organization(
        request.user,
        organization_id
    )

    if organization is None:
        messages.error(
            request,
            "دسترسی به سازمان امکان‌پذیر نیست."
        )
        return redirect("accounts:organization_list")

    if not has_organization_role(
        request.user,
        organization_id,
        ["admin"]
    ):
        messages.error(
            request,
            "فقط مدیر سازمان اجازه لغو دعوت‌نامه را دارد."
        )
        return redirect(
            "accounts:organization_invitations",
            organization_id=organization_id
        )

    invitation = get_object_or_404(
        OrganizationInvitation,
        pk=invitation_id,
        organization=organization
    )

    if invitation.accepted_at is not None:
        messages.error(
            request,
            "دعوت‌نامه پذیرفته‌شده قابل لغو نیست."
        )

    elif invitation.revoked_at is not None:
        messages.warning(
            request,
            "این دعوت‌نامه قبلاً لغو شده است."
        )

    elif invitation.is_expired:
        messages.warning(
            request,
            "اعتبار این دعوت‌نامه قبلاً به پایان رسیده است."
        )

    else:
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["revoked_at"])

        messages.success(
            request,
            "دعوت‌نامه با موفقیت لغو شد."
        )

    return redirect(
        "accounts:organization_invitations",
        organization_id=organization_id
    )
