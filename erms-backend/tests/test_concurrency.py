"""
The compare-and-set in services._transition is what protects us on SQLite,
where select_for_update() is a no-op. We simulate the dangerous interleaving:
request B read the claim as SUBMITTED, request A approved it in between,
then B tries to approve from its stale view.
"""

from decimal import Decimal

import pytest

from apps.claims import services
from apps.claims.exceptions import InvalidTransition
from apps.claims.models import Claim, ClaimEvent

pytestmark = pytest.mark.django_db


def test_stale_approve_is_rejected_by_cas(monkeypatch, approver, approver2, submitted_claim):
    # Request B's view of the world: fetched before A acts
    stale = Claim.objects.select_related("employee").get(pk=submitted_claim.pk)
    assert stale.status == "SUBMITTED"

    # Request A wins the race
    services.approve_claim(claim_id=submitted_claim.pk, actor=approver)
    events_before = ClaimEvent.objects.filter(claim=submitted_claim).count()

    # Request B continues with its stale object (as it would on SQLite without a row lock)
    monkeypatch.setattr(services, "_lock", lambda claim_id: stale)
    with pytest.raises(InvalidTransition) as exc:
        services.approve_claim(
            claim_id=submitted_claim.pk,
            actor=approver2,
            approved_override=Decimal("100.00"),
            comment="should never land",
        )
    assert exc.value.extra["current_status"] == "APPROVED"

    fresh = Claim.objects.get(pk=submitted_claim.pk)
    assert fresh.reviewer_id == approver.id
    assert fresh.total_approved == Decimal("8000.00")
    assert ClaimEvent.objects.filter(claim=submitted_claim).count() == events_before  # B wrote nothing
    assert all(i.approved_amount == i.amount for i in fresh.items.all())  # B's item writes rolled back


def test_stale_submit_is_rejected_by_cas(monkeypatch, employee, draft_claim):
    stale = Claim.objects.select_related("employee").get(pk=draft_claim.pk)
    services.submit_claim(claim_id=draft_claim.pk, actor=employee)  # first click

    monkeypatch.setattr(services, "_lock", lambda claim_id: stale)
    with pytest.raises(InvalidTransition):
        services.submit_claim(claim_id=draft_claim.pk, actor=employee)  # second click, stale view

    assert Claim.objects.get(pk=draft_claim.pk).submission_count == 1
