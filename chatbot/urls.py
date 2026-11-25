from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path(
        '',
        views.chat_home,
        name='home',
    ),

    path(
        'confirm-organization-deletion/',
        views.confirm_organization_transaction_deletion,
        name='confirm_organization_deletion',
    ),
]