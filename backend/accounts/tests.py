from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase


class UserModelTests(TestCase):
    def setUp(self):
        self.User = get_user_model()

    def test_create_user_with_email_lowercases_and_hashes_with_bcrypt(self):
        user = self.User.objects.create_user("Alice@Example.com", password="s3cure-pass!")
        self.assertEqual(user.email, "alice@example.com")
        self.assertTrue(user.password.startswith("bcrypt_sha256$"))
        self.assertTrue(user.check_password("s3cure-pass!"))
        self.assertEqual(user.timezone, "Asia/Kolkata")

    def test_email_is_unique(self):
        self.User.objects.create_user("bob@example.com", password="x")
        with self.assertRaises(IntegrityError):
            self.User.objects.create_user("bob@example.com", password="y")

    def test_create_superuser(self):
        admin = self.User.objects.create_superuser("admin@example.com", password="x")
        self.assertTrue(admin.is_staff and admin.is_superuser)
