from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Habit(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="habits",
        verbose_name="Пользователь",
    )
    place = models.CharField(
        max_length=255,
        verbose_name="Место",
    )
    time = models.TimeField(
        verbose_name="Время выполнения",
    )
    action = models.CharField(
        max_length=255,
        verbose_name="Действие",
    )
    is_pleasant = models.BooleanField(
        default=False,
        verbose_name="Приятная привычка",
    )
    related_habit = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rewarded_habits",
        verbose_name="Связанная привычка",
    )
    periodicity = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(7),
        ],
        verbose_name="Периодичность в днях",
    )
    reward = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Вознаграждение",
    )
    duration = models.PositiveSmallIntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(120),
        ],
        verbose_name="Продолжительность в секундах",
    )
    is_public = models.BooleanField(
        default=False,
        verbose_name="Публичная привычка",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Дата изменения",
    )
    last_reminder_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Последнее напоминание",
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"

    def __str__(self):
        return f"{self.action} в {self.time}, место: {self.place}"
