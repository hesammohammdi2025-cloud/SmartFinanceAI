
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),

    path(
        "organizations/",
        views.organization_list,
        name="organization_list"
    ),

    path(
        "organizations/create/",
        views.organization_create,
        name="organization_create"
    ),

    path(
        "organizations/<int:organization_id>/invite/",
        views.organization_invite,
        name="organization_invite"
    ),

    path(
        "invitations/<uuid:token>/accept/",
        views.accept_invitation,
        name="accept_invitation"
    ),

    path(
        "organizations/<int:organization_id>/members/",
        views.organization_members,
        name="organization_members"
    ),

    path(
        "organizations/<int:organization_id>/members/<int:membership_id>/update-role/",
        views.organization_member_update_role,
        name="organization_member_update_role"
    ),

    path(
        "organizations/<int:organization_id>/members/<int:membership_id>/remove/",
        views.organization_member_remove,
        name="organization_member_remove"
    ),

    path(
        "organizations/<int:organization_id>/invitations/",
        views.organization_invitations,
        name="organization_invitations"
    ),

    path(
        "organizations/<int:organization_id>/invitations/<int:invitation_id>/cancel/",
        views.organization_invitation_cancel,
        name="organization_invitation_cancel"
    ),
]
