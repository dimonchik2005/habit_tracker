import logging

import requests
from celery import shared_task
from django.db import transaction
from django.utils import timezone

from habits.models import Habit
from telegram_bot.services import (
    TelegramAPIError,
    send_telegram_message,
)


logger = logging.getLogger(__name__)


def reminder_is_due(habit, now):
    current_time = now.time().replace(tzinfo=None)

    if habit.time > current_time:
        return False

    if habit.last_reminder_at is None:
        return True

    last_reminder_date = timezone.localtime(
        habit.last_reminder_at
    ).date()

    days_passed = (now.date() - last_reminder_date).days

    return days_passed >= habit.periodicity


def build_reminder_message(habit):
    return (
        f"Напоминание: {habit.action}\n"
        f"Время: {habit.time.strftime('%H:%M')}\n"
        f"Место: {habit.place}\n"
        f"Длительность: {habit.duration} секунд."
    )


@shared_task
def send_habit_reminders():
    now = timezone.localtime()
    current_time = now.time().replace(tzinfo=None)

    habit_ids = list(
        Habit.objects.filter(
            time__lte=current_time,
            is_pleasant=False,
            user__is_active=True,
            user__telegram_chat_id__isnull=False,
        ).values_list("pk", flat=True)
    )

    sent_count = 0

    for habit_id in habit_ids:
        with transaction.atomic():
            habit = (
                Habit.objects.select_for_update(
                    skip_locked=True,
                    of=("self",),
                )
                .select_related("user")
                .filter(
                    pk=habit_id,
                    is_pleasant=False,
                    user__is_active=True,
                    user__telegram_chat_id__isnull=False,
                )
                .first()
            )

            if habit is None:
                continue

            if not reminder_is_due(habit, now):
                continue

            try:
                send_telegram_message(
                    habit.user.telegram_chat_id,
                    build_reminder_message(habit),
                )
            except (TelegramAPIError, requests.RequestException):
                logger.warning(
                    "Не удалось отправить напоминание "
                    "для привычки %s.",
                    habit.pk,
                )
                continue

            habit.last_reminder_at = timezone.now()
            habit.save(update_fields=["last_reminder_at"])
            sent_count += 1

    return sent_count