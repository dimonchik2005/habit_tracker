from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from habits.models import Habit
from users.models import User
from django.test import override_settings

class HabitAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="owner@example.com",
            password="StrongPass!4826",
        )
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="StrongPass!4826",
        )
        self.client.force_authenticate(user=self.user)

    def get_habit_data(self, **changes):
        data = {
            "place": "Дома",
            "time": "08:00:00",
            "action": "Сделать зарядку",
            "is_pleasant": False,
            "related_habit": None,
            "periodicity": 1,
            "reward": "Выпить кофе",
            "duration": 60,
            "is_public": False,
        }
        data.update(changes)
        return data

    def create_habit(self, user=None, **changes):
        data = {
            "user": user or self.user,
            "place": "Дома",
            "time": "08:00:00",
            "action": "Сделать зарядку",
            "is_pleasant": False,
            "periodicity": 1,
            "reward": "",
            "duration": 60,
            "is_public": False,
        }
        data.update(changes)
        return Habit.objects.create(**data)

    def test_authentication_is_required(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("habits:habit-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_create_habit_assigns_owner(self):
        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        habit = Habit.objects.get(pk=response.data["id"])
        self.assertEqual(habit.user, self.user)

    def test_list_contains_only_own_habits(self):
        self.create_habit()
        self.create_habit(user=self.other_user)

        response = self.client.get(
            reverse("habits:habit-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["user"],
            self.user.pk,
        )

    def test_cannot_retrieve_other_users_habit(self):
        habit = self.create_habit(user=self.other_user)

        response = self.client.get(
            reverse(
                "habits:habit-detail",
                kwargs={"pk": habit.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_update_own_habit(self):
        habit = self.create_habit()

        response = self.client.patch(
            reverse(
                "habits:habit-detail",
                kwargs={"pk": habit.pk},
            ),
            {"action": "Прочитать десять страниц"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        habit.refresh_from_db()
        self.assertEqual(
            habit.action,
            "Прочитать десять страниц",
        )

    def test_delete_own_habit(self):
        habit = self.create_habit()

        response = self.client.delete(
            reverse(
                "habits:habit-detail",
                kwargs={"pk": habit.pk},
            )
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            Habit.objects.filter(pk=habit.pk).exists()
        )

    def test_public_list(self):
        self.create_habit(is_public=True)
        self.create_habit(
            user=self.other_user,
            is_public=True,
        )
        self.create_habit(is_public=False)

        self.client.force_authenticate(user=None)

        response = self.client.get(
            reverse("habits:public-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 2)

    def test_limit_offset_pagination(self):
        for number in range(6):
            self.create_habit(
                action=f"Привычка {number}"
            )

        response = self.client.get(
            reverse("habits:habit-list"),
            {
                "limit": 2,
                "offset": 1,
            },
        )

        self.assertEqual(response.data["count"], 6)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)

    def test_reward_and_related_habit_are_incompatible(self):
        pleasant_habit = self.create_habit(
            action="Послушать музыку",
            is_pleasant=True,
        )

        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(
                reward="Выпить кофе",
                related_habit=pleasant_habit.pk,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_duration_must_not_exceed_120_seconds(self):
        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(duration=121),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_periodicity_must_be_between_1_and_7(self):
        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(periodicity=8),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_related_habit_must_be_pleasant(self):
        useful_habit = self.create_habit(
            action="Прочитать книгу",
            is_pleasant=False,
        )

        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(
                reward="",
                related_habit=useful_habit.pk,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_pleasant_habit_cannot_have_reward(self):
        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(
                is_pleasant=True,
                reward="Выпить кофе",
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_partial_update_uses_existing_values(self):
        habit = self.create_habit(
            reward="Выпить кофе",
        )

        response = self.client.patch(
            reverse(
                "habits:habit-detail",
                kwargs={"pk": habit.pk},
            ),
            {"is_pleasant": True},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_cannot_modify_other_users_public_habit(self):
        habit = self.create_habit(
            user=self.other_user,
            is_public=True,
            action="Чужая привычка",
        )
        url = reverse(
            "habits:habit-detail",
            kwargs={"pk": habit.pk},
        )

        for method in ("put", "patch", "delete"):
            with self.subTest(method=method):
                request = getattr(self.client, method)

                if method == "delete":
                    response = request(url)
                else:
                    response = request(
                        url,
                        self.get_habit_data(action="Подмена"),
                        format="json",
                    )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_404_NOT_FOUND,
                )

        habit.refresh_from_db()
        self.assertEqual(habit.action, "Чужая привычка")

    def test_cannot_assign_another_owner(self):
        data = self.get_habit_data()
        data["user"] = self.other_user.pk

        response = self.client.post(
            reverse("habits:habit-list"),
            data,
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        habit = Habit.objects.get(pk=response.data["id"])
        self.assertEqual(habit.user_id, self.user.pk)

    def test_cannot_link_other_users_private_habit(self):
        other_habit = self.create_habit(
            user=self.other_user,
            is_pleasant=True,
            is_public=False,
        )

        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(
                reward="",
                related_habit=other_habit.pk,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("related_habit", response.data)

    def test_can_link_own_pleasant_habit(self):
        pleasant_habit = self.create_habit(
            is_pleasant=True,
        )

        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(
                reward="",
                related_habit=pleasant_habit.pk,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        habit = Habit.objects.get(pk=response.data["id"])
        self.assertEqual(
            habit.related_habit_id,
            pleasant_habit.pk,
        )

    def test_cannot_change_used_reward_to_useful_habit(self):
        pleasant_habit = self.create_habit(
            is_pleasant=True,
        )
        self.create_habit(related_habit=pleasant_habit)

        response = self.client.patch(
            reverse(
                "habits:habit-detail",
                kwargs={"pk": pleasant_habit.pk},
            ),
            {"is_pleasant": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        pleasant_habit.refresh_from_db()
        self.assertTrue(pleasant_habit.is_pleasant)

    def test_pleasant_habit_cannot_have_related_habit(self):
        pleasant_habit = self.create_habit(
            is_pleasant=True,
        )

        response = self.client.post(
            reverse("habits:habit-list"),
            self.get_habit_data(
                is_pleasant=True,
                reward="",
                related_habit=pleasant_habit.pk,
            ),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_duration_and_periodicity_boundaries(self):
        cases = (
            ("duration", 0),
            ("duration", 121),
            ("periodicity", 0),
            ("periodicity", 8),
        )

        for field, value in cases:
            with self.subTest(field=field, value=value):
                response = self.client.post(
                    reverse("habits:habit-list"),
                    self.get_habit_data(**{field: value}),
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertIn(field, response.data)

    def test_patch_checks_existing_reward(self):
        pleasant_habit = self.create_habit(
            is_pleasant=True,
        )
        habit = self.create_habit(reward="Кофе")

        response = self.client.patch(
            reverse(
                "habits:habit-detail",
                kwargs={"pk": habit.pk},
            ),
            {"related_habit": pleasant_habit.pk},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        habit.refresh_from_db()
        self.assertIsNone(habit.related_habit_id)
        self.assertEqual(habit.reward, "Кофе")

    def test_default_pagination_returns_five_habits(self):
        habits = [
            self.create_habit(action=f"Привычка {number}")
            for number in range(6)
        ]

        response = self.client.get(
            reverse("habits:habit-list")
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["count"], 6)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [habit.pk for habit in habits[:5]],
        )
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])

    def test_offset_skips_requested_records(self):
        habits = [
            self.create_habit(action=f"Привычка {number}")
            for number in range(4)
        ]

        response = self.client.get(
            reverse("habits:habit-list"),
            {"limit": 2, "offset": 1},
        )

        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [habit.pk for habit in habits[1:3]],
        )

    def test_pagination_limit_is_capped_at_twenty(self):
        for number in range(21):
            self.create_habit(action=f"Привычка {number}")

        response = self.client.get(
            reverse("habits:habit-list"),
            {"limit": 100},
        )

        self.assertEqual(response.data["count"], 21)
        self.assertEqual(
            len(response.data["results"]),
            20,
        )

    def test_public_list_does_not_allow_creation(self):
        response = self.client.post(
            reverse("habits:public-list"),
            self.get_habit_data(),
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(Habit.objects.count(), 0)

@override_settings(
    CORS_ALLOWED_ORIGINS=["http://localhost:3000"],
    CORS_ALLOW_ALL_ORIGINS=False,
)
class CorsTests(APITestCase):
    def test_allowed_origin_receives_cors_header(self):
        response = self.client.get(
            reverse("habits:public-list"),
            HTTP_ORIGIN="http://localhost:3000",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.get("Access-Control-Allow-Origin"),
            "http://localhost:3000",
        )

    def test_unknown_origin_receives_no_cors_header(self):
        response = self.client.get(
            reverse("habits:public-list"),
            HTTP_ORIGIN="https://unknown.example",
        )

        self.assertNotIn(
            "Access-Control-Allow-Origin",
            response.headers,
        )

    def test_preflight_allows_authorization_header(self):
        response = self.client.options(
            reverse("habits:habit-list"),
            HTTP_ORIGIN="http://localhost:3000",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS=(
                "authorization,content-type"
            ),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            response.get("Access-Control-Allow-Origin"),
            "http://localhost:3000",
        )

        allowed_headers = {
            header.strip().lower()
            for header in response.get(
                "Access-Control-Allow-Headers", ""
            ).split(",")
        }

        self.assertIn("authorization", allowed_headers)
        self.assertIn("content-type", allowed_headers)
        self.assertIn(
            "POST",
            response.get("Access-Control-Allow-Methods", ""),
        )
