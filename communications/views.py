
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q, F
from django.shortcuts import render, redirect, get_object_or_404

from accounts.permissions import (
    get_user_organization,
    get_organization_role,
)

from .models import Conversation, Message


LIMITED_ROLES = ("viewer", "employee")
MANAGER_ROLES = ("admin", "manager")


def _get_conversation_access(user, organization_id):
    """
    تعیین سطح دسترسی کاربر به پیام‌رسان سازمان.
    """

    organization = get_user_organization(
        user,
        organization_id
    )

    if organization is None:
        return None, None

    role = get_organization_role(
        user,
        organization_id
    )

    if role not in LIMITED_ROLES + MANAGER_ROLES:
        return organization, None

    return organization, role


def _get_or_create_employee_conversation(organization, user):
    """
    دریافت یا ایجاد گفتگوی اختصاصی کارمند.
    """

    conversation, _ = Conversation.objects.get_or_create(
        organization=organization,
        employee=user
    )

    return conversation


@login_required
def employee_conversation(request, organization_id):
    """
    صفحه گفتگوی اختصاصی کارمند یا مشاهده‌گر.
    """

    organization, role = _get_conversation_access(
        request.user,
        organization_id
    )

    if organization is None or role not in LIMITED_ROLES:
        messages.error(
            request,
            "شما اجازه دسترسی به این بخش را ندارید."
        )
        return redirect("accounts:organization_list")

    conversation = _get_or_create_employee_conversation(
        organization,
        request.user
    )

    if request.method == "POST":
        body = request.POST.get("body", "").strip()

        if not body:
            messages.error(
                request,
                "متن پیام را وارد کنید."
            )

        elif len(body) > 5000:
            messages.error(
                request,
                "متن پیام نباید بیشتر از ۵۰۰۰ کاراکتر باشد."
            )

        else:
            with transaction.atomic():
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    body=body
                )

                conversation.save(update_fields=["updated_at"])

            messages.success(
                request,
                "پیام شما با موفقیت ارسال شد."
            )

            return redirect(
                "employee_conversation",
                organization_id=organization.id
            )

    unread_manager_messages = conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    )

    unread_manager_messages.update(is_read=True)

    conversation_messages = conversation.messages.select_related(
        "sender"
    ).all()

    return render(
        request,
        "communications/employee_conversation.html",
        {
            "organization": organization,
            "conversation": conversation,
            "conversation_messages": conversation_messages,
        }
    )


@login_required
def manager_conversations(request, organization_id):
    """
    فهرست گفتگوهای کارکنان برای مدیر سازمان
    همراه با تعداد پیام‌های خوانده‌نشده.
    """

    organization, role = _get_conversation_access(
        request.user,
        organization_id
    )

    if organization is None or role not in MANAGER_ROLES:
        messages.error(
            request,
            "شما اجازه مشاهده گفتگوهای کارکنان را ندارید."
        )
        return redirect("accounts:organization_list")

    conversations = Conversation.objects.filter(
        organization=organization
    ).select_related(
        "employee"
    ).annotate(
        unread_count=Count(
            "messages",
            filter=Q(
                messages__is_read=False,
                messages__sender=F("employee")
            )
        )
    ).order_by("-updated_at")

    total_unread_messages = sum(
        conversation.unread_count
        for conversation in conversations
    )

    return render(
        request,
        "communications/manager_conversations.html",
        {
            "organization": organization,
            "conversations": conversations,
            "total_unread_messages": total_unread_messages,
        }
    )


@login_required
def manager_conversation_detail(
    request,
    organization_id,
    conversation_id
):
    """
    مشاهده و پاسخ به گفتگوی یک کارمند.
    """

    organization, role = _get_conversation_access(
        request.user,
        organization_id
    )

    if organization is None or role not in MANAGER_ROLES:
        messages.error(
            request,
            "شما اجازه دسترسی به این گفتگو را ندارید."
        )
        return redirect("accounts:organization_list")

    conversation = get_object_or_404(
        Conversation.objects.select_related("employee"),
        pk=conversation_id,
        organization=organization
    )

    if request.method == "POST":
        body = request.POST.get("body", "").strip()

        if not body:
            messages.error(
                request,
                "متن پاسخ را وارد کنید."
            )

        elif len(body) > 5000:
            messages.error(
                request,
                "متن پاسخ نباید بیشتر از ۵۰۰۰ کاراکتر باشد."
            )

        else:
            with transaction.atomic():
                Message.objects.create(
                    conversation=conversation,
                    sender=request.user,
                    body=body
                )

                conversation.save(update_fields=["updated_at"])

            messages.success(
                request,
                "پاسخ شما با موفقیت ارسال شد."
            )

            return redirect(
                "manager_conversation_detail",
                organization_id=organization.id,
                conversation_id=conversation.id
            )

    conversation.messages.filter(
        is_read=False
    ).exclude(
        sender=request.user
    ).update(is_read=True)

    conversation_messages = conversation.messages.select_related(
        "sender"
    ).all()

    return render(
        request,
        "communications/manager_conversation_detail.html",
        {
            "organization": organization,
            "conversation": conversation,
            "conversation_messages": conversation_messages,
        }
    )
