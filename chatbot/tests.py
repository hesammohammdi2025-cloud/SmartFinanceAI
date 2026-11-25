
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .models import ChatMessage


class ChatbotSecurityTests(TestCase):
    """
    تست‌های امنیتی و عملکردی چت‌بات SmartFinance AI
    """

    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="TestPass123!",
        )

        self.user2 = User.objects.create_user(
            username="user2",
            password="TestPass123!",
        )

        self.chat_url = reverse("chatbot:home")

        cache.clear()

    def login_user(self, user=None):
        """
        ورود آزمایشی بدون اجرای Authentication Backend.
        برای جلوگیری از تداخل Axes در تست‌ها از force_login استفاده می‌کنیم.
        """
        self.client.force_login(user or self.user1)

    def ajax_post(self, data):
        """
        ارسال درخواست POST با هدر AJAX.
        """
        return self.client.post(
            self.chat_url,
            data,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_unauthenticated_user_cannot_access_chat(self):
        """
        کاربر واردنشده نباید به چت‌بات دسترسی داشته باشد.
        """
        response = self.client.get(self.chat_url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("accounts/login", response.url)

    def test_authenticated_user_can_open_chat(self):
        """
        کاربر واردشده باید بتواند صفحه چت را باز کند.
        """
        self.login_user()

        response = self.client.get(self.chat_url)

        self.assertEqual(response.status_code, 200)

    def test_users_cannot_see_each_others_messages(self):
        """
        تاریخچه گفت‌وگوی کاربران باید کاملاً جدا باشد.
        """

        ChatMessage.objects.create(
            user=self.user2,
            role="user",
            content="این پیام خصوصی کاربر دوم است.",
        )

        self.login_user(self.user1)

        response = self.client.get(self.chat_url)

        self.assertEqual(response.status_code, 200)

        self.assertNotContains(
            response,
            "این پیام خصوصی کاربر دوم است.",
        )

    @patch("chatbot.views.generate_ai_response")
    def test_greeting_does_not_call_openai(self, mock_ai):
        """
        پاسخ به سلام باید بدون فراخوانی API تولید شود.
        """
        self.login_user()

        response = self.ajax_post({
            "question": "سلام",
        })

        self.assertEqual(response.status_code, 200)

        mock_ai.assert_not_called()

        self.assertEqual(
            ChatMessage.objects.filter(user=self.user1).count(),
            2,
        )

    @patch("chatbot.views.generate_ai_response")
    def test_balance_question_does_not_call_openai(self, mock_ai):
        """
        محاسبه موجودی باید مستقیماً در Django انجام شود.
        """
        self.login_user()

        response = self.ajax_post({
            "question": "موجودی من چقدر است؟",
        })

        self.assertEqual(response.status_code, 200)

        mock_ai.assert_not_called()

        self.assertEqual(
            ChatMessage.objects.filter(user=self.user1).count(),
            2,
        )

    def test_empty_question_does_not_create_messages(self):
        """
        سؤال خالی نباید در تاریخچه ذخیره شود.
        """
        self.login_user()

        self.ajax_post({
            "question": "",
        })

        self.assertEqual(
            ChatMessage.objects.filter(user=self.user1).count(),
            0,
        )

    def test_question_length_is_limited(self):
        """
        سؤال بیشتر از ۲۰۰۰ کاراکتر باید رد شود.
        """
        self.login_user()

        response = self.ajax_post({
            "question": "الف" * 2001,
        })

        self.assertEqual(response.status_code, 200)

        response_text = response.content.decode("utf-8")

        self.assertIn("طول سؤال", response_text)

        self.assertEqual(
            ChatMessage.objects.filter(user=self.user1).count(),
            0,
        )

    def test_rate_limit_blocks_excess_requests(self):
        """
        درخواست یازدهم در بازه محدودیت باید با خطای 429 مواجه شود.
        """
        self.login_user()

        for i in range(10):
            response = self.ajax_post({
                "question": f"سلام شماره {i}",
            })

            self.assertEqual(response.status_code, 200)

        response = self.ajax_post({
            "question": "درخواست یازدهم",
        })

        self.assertEqual(response.status_code, 429)
