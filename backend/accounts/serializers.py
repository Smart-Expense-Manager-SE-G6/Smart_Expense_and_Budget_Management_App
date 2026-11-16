
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import validate_timezone

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Profile as seen by its owner. Email is fixed after registration."""

    timezone = serializers.CharField(max_length=64, validators=[validate_timezone], required=False)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "timezone",
            "email_alerts",
            "date_joined",
            "is_staff",
        ]
        read_only_fields = ["id", "email", "date_joined", "is_staff"]


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.", code="wrong_password")
        return value

    def validate(self, attrs):
        user = self.context["request"].user
        try:
            validate_password(attrs["new_password"], user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)}, code="weak_password")
        if attrs["new_password"] == attrs["current_password"]:
            raise serializers.ValidationError({"new_password": "Choose a password you have not used here."}, code="same_password")
        return attrs


class AccountDeleteSerializer(serializers.Serializer):
    password = serializers.CharField(trim_whitespace=False)

    def validate_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.", code="wrong_password")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    # Declared explicitly so uniqueness is checked case-insensitively in validate_email,
    # not by ModelSerializer's automatic (case-sensitive) unique validator.
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False, style={"input_type": "password"})
    timezone = serializers.CharField(max_length=64, validators=[validate_timezone], required=False)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "timezone"]

    def validate_email(self, value):
        email = value.strip().lower()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email already exists.", code="email_taken")
        return email

    def validate(self, attrs):
        # Run Django's password validators against the would-be user (length, common, similarity).
        candidate = User(**{k: v for k, v in attrs.items() if k != "password"})
        try:
            validate_password(attrs["password"], candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}, code="weak_password") from exc
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(trim_whitespace=False, style={"input_type": "password"})
