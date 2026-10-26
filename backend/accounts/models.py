import zoneinfo

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


def validate_timezone(value):
    if value not in zoneinfo.available_timezones():
        raise ValidationError(f"{value} is not a valid IANA time zone")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Application user. Signs in with email; there is no username.

    Other modules must reference this via settings.AUTH_USER_MODEL,
    never by importing it directly into a ForeignKey.
    """

    username = None
    email = models.EmailField(unique=True)
    # Budget periods are computed in the user's own time zone (D7).
    timezone = models.CharField(max_length=64, default="Asia/Kolkata", validators=[validate_timezone])

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
