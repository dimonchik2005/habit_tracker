from rest_framework import serializers


def validate_habit(attrs, instance=None):
    errors = {}

    def get_value(field_name, default=None):
        if field_name in attrs:
            return attrs[field_name]

        if instance is not None:
            return getattr(instance, field_name)

        return default

    def add_error(field_name, message):
        errors.setdefault(field_name, []).append(message)

    reward = get_value("reward", "")
    related_habit = get_value("related_habit")
    is_pleasant = get_value("is_pleasant", False)
    periodicity = get_value("periodicity", 1)
    duration = get_value("duration")

    if reward and related_habit:
        add_error(
            "non_field_errors",
            "Нельзя одновременно указывать вознаграждение "
            "и связанную привычку.",
        )

    if duration is not None and not 1 <= duration <= 120:
        add_error(
            "duration",
            "Продолжительность должна быть от 1 до 120 секунд.",
        )

    if periodicity is not None and not 1 <= periodicity <= 7:
        add_error(
            "periodicity",
            "Периодичность должна быть от 1 до 7 дней.",
        )

    if related_habit and not related_habit.is_pleasant:
        add_error(
            "related_habit",
            "Связанная привычка должна быть приятной.",
        )

    if is_pleasant:
        if reward:
            add_error(
                "reward",
                "У приятной привычки не может быть вознаграждения.",
            )

        if related_habit:
            add_error(
                "related_habit",
                "У приятной привычки не может быть связанной привычки.",
            )

    if instance is not None:
        if related_habit is not None and related_habit.pk == instance.pk:
            add_error(
                "related_habit",
                "Привычка не может ссылаться сама на себя.",
            )

        if not is_pleasant and instance.rewarded_habits.exists():
            add_error(
                "is_pleasant",
                "Нельзя убрать признак приятной привычки, "
                "пока она используется как награда.",
            )

    if errors:
        raise serializers.ValidationError(errors)

    return attrs