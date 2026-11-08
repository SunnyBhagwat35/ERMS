"""
Serializers validate shape and types. Business rules (caps, dates, who may do
what, state) live in services.py so there is exactly one place to look.
"""

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer

from . import services
from .models import Claim, ClaimEvent, ClaimItem, ExpenseCategory
from .validators import receipt_errors


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "code", "name", "max_amount", "is_active"]
        read_only_fields = fields


class ClaimItemSerializer(serializers.ModelSerializer):
    """Used for reading items and for add/update (JSON or multipart with `receipt`)."""

    category_code = serializers.CharField(source="category.code", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ClaimItem
        fields = [
            "id",
            "category",
            "category_code",
            "category_name",
            "description",
            "expense_date",
            "amount",
            "approved_amount",
            "receipt",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "approved_amount", "created_at", "updated_at"]

    def validate_receipt(self, file):
        errors = receipt_errors(file)
        if errors:
            raise serializers.ValidationError(errors)
        return file


class ClaimCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    items = ClaimItemSerializer(many=True, required=False)


class ClaimUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class ClaimListSerializer(serializers.ModelSerializer):
    employee = UserSerializer(read_only=True)
    item_count = serializers.IntegerField(read_only=True)  # annotated in selectors
    is_partial = serializers.BooleanField(read_only=True)

    class Meta:
        model = Claim
        fields = [
            "id",
            "claim_number",
            "title",
            "status",
            "employee",
            "total_claimed",
            "total_approved",
            "is_partial",
            "item_count",
            "submission_count",
            "submitted_at",
            "reviewed_at",
            "paid_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ClaimDetailSerializer(serializers.ModelSerializer):
    employee = UserSerializer(read_only=True)
    reviewer = UserSerializer(read_only=True)
    paid_by = UserSerializer(read_only=True)
    items = ClaimItemSerializer(many=True, read_only=True)
    is_partial = serializers.BooleanField(read_only=True)
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Claim
        fields = [
            "id",
            "claim_number",
            "title",
            "description",
            "status",
            "employee",
            "total_claimed",
            "total_approved",
            "approved_override",
            "is_partial",
            "reviewer",
            "reviewer_comment",
            "submission_count",
            "submitted_at",
            "reviewed_at",
            "paid_at",
            "paid_by",
            "payment_reference",
            "items",
            "allowed_actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_allowed_actions(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return []
        return services.allowed_actions(obj, request.user)


class ItemDecisionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    approved_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class ApproveSerializer(serializers.Serializer):
    items = ItemDecisionSerializer(many=True, required=False, default=list)
    approved_override = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True, default=None
    )
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class RejectSerializer(serializers.Serializer):
    comment = serializers.CharField()


class PaySerializer(serializers.Serializer):
    payment_reference = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")


class ClaimEventSerializer(serializers.ModelSerializer):
    actor = UserSerializer(read_only=True)

    class Meta:
        model = ClaimEvent
        fields = ["id", "action", "from_status", "to_status", "comment", "data", "actor", "created_at"]
        read_only_fields = fields
