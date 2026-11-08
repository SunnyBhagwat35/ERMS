import pytest

pytestmark = pytest.mark.django_db


def _ids(claim):
    return {i.category.code: i.id for i in claim.items.select_related("category")}


def test_per_item_amounts(client_for, approver, submitted_claim):
    apr = client_for(approver)
    ids = _ids(submitted_claim)
    res = apr.post(
        f"/api/claims/{submitted_claim.pk}/approve/",
        {"items": [{"id": ids["TRAVEL"], "approved_amount": "4500.00"}], "comment": "Cab capped at policy rate."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["status"] == "APPROVED"
    assert res.data["is_partial"] is True
    assert res.data["total_approved"] == "6500.00"  # 4500 + 2000 (unlisted item approved in full)
    assert res.data["approved_override"] is None
    by_code = {i["category_code"]: i["approved_amount"] for i in res.data["items"]}
    assert by_code == {"TRAVEL": "4500.00", "FOOD": "2000.00"}

    events = apr.get(f"/api/claims/{submitted_claim.pk}/events/").data
    assert events[-1]["action"] == "PARTIALLY_APPROVED"
    assert events[-1]["data"]["item_sum"] == "6500.00"


def test_claim_level_override(client_for, approver, submitted_claim):
    apr = client_for(approver)
    res = apr.post(
        f"/api/claims/{submitted_claim.pk}/approve/",
        {"approved_override": "6500.00", "comment": "Budget cap for the quarter."},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert res.data["total_approved"] == "6500.00"
    assert res.data["approved_override"] == "6500.00"
    assert res.data["is_partial"] is True


def test_partial_requires_comment(client_for, approver, submitted_claim):
    res = client_for(approver).post(
        f"/api/claims/{submitted_claim.pk}/approve/", {"approved_override": "6500.00"}, format="json"
    )
    assert res.status_code == 400
    assert "comment" in res.data["detail"].lower()
    submitted_claim.refresh_from_db()
    assert submitted_claim.status == "SUBMITTED"  # nothing changed


def test_item_amount_above_claimed_rejected(client_for, approver, submitted_claim):
    ids = _ids(submitted_claim)
    res = client_for(approver).post(
        f"/api/claims/{submitted_claim.pk}/approve/",
        {"items": [{"id": ids["TRAVEL"], "approved_amount": "9999.00"}], "comment": "x"},
        format="json",
    )
    assert res.status_code == 400
    assert any("between 0 and 6000.00" in e for e in res.data["detail"])


def test_override_above_total_rejected(client_for, approver, submitted_claim):
    res = client_for(approver).post(
        f"/api/claims/{submitted_claim.pk}/approve/", {"approved_override": "9000.00", "comment": "x"}, format="json"
    )
    assert res.status_code == 400
    assert any("Override must be between" in e for e in res.data["detail"])


def test_zero_total_must_be_rejected_instead(client_for, approver, submitted_claim):
    res = client_for(approver).post(
        f"/api/claims/{submitted_claim.pk}/approve/", {"approved_override": "0.00", "comment": "nothing"}, format="json"
    )
    assert res.status_code == 400
    assert "Reject the claim instead" in res.data["detail"]


def test_foreign_item_id_rejected(client_for, approver, submitted_claim):
    res = client_for(approver).post(
        f"/api/claims/{submitted_claim.pk}/approve/",
        {"items": [{"id": 999999, "approved_amount": "1.00"}], "comment": "x"},
        format="json",
    )
    assert res.status_code == 400
    assert any("does not belong" in e for e in res.data["detail"])
