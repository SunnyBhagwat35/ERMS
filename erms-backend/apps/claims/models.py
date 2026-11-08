from decimal import Decimal

from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

MONEY = {"max_digits": 12, "decimal_places": 2}


class ExpenseCategory(models.Model):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    max_amount = models.DecimalField(**MONEY, null=True, blank=True, help_text="Per-item cap. Blank = no cap.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        verbose_name_plural = "expense categories"

    def __str__(self) -> str:
        return f"{self.code} – {self.name}"


class ClaimStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    PAID = "PAID", "Paid"


class Claim(models.Model):
    """
    Header of a reimbursement request. Amounts are denormalised here
    (total_claimed / total_approved) and recalculated by the service layer
    whenever items change, so list screens never need to sum items.
    """

    claim_number = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="claims")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=ClaimStatus.choices, default=ClaimStatus.DRAFT, db_index=True)

    total_claimed = models.DecimalField(**MONEY, default=Decimal("0.00"))
    total_approved = models.DecimalField(**MONEY, null=True, blank=True)
    # Claim-level override set by the approver; wins over the sum of item approvals.
    approved_override = models.DecimalField(**MONEY, null=True, blank=True)

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="reviewed_claims"
    )
    reviewer_comment = models.TextField(blank=True)
    submission_count = models.PositiveIntegerField(default=0, help_text="Incremented on every submit; >1 means resubmitted.")

    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="paid_claims"
    )
    payment_reference = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(total_claimed__gte=0), name="claim_total_claimed_non_negative"),
            models.CheckConstraint(
                condition=Q(total_approved__isnull=True)
                | (Q(total_approved__gte=0) & Q(total_approved__lte=F("total_claimed"))),
                name="claim_total_approved_within_claimed",
            ),
        ]

    @property
    def is_partial(self) -> bool:
        return (
            self.status in (ClaimStatus.APPROVED, ClaimStatus.PAID)
            and self.total_approved is not None
            and self.total_approved < self.total_claimed
        )

    def __str__(self) -> str:
        return f"{self.claim_number} [{self.status}] {self.title}"


def receipt_upload_path(instance, filename):
    return f"receipts/{instance.claim_id}/{filename}"


class ClaimItem(models.Model):
    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="items")
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name="items")
    description = models.CharField(max_length=255)
    expense_date = models.DateField()
    amount = models.DecimalField(**MONEY, validators=[MinValueValidator(Decimal("0.01"))])
    approved_amount = models.DecimalField(**MONEY, null=True, blank=True)
    receipt = models.FileField(
        upload_to=receipt_upload_path,
        null=True,
        blank=True,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["expense_date", "id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="claimitem_amount_positive"),
            models.CheckConstraint(
                condition=Q(approved_amount__isnull=True)
                | (Q(approved_amount__gte=0) & Q(approved_amount__lte=F("amount"))),
                name="claimitem_approved_within_amount",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} ({self.amount})"


class ClaimEvent(models.Model):
    """
    Append-only history. One row per business action; `data` holds a JSON
    snapshot of whatever that action touched (amounts, changed fields...).
    """

    class Action(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        ITEM_ADDED = "ITEM_ADDED", "Item added"
        ITEM_UPDATED = "ITEM_UPDATED", "Item updated"
        ITEM_REMOVED = "ITEM_REMOVED", "Item removed"
        SUBMITTED = "SUBMITTED", "Submitted"
        RESUBMITTED = "RESUBMITTED", "Resubmitted"
        APPROVED = "APPROVED", "Approved"
        PARTIALLY_APPROVED = "PARTIALLY_APPROVED", "Partially approved"
        REJECTED = "REJECTED", "Rejected"
        REOPENED = "REOPENED", "Reopened"
        PAID = "PAID", "Paid"

    claim = models.ForeignKey(Claim, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=24, choices=Action.choices)
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    comment = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["claim", "created_at"])]

    def __str__(self) -> str:
        return f"{self.claim_id} {self.action} by {self.actor_id}"
