from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class UserManagerTests(TestCase):
    def test_create_user_without_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                password="StrongPass!4826",
            )

    def test_create_superuser(self):
        user = User.objects.create_superuser(
            email="admin@example.com",
            password="StrongPass!4826",
        )

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("StrongPass!4826"))


class UserAPITests(APITestCase):
    def test_user_registration(self):
        response = self.client.post(
            reverse("users:register"),
            {
                "email": "new@example.com",
                "password": "StrongPass!4826",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        user = User.objects.get(email="new@example.com")

        self.assertTrue(
            user.check_password("StrongPass!4826")
        )
        self.assertNotIn("password", response.data)

    def test_obtain_jwt_token(self):
        User.objects.create_user(
            email="user@example.com",
            password="StrongPass!4826",
        )

        response = self.client.post(
            reverse("token_obtain_pair"),
            {
                "email": "user@example.com",
                "password": "StrongPass!4826",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)