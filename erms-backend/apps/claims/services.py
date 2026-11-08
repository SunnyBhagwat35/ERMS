"""
Business logic for the claims. Views and serializers will not change
claims directl, every write goes through a function here.

Steps:

  1. open a transaction and lock the claim row   (_lock → select_for_update)
  2. check who is acting and what state the claim is in
  3. validate the request against business rules
  4. compare-and-set UPDATE guarded by the expected status   (_transition)
  5. append a ClaimEvent

About step 4: Django ignores select_for_update() on SQLite, so the row lock
only exists once you move to PostgreSQL. The guarded UPDATE in _transition is
what actually prevents two overlapping requests from both succeeding on
SQLite — only the first one finds the row in the expected status.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .exceptions import InvalidTransition, NotFound, NotPermitted, ValidationFailed
from .models import Claim, ClaimEvent, ClaimItem, ClaimStatus
from .validators import item_errors

log = logging.getLogger(__name__)

Status = ClaimStatus
Action = ClaimEvent.Action
ZERO = Decimal("0.00")
ITEM_FIELDS = ("category", "description", "expense_date", "amount")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _lock(claim_id: int) -> Claim:
    """Fetch the claim with a row lock (PostgreSQL). No-op on SQLite — see module docstring."""
    try:
        return Claim.objects.select_for_update().select_related("employee").get(pk=claim_id)
    except Claim.DoesNotExist:
        raise NotFound("Claim not found.") from None


def _get_item(claim: Claim, item_id: int) -> ClaimItem:
    try:
        return claim.items.select_related("category").get(pk=item_id)
    except ClaimItem.DoesNotExist:
        raise NotFound(f"Item {item_id} does not belong to claim {claim.claim_number}.") from None


def _require_owner(claim: Claim, actor) -> None:
    if claim.employee_id != actor.id:
        raise NotPermitted("Only the claim owner can do this.")


def _require_approver(actor) -> None:
    if not actor.is_approver:
        raise NotPermitted("Only approvers can do this.")


def _require_not_owner(claim: Claim, actor) -> None:
    if claim.employee_id == actor.id:
        raise NotPermitted("You cannot review or pay your own claim.")


def _require_status(claim: Claim, *allowed: str) -> None:
    if claim.status not in allowed:
        raise InvalidTransition(
            f"Claim is {claim.status}; this action requires {' or '.join(allowed)}.",
            current_status=claim.status,
        )


def _transition(claim: Claim, *, from_status: str, to_status: str, **fields) -> Claim:
    """
    Compare-and-set. UPDATE ... WHERE id = ? AND status = <from_status>.
    If another request already moved the claim, zero rows match and we raise
    409 instead of silently overwriting their work.
    """
    rows = Claim.objects.filter(pk=claim.pk, status=from_status).update(
        status=to_status, updated_at=timezone.now(), **fields
    )
    if rows != 1:
        claim.refresh_from_db(fields=["status"])
        log.warning("CAS failed on claim %s: expected %s, found %s", claim.pk, from_status, claim.status)
        raise InvalidTransition(
            f"Claim was changed by another request; it is now {claim.status}.",
            current_status=claim.status,
        )
    claim.refresh_from_db()
    return claim


def _recalculate_total(claim: Claim) -> Claim:
    total = sum((item.amount for item in claim.items.all()), ZERO)
    Claim.objects.filter(pk=claim.pk).update(total_claimed=total, updated_at=timezone.now())
    claim.refresh_from_db()
    return claim


def _money(value) -> str | None:
    return None if value is None else f"{value:.2f}"


def _item_dict(item: ClaimItem) -> dict:
    return {
        "id": item.id,
        "category": item.category.code,
        "description": item.description,
        "expense_date": item.expense_date.isoformat(),
        "amount": _money(item.amount),
        "approved_amount": _money(item.approved_amount),
        "has_receipt": bool(item.receipt),
    }


def _snapshot(claim: Claim, items=None) -> dict:
    if items is None:
        items = list(claim.items.select_related("category"))
    return {
        "total_claimed": _money(claim.total_claimed),
        "total_approved": _money(claim.total_approved),
        "approved_override": _money(claim.approved_override),
        "items": [_item_dict(i) for i in items],
    }


def _log(claim: Claim, actor, action: str, *, from_status="", to_status="", comment="", data=None) -> ClaimEvent:
    return ClaimEvent.objects.create(
        claim=claim,
        actor=actor,
        action=action,
        from_status=from_status,
        to_status=to_status,
        comment=comment,
        data=data or {},
    )


def _create_item(claim: Claim, data: dict) -> ClaimItem:
    errors = item_errors(
        category=data.get("category"),
        amount=data.get("amount"),
        expense_date=data.get("expense_date"),
        description=data.get("description"),
    )
    if errors:
        raise ValidationFailed(errors)
    return ClaimItem.objects.create(
        claim=claim,
        category=data["category"],
        description=data["description"].strip(),
        expense_date=data["expense_date"],
        amount=data["amount"],
        receipt=data.get("receipt"),
    )


def _submission_errors(claim: Claim, items: list[ClaimItem]) -> list[str]:
    errors: list[str] = []
    if not claim.title.strip():
        errors.append("Title is required.")
    if not items:
        errors.append("Add at least one expense item before submitting.")
    for item in items:
        for err in item_errors(
            category=item.category, amount=item.amount, expense_date=item.expense_date, description=item.description
        ):
            errors.append(f"Item {item.id} ({item.description}): {err}")
    return errors


# --------------------------------------------------------------------------- #
# Draft editing (owner only, DRAFT only)
# --------------------------------------------------------------------------- #


@transaction.atomic
def create_claim(*, employee, title: str, description: str = "", items=()) -> Claim:
    title = (title or "").strip()
    if not title:
        raise ValidationFailed("Title is required.")

    claim = Claim.objects.create(employee=employee, title=title, description=description or "")
    # Number from the primary key: unique and race-free without a counter table.
    claim.claim_number = f"CLM-{timezone.now().year}-{claim.pk:04d}"
    claim.save(update_fields=["claim_number"])

    created = [_create_item(claim, data) for data in items]
    if created:
        claim = _recalculate_total(claim)

    _log(claim, employee, Action.CREATED, to_status=Status.DRAFT, data=_snapshot(claim, created))
    return claim


@transaction.atomic
def update_claim(*, claim_id: int, actor, **fields) -> Claim:
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.DRAFT)

    if "title" in fields and not (fields["title"] or "").strip():
        raise ValidationFailed("Title cannot be blank.")

    changes = {}
    for name in ("title", "description"):
        if name in fields and fields[name] is not None:
            new = fields[name].strip() if name == "title" else fields[name]
            old = getattr(claim, name)
            if new != old:
                changes[name] = {"from": old, "to": new}
                setattr(claim, name, new)

    if not changes:
        return claim  # idempotent: nothing to write, nothing to log

    claim.save(update_fields=[*changes, "updated_at"])
    _log(claim, actor, Action.UPDATED, from_status=Status.DRAFT, to_status=Status.DRAFT, data={"changes": changes})
    return claim


@transaction.atomic
def delete_claim(*, claim_id: int, actor) -> None:
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.DRAFT)
    for item in claim.items.all():
        if item.receipt:
            item.receipt.delete(save=False)
    log.info("Draft %s deleted by %s", claim.claim_number, actor.username)
    claim.delete()  # events cascade; a never-submitted draft has no audit value


@transaction.atomic
def add_item(*, claim_id: int, actor, **data) -> ClaimItem:
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.DRAFT)

    item = _create_item(claim, data)
    claim = _recalculate_total(claim)
    _log(
        claim,
        actor,
        Action.ITEM_ADDED,
        from_status=Status.DRAFT,
        to_status=Status.DRAFT,
        data={"item": _item_dict(item), "total_claimed": _money(claim.total_claimed)},
    )
    return item


@transaction.atomic
def update_item(*, claim_id: int, item_id: int, actor, **data) -> ClaimItem:
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.DRAFT)
    item = _get_item(claim, item_id)

    merged = {name: data.get(name, getattr(item, name)) for name in ITEM_FIELDS}
    if merged["description"]:
        merged["description"] = merged["description"].strip()
    errors = item_errors(**merged)
    if errors:
        raise ValidationFailed(errors)

    changes = {}
    for name, new in merged.items():
        old = getattr(item, name)
        if new != old:
            changes[name] = {"from": str(old), "to": str(new)}
            setattr(item, name, new)

    if "receipt" in data and data["receipt"] is not None:
        if item.receipt:
            item.receipt.delete(save=False)
        item.receipt = data["receipt"]
        changes["receipt"] = {"from": None, "to": data["receipt"].name}

    if not changes:
        return item

    item.save()
    claim = _recalculate_total(claim)
    _log(
        claim,
        actor,
        Action.ITEM_UPDATED,
        from_status=Status.DRAFT,
        to_status=Status.DRAFT,
        data={"item_id": item.id, "changes": changes, "total_claimed": _money(claim.total_claimed)},
    )
    return item


@transaction.atomic
def remove_item(*, claim_id: int, item_id: int, actor) -> Claim:
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.DRAFT)
    item = _get_item(claim, item_id)

    snapshot = _item_dict(item)
    if item.receipt:
        item.receipt.delete(save=False)
    item.delete()
    claim = _recalculate_total(claim)
    _log(
        claim,
        actor,
        Action.ITEM_REMOVED,
        from_status=Status.DRAFT,
        to_status=Status.DRAFT,
        data={"item": snapshot, "total_claimed": _money(claim.total_claimed)},
    )
    return claim


# --------------------------------------------------------------------------- #
# Lifecycle transitions
# --------------------------------------------------------------------------- #


@transaction.atomic
def submit_claim(*, claim_id: int, actor) -> Claim:
    """DRAFT -> SUBMITTED. Re-validates every item so a changed category cap can't slip through."""
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.DRAFT)

    items = list(claim.items.select_related("category"))
    errors = _submission_errors(claim, items)
    if errors:
        raise ValidationFailed(errors)

    is_resubmission = claim.submission_count > 0
    total = sum((i.amount for i in items), ZERO)

    claim = _transition(
        claim,
        from_status=Status.DRAFT,
        to_status=Status.SUBMITTED,
        total_claimed=total,
        total_approved=None,
        approved_override=None,
        reviewer=None,
        reviewer_comment="",  # the rejection reason stays in the event history
        reviewed_at=None,
        submitted_at=timezone.now(),
        submission_count=F("submission_count") + 1,
    )
    # Clear leftovers from any earlier review so the next approver starts clean.
    ClaimItem.objects.filter(claim=claim).update(approved_amount=None)
    for item in items:
        item.approved_amount = None

    _log(
        claim,
        actor,
        Action.RESUBMITTED if is_resubmission else Action.SUBMITTED,
        from_status=Status.DRAFT,
        to_status=Status.SUBMITTED,
        data={**_snapshot(claim, items), "submission_count": claim.submission_count},
    )
    return claim


