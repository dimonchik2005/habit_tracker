from rest_framework import serializers

from habits.models import Habit
from habits.validators import validate_habit


class HabitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Habit
        fields = (
            "id",
            "user",
            "place",
            "time",
            "action",
            "is_pleasant",
            "related_habit",
            "periodicity",
            "reward",
            "duration",
            "is_public",
            "created_at",
            "updated_at",
            "last_reminder_at",
        )
        read_only_fields = (
            "id",
            "user",
            "created_at",
            "updated_at",
            "last_reminder_at",
        )

    def validate(self, attrs):
        return validate_habit(attrs, instance=self.instance)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        request = self.context.get("request")
        queryset = Habit.objects.none()

        if request is not None and request.user.is_authenticated:
            queryset = Habit.objects.filter(
                user=request.user,
                is_pleasant=True,
            )

        self.fields["related_habit"].queryset = queryset