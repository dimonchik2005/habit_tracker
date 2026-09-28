from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from habits.models import Habit
from habits.serializers import HabitSerializer
from habits.paginators import HabitPagination

class HabitViewSet(ModelViewSet):
    serializer_class = HabitSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = HabitPagination

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Habit.objects.none()

        return Habit.objects.filter(
            user=self.request.user
        ).select_related("user", "related_habit")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PublicHabitListAPIView(ListAPIView):
    serializer_class = HabitSerializer
    permission_classes = [AllowAny]
    pagination_class = HabitPagination

    def get_queryset(self):
        return Habit.objects.filter(
            is_public=True
        ).select_related("user", "related_habit")