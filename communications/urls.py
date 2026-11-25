
from django.urls import path

from . import views


urlpatterns = [
    # گفتگوی اختصاصی کارمند و مشاهده‌گر
    path(
        "organizations/<int:organization_id>/conversation/",
        views.employee_conversation,
        name="employee_conversation"
    ),

    # فهرست گفتگوهای مدیر
    path(
        "organizations/<int:organization_id>/conversations/",
        views.manager_conversations,
        name="manager_conversations"
    ),

    # مشاهده و پاسخ به گفتگوی کارمند
    path(
        "organizations/<int:organization_id>/conversations/<int:conversation_id>/",
        views.manager_conversation_detail,
        name="manager_conversation_detail"
    ),
]