@transaction.atomic
def approve_claim(*, claim_id: int, actor, item_decisions=(), approved_override=None, comment: str = "") -> Claim:
    """
    SUBMITTED -> APPROVED, fully or partially.

    item_decisions: [{"id": <item id>, "approved_amount": Decimal}, ...]
                    Items not listed are approved in full.
    approved_override: optional claim-level total that wins over the item sum.
    A comment is mandatory whenever the approved total is below the claimed total.
    """
    claim = _lock(claim_id)
    _require_approver(actor)
    _require_not_owner(claim, actor)
    _require_status(claim, Status.SUBMITTED)

    items = {i.id: i for i in claim.items.select_related("category")}
    errors: list[str] = []

    decisions: dict[int, Decimal] = {}
    for decision in item_decisions:
        item_id = decision["id"]
        if item_id not in items:
            errors.append(f"Item {item_id} does not belong to this claim.")
        elif item_id in decisions:
            errors.append(f"Item {item_id} is listed more than once.")
        else:
            decisions[item_id] = decision["approved_amount"]

    for item in items.values():
        approved = decisions.get(item.id, item.amount)
        if approved < 0 or approved > item.amount:
            errors.append(f"Item {item.id} ({item.description}): approved amount must be between 0 and {item.amount}.")
        item.approved_amount = approved

    if approved_override is not None and not (0 <= approved_override <= claim.total_claimed):
        errors.append(f"Override must be between 0 and {claim.total_claimed}.")

    if errors:
        raise ValidationFailed(errors)

    item_sum = sum((i.approved_amount for i in items.values()), ZERO)
    total = approved_override if approved_override is not None else item_sum
    if total <= 0:
        raise ValidationFailed("Approved total is zero. Reject the claim instead.")

    is_partial = total < claim.total_claimed
    comment = (comment or "").strip()
    if is_partial and not comment:
        raise ValidationFailed("A comment is required when approving less than the claimed amount.")

    claim = _transition(
        claim,
        from_status=Status.SUBMITTED,
        to_status=Status.APPROVED,
        total_approved=total,
        approved_override=approved_override,
        reviewer=actor,
        reviewer_comment=comment,
        reviewed_at=timezone.now(),
    )
    ClaimItem.objects.bulk_update(items.values(), ["approved_amount"])

    _log(
        claim,
        actor,
        Action.PARTIALLY_APPROVED if is_partial else Action.APPROVED,
        from_status=Status.SUBMITTED,
        to_status=Status.APPROVED,
        comment=comment,
        data={**_snapshot(claim, list(items.values())), "item_sum": _money(item_sum)},
    )
    return claim


