
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from .ai_service import generate_ai_response


@override_settings(
    OPENAI_API_KEY="test-api-key",
    OPENAI_MODEL="gpt-4.1-mini",
)
class AIServiceTests(SimpleTestCase):

    @patch("chatbot.ai_service.OpenAI")
    def test_successful_response(self, mock_openai):

        mock_client = mock_openai.return_value

        mock_client.responses.create.return_value = SimpleNamespace(
            output_text="سلام! این یک پاسخ آزمایشی است."
        )

        result = generate_ai_response(
            question="چگونه هزینه‌هایم را مدیریت کنم؟"
        )

        self.assertEqual(
            result,
            "سلام! این یک پاسخ آزمایشی است."
        )

        mock_client.responses.create.assert_called_once()

    @patch("chatbot.ai_service.OpenAI")
    def test_empty_question_is_rejected(self, mock_openai):

        with self.assertRaises(ValueError):
            generate_ai_response("")

        mock_openai.assert_not_called()

    @patch("chatbot.ai_service.OpenAI")
    def test_long_question_is_rejected(self, mock_openai):

        question = "الف" * 2001

        with self.assertRaises(ValueError):
            generate_ai_response(question)

        mock_openai.assert_not_called()

    @patch("chatbot.ai_service.OpenAI")
    def test_missing_api_key_is_rejected(self, mock_openai):

        with override_settings(OPENAI_API_KEY=""):

            with self.assertRaises(ValueError):
                generate_ai_response("سلام")

        mock_openai.assert_not_called()

    @patch("chatbot.ai_service.OpenAI")
    def test_invalid_history_role_is_ignored(self, mock_openai):

        mock_client = mock_openai.return_value

        mock_client.responses.create.return_value = SimpleNamespace(
            output_text="پاسخ آزمایشی"
        )

        history = [
            {
                "role": "system",
                "content": "دستور غیرمجاز"
            },
            {
                "role": "user",
                "content": "سلام"
            },
            {
                "role": "assistant",
                "content": "سلام، چطور می‌توانم کمک کنم؟"
            },
        ]

        generate_ai_response(
            question="سؤال جدید",
            conversation_history=history,
        )

        call_args = mock_client.responses.create.call_args

        sent_messages = call_args.kwargs["input"]

        self.assertEqual(len(sent_messages), 3)

        self.assertEqual(
            sent_messages[0]["role"],
            "user"
        )

        self.assertEqual(
            sent_messages[1]["role"],
            "assistant"
        )

        self.assertEqual(
            sent_messages[2]["role"],
            "user"
        )
