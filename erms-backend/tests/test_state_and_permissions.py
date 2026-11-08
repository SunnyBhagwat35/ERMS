"""Invalid transitions (409), duplicate requests (409), role/ownership rules (403/404), visibility."""

from decimal import Decimal

import pytest

pytestmark = pytest.mark.django_db


# --- 409: wrong state / duplicate request -----------------------------------


def test_approve_a_draft_is_409(client_for, approver, draft_claim):
    # Approver can see the draft? No — drafts of others are invisible, so 404 not 409.
    res = client_for(approver).post(f"/api/claims/{draft_claim.pk}/approve/", {}, format="json")
    assert res.status_code == 404


def test_double_submit_is_409(client_for, employee, draft_claim):
    emp = client_for(employee)
    assert emp.post(f"/api/claims/{draft_claim.pk}/submit/").status_code == 200
    res = emp.post(f"/api/claims/{draft_claim.pk}/submit/")  # duplicate click
    assert res.status_code == 409
    assert res.data["code"] == "invalid_transition"
    assert res.data["current_status"] == "SUBMITTED"
    draft_claim.refresh_from_db()
    assert draft_claim.submission_count == 1  # counted once


def test_double_approve_is_409(client_for, approver, approver2, submitted_claim):
    assert client_for(approver).post(f"/api/claims/{submitted_claim.pk}/approve/", {}, format="json").status_code == 200
    res = client_for(approver2).post(f"/api/claims/{submitted_claim.pk}/approve/", {}, format="json")
    assert res.status_code == 409
    assert res.data["current_status"] == "APPROVED"
    submitted_claim.refresh_from_db()
    assert submitted_claim.reviewer_id == approver.id  # first approver kept


def test_pay_before_approval_is_409(client_for, approver, submitted_claim):
    res = client_for(approver).post(f"/api/claims/{submitted_claim.pk}/pay/", {}, format="json")
    assert res.status_code == 409


def test_reject_after_approve_is_409(client_for, approver, submitted_claim):
    apr = client_for(approver)
    apr.post(f"/api/claims/{submitted_claim.pk}/approve/", {}, format="json")
    res = apr.post(f"/api/claims/{submitted_claim.pk}/reject/", {"comment": "changed my mind"}, format="json")
    assert res.status_code == 409


def test_edit_after_submit_is_409(client_for, employee, submitted_claim, travel, today):
    emp = client_for(employee)
    cid = submitted_claim.pk
    assert emp.patch(f"/api/claims/{cid}/", {"title": "sneaky"}, format="json").status_code == 409
    res = emp.post(
        f"/api/claims/{cid}/items/",
        {"category": travel.id, "description": "x", "expense_date": str(today), "amount": "1.00"},
        format="json",
    )
    assert res.status_code == 409
    assert emp.delete(f"/api/claims/{cid}/").status_code == 409


def test_reopen_non_rejected_is_409(client_for, employee, submitted_claim):
    assert client_for(employee).post(f"/api/claims/{submitted_claim.pk}/reopen/").status_code == 409


def test_paid_is_terminal(client_for, employee, approver, submitted_claim):
    apr = client_for(approver)
    apr.post(f"/api/claims/{submitted_claim.pk}/approve/", {}, format="json")
    apr.post(f"/api/claims/{submitted_claim.pk}/pay/", {}, format="json")
    assert apr.post(f"/api/claims/{submitted_claim.pk}/pay/", {}, format="json").status_code == 409
    assert client_for(employee).post(f"/api/claims/{submitted_claim.pk}/reopen/").status_code == 409


# --- 403: role / ownership --------------------------------------------------


def test_employee_cannot_approve(client_for, employee, submitted_claim):
    res = client_for(employee).post(f"/api/claims/{submitted_claim.pk}/approve/", {}, format="json")
    assert res.status_code == 403


def test_approver_cannot_review_own_claim(client_for, approver, approver2, travel, today):
    from apps.claims import services

    own = services.create_claim(
        employee=approver,
        title="My own trip",
        items=[{"category": travel, "description": "Cab", "expense_date": today, "amount": Decimal("300.00")}],
    )
    services.submit_claim(claim_id=own.pk, actor=approver)

    me = client_for(approver)
    assert me.get(f"/api/claims/{own.pk}/").data["allowed_actions"] == []
    assert me.post(f"/api/claims/{own.pk}/approve/", {}, format="json").status_code == 403
    assert me.post(f"/api/claims/{own.pk}/reject/", {"comment": "x"}, format="json").status_code == 403

    # A different approver can
    assert client_for(approver2).post(f"/api/claims/{own.pk}/approve/", {}, format="json").status_code == 200
    assert me.post(f"/api/claims/{own.pk}/pay/", {}, format="json").status_code == 403


def test_other_employee_cannot_see_or_touch_claim(client_for, employee2, draft_claim):
    other = client_for(employee2)
    assert other.get(f"/api/claims/{draft_claim.pk}/").status_code == 404
    assert other.post(f"/api/claims/{draft_claim.pk}/submit/").status_code == 404
    assert other.delete(f"/api/claims/{draft_claim.pk}/").status_code == 404
    assert other.get("/api/claims/").data["count"] == 0


def test_unauthenticated_is_401(draft_claim):
    from rest_framework.test import APIClient

    assert APIClient().get("/api/claims/").status_code == 401


# --- visibility & filters ---------------------------------------------------


def test_approver_sees_submitted_not_drafts(client_for, approver, employee, draft_claim, travel, today):
    from apps.claims import services

    other = services.create_claim(
        employee=employee,
        title="Submitted one",
        items=[{"category": travel, "description": "Cab", "expense_date": today, "amount": Decimal("100.00")}],
    )
    services.submit_claim(claim_id=other.pk, actor=employee)

    apr = client_for(approver)
    listed = {c["claim_number"] for c in apr.get("/api/claims/").data["results"]}
    assert other.claim_number in listed
    assert draft_claim.claim_number not in listed

    queue = apr.get("/api/claims/?status=SUBMITTED").data["results"]
    assert [c["id"] for c in queue] == [other.pk]

    assert apr.get("/api/claims/?status=BOGUS").status_code == 400


def test_reviewed_by_me_filter(client_for, approver, approver2, submitted_claim):
    client_for(approver).post(f"/api/claims/{submitted_claim.pk}/approve/", {}, format="json")
    assert client_for(approver).get("/api/claims/?reviewed_by_me=true").data["count"] == 1
    assert client_for(approver2).get("/api/claims/?reviewed_by_me=true").data["count"] == 0