@transaction.atomic
def reject_claim(*, claim_id: int, actor, comment: str) -> Claim:
    """SUBMITTED -> REJECTED. Comment is mandatory so the employee knows what to fix."""
    claim = _lock(claim_id)
    _require_approver(actor)
    _require_not_owner(claim, actor)
    _require_status(claim, Status.SUBMITTED)

    comment = (comment or "").strip()
    if not comment:
        raise ValidationFailed("A comment is required when rejecting a claim.")

    claim = _transition(
        claim,
        from_status=Status.SUBMITTED,
        to_status=Status.REJECTED,
        reviewer=actor,
        reviewer_comment=comment,
        reviewed_at=timezone.now(),
        total_approved=None,
        approved_override=None,
    )
    _log(
        claim,
        actor,
        Action.REJECTED,
        from_status=Status.SUBMITTED,
        to_status=Status.REJECTED,
        comment=comment,
        data=_snapshot(claim),
    )
    return claim


@transaction.atomic
def reopen_claim(*, claim_id: int, actor) -> Claim:
    """REJECTED -> DRAFT so the owner can correct and resubmit. Reviewer comment stays visible until resubmit."""
    claim = _lock(claim_id)
    _require_owner(claim, actor)
    _require_status(claim, Status.REJECTED)

    claim = _transition(claim, from_status=Status.REJECTED, to_status=Status.DRAFT)
    _log(
        claim,
        actor,
        Action.REOPENED,
        from_status=Status.REJECTED,
        to_status=Status.DRAFT,
        data={"rejection_comment": claim.reviewer_comment},
    )
    return claim


