from pathlib import PurePath

from django.conf import settings
from django.db.models import Q
from rest_framework import serializers

from .models import Category, Expense


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "owner",
            "parent",
            "children",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "is_active", "created_at", "updated_at"]

    def get_children(self, category):
        user = self.context["request"].user
        children = category.children.filter(
            is_active=True,
        ).filter(
            Q(owner__isnull=True) | Q(owner=user)
        ).order_by("name", "id")
        return [
            {
                "id": child.pk,
                "name": child.name,
                "parent": child.parent_id,
                "is_active": child.is_active,
            }
            for child in children
        ]

    def validate_name(self, name):
        name = name.strip()
        if not name:
            raise serializers.ValidationError("Category name cannot be empty.")

        user = self.context["request"].user
        queryset = Category.objects.filter(name__iexact=name)
        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.filter(owner=user).exists():
            raise serializers.ValidationError(
                "You already have a category with this name."
            )
        return name

    def validate_parent(self, parent):
        if parent is None:
            return parent

        user = self.context["request"].user
        if not parent.is_active:
            raise serializers.ValidationError("The selected parent is inactive.")
        if parent.owner_id is not None and parent.owner_id != user.pk:
            raise serializers.ValidationError(
                "You cannot use another user's category as the parent."
            )
        if self.instance is not None and parent.pk == self.instance.pk:
            raise serializers.ValidationError(
                "A category cannot be its own parent."
            )

        ancestor = parent
        visited = set()
        while ancestor is not None:
            if ancestor.pk in visited:
                raise serializers.ValidationError(
                    "The category hierarchy contains a cycle."
                )
            visited.add(ancestor.pk)
            if not ancestor.is_active:
                raise serializers.ValidationError(
                    "The category hierarchy contains an inactive parent."
                )
            if ancestor.owner_id is not None and ancestor.owner_id != user.pk:
                raise serializers.ValidationError(
                    "You cannot use another user's category in the parent hierarchy."
                )
            if self.instance is not None and ancestor.pk == self.instance.pk:
                raise serializers.ValidationError(
                    "The category hierarchy cannot contain a cycle."
                )
            ancestor = ancestor.parent
        return parent


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            "id",
            "owner",
            "category",
            "amount",
            "description",
            "date",
            "payment_method",
            "is_deleted",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "is_deleted", "created_at", "updated_at"]

    def validate_category(self, category):
        if category is None:
            return category

        user = self.context["request"].user
        if not category.is_active:
            raise serializers.ValidationError("The selected category is inactive.")
        if category.owner_id is not None and category.owner_id != user.pk:
            raise serializers.ValidationError("You cannot use another user's category.")
        return category

    def create(self, validated_data):
        validated_data["owner"] = self.context["request"].user
        return super().create(validated_data)


class ReceiptUploadSerializer(serializers.Serializer):
    receipt = serializers.FileField()

    def validate_receipt(self, receipt):
        max_size = settings.RECEIPT_MAX_SIZE_BYTES
        if receipt.size > max_size:
            raise serializers.ValidationError(
                f"Receipt must not exceed {max_size} bytes."
            )

        filename = receipt.name or ""
        if PurePath(filename).name != filename:
            raise serializers.ValidationError("Receipt filename must not contain a path.")
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        allowed_types = {
            "jpg": ("image/jpeg", b"\xff\xd8\xff"),
            "jpeg": ("image/jpeg", b"\xff\xd8\xff"),
            "png": ("image/png", b"\x89PNG\r\n\x1a\n"),
            "pdf": ("application/pdf", b"%PDF-"),
        }
        if extension not in allowed_types:
            raise serializers.ValidationError(
                "Only JPEG, PNG, and PDF receipts are supported."
            )

        expected_type, signature = allowed_types[extension]
        if receipt.content_type != expected_type:
            raise serializers.ValidationError(
                "The uploaded file MIME type does not match its extension."
            )
        header = receipt.read(len(signature))
        receipt.seek(0)
        if header != signature:
            raise serializers.ValidationError("The uploaded file content is invalid.")
        return receipt
