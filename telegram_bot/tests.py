from unittest.mock import Mock, patch

import requests
from django.test import TestCase, override_settings
from django.utils import timezone

from habits.models import Habit
from telegram_bot.tasks import send_habit_reminders
from users.models import User
from telegram_bot.services import (
    TelegramAPIError,
    send_telegram_message,
)
from datetime import datetime, timedelta

class TelegramServiceTests(TestCase):
    @override_settings(TELEGRAM_BOT_TOKEN="test-token")
    @patch("telegram_bot.services.requests.post")
    def test_send_telegram_message(self, mock_post):
        response = Mock()
        response.json.return_value = {"ok": True}
        mock_post.return_value = response

        result = send_telegram_message(
            chat_id=123456789,
            text="Тест",
        )

        self.assertTrue(result["ok"])
        response.raise_for_status.assert_called_once()

        mock_post.assert_called_once_with(
            (
                "https://api.telegram.org/"
                "bottest-token/sendMessage"
            ),
            json={
                "chat_id": 123456789,
                "text": "Тест",
            },
            timeout=10,
        )

    @override_settings(TELEGRAM_BOT_TOKEN="")
    @patch("telegram_bot.services.requests.post")
    def test_missing_token(self, mock_post):
        with self.assertRaises(TelegramAPIError):
            send_telegram_message(123456789, "Тест")

        mock_post.assert_not_called()

    @override_settings(TELEGRAM_BOT_TOKEN="test-token")
    @patch("telegram_bot.services.requests.post")
    def test_telegram_rejects_message(self, mock_post):
        mock_post.return_value.json.return_value = {
            "ok": False,
            "description": "Bad Request",
        }

        with self.assertRaises(TelegramAPIError):
            send_telegram_message(123456789, "Тест")

    @override_settings(TELEGRAM_BOT_TOKEN="test-token")
    @patch(
        "telegram_bot.services.requests.post",
        side_effect=requests.Timeout,
    )
    def test_network_timeout(self, mock_post):
        with self.assertRaises(TelegramAPIError):
            send_telegram_message(123456789, "Тест")


class TelegramTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="telegram@example.com",
            password="StrongPass!4826",
            telegram_chat_id=123456789,
        )

        self.now = timezone.make_aware(
            datetime(2026, 9, 13, 12, 0),
            timezone.get_current_timezone(),
        )

        original_localtime = timezone.localtime

        def fixed_localtime(value=None, timezone=None):
            if value is None:
                return self.now
            return original_localtime(value, timezone)

        clock = patch(
            "telegram_bot.tasks.timezone.localtime",
            side_effect=fixed_localtime,
        )
        clock.start()
        self.addCleanup(clock.stop)

        now = self.now

        self.habit = Habit.objects.create(
            user=self.user,
            place="Дома",
            time=now.time().replace(
                second=0,
                microsecond=0,
                tzinfo=None,
            ),
            action="Сделать зарядку",
            is_pleasant=False,
            periodicity=1,
            reward="Выпить кофе",
            duration=60,
            is_public=False,
        )

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_reminder_is_sent(self, mock_send):
        result = send_habit_reminders()

        self.assertEqual(result, 1)
        mock_send.assert_called_once()

        self.habit.refresh_from_db()
        self.assertIsNotNone(
            self.habit.last_reminder_at
        )

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_reminder_is_not_sent_twice(self, mock_send):
        self.habit.last_reminder_at = self.now
        self.habit.save(
            update_fields=["last_reminder_at"]
        )

        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_not_called()

    @patch(
        "telegram_bot.tasks.send_telegram_message",
        side_effect=requests.RequestException,
    )
    def test_failed_message_is_not_marked_as_sent(
        self,
        mock_send,
    ):
        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_called_once()

        self.habit.refresh_from_db()
        self.assertIsNone(
            self.habit.last_reminder_at
        )

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_overdue_reminder_is_sent(self, mock_send):
        self.habit.time = (
            self.now - timedelta(minutes=10)
        ).time().replace(tzinfo=None)
        self.habit.save(update_fields=["time"])

        result = send_habit_reminders()

        self.assertEqual(result, 1)
        mock_send.assert_called_once()

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_future_reminder_is_not_sent(self, mock_send):
        self.habit.time = (
            self.now + timedelta(minutes=10)
        ).time().replace(tzinfo=None)
        self.habit.save(update_fields=["time"])

        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_not_called()

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_periodicity_has_not_elapsed(self, mock_send):
        self.habit.periodicity = 3
        self.habit.last_reminder_at = (
            self.now - timedelta(days=2)
        )
        self.habit.save(
            update_fields=["periodicity", "last_reminder_at"]
        )

        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_not_called()

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_periodicity_has_elapsed(self, mock_send):
        self.habit.periodicity = 3
        self.habit.last_reminder_at = (
            self.now - timedelta(days=3)
        )
        self.habit.save(
            update_fields=["periodicity", "last_reminder_at"]
        )

        result = send_habit_reminders()

        self.assertEqual(result, 1)
        mock_send.assert_called_once()

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_pleasant_habit_has_no_reminder(self, mock_send):
        self.habit.is_pleasant = True
        self.habit.reward = ""
        self.habit.save(
            update_fields=["is_pleasant", "reward"]
        )

        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_not_called()

    @patch("telegram_bot.tasks.send_telegram_message")
    def test_user_without_chat_id_is_skipped(self, mock_send):
        self.user.telegram_chat_id = None
        self.user.save(update_fields=["telegram_chat_id"])

        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_not_called()

    @patch(
        "telegram_bot.tasks.send_telegram_message",
        side_effect=TelegramAPIError("Ошибка отправки"),
    )
    def test_api_error_does_not_mark_reminder_sent(
        self,
        mock_send,
    ):
        result = send_habit_reminders()

        self.assertEqual(result, 0)
        mock_send.assert_called_once()

        self.habit.refresh_from_db()
        self.assertIsNone(self.habit.last_reminder_at)