@transaction.atomic
def mark_paid(*, claim_id: int, actor, payment_reference: str = "") -> Claim:
    """APPROVED -> PAID. No money moves; we only record a reference."""
    claim = _lock(claim_id)
    _require_approver(actor)
    _require_not_owner(claim, actor)
    _require_status(claim, Status.APPROVED)

    reference = (payment_reference or "").strip() or f"DEMO-PAY-{claim.claim_number}"
    claim = _transition(
        claim,
        from_status=Status.APPROVED,
        to_status=Status.PAID,
        paid_at=timezone.now(),
        paid_by=actor,
        payment_reference=reference,
    )
    _log(
        claim,
        actor,
        Action.PAID,
        from_status=Status.APPROVED,
        to_status=Status.PAID,
        data={"payment_reference": reference, "amount": _money(claim.total_approved)},
    )
    return claim


# --------------------------------------------------------------------------- #
# Read helper used by serializers so the frontend knows which buttons to show
# --------------------------------------------------------------------------- #


def allowed_actions(claim: Claim, user) -> list[str]:
    is_owner = claim.employee_id == user.id
    actions: list[str] = []
    if claim.status == Status.DRAFT and is_owner:
        actions += ["edit", "delete", "submit"]
    if claim.status == Status.SUBMITTED and user.is_approver and not is_owner:
        actions += ["approve", "reject"]
    if claim.status == Status.APPROVED and user.is_approver and not is_owner:
        actions.append("pay")
    if claim.status == Status.REJECTED and is_owner:
        actions.append("reopen")
    return actions
