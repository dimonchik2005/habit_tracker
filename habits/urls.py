from django.urls import include, path
from rest_framework.routers import DefaultRouter

from habits.views import HabitViewSet, PublicHabitListAPIView


app_name = "habits"

router = DefaultRouter()
router.register("", HabitViewSet, basename="habit")

urlpatterns = [
    path(
        "public/",
        PublicHabitListAPIView.as_view(),
        name="public-list",
    ),
    path("", include(router.urls)),
]