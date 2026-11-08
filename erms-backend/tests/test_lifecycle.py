import re

import pytest

pytestmark = pytest.mark.django_db


def test_create_submit_approve_pay(client_for, employee, approver, travel, today):
    emp = client_for(employee)
    apr = client_for(approver)

    # Create with one item in a single request
    res = emp.post(
        "/api/claims/",
        {
            "title": "Train to Pune",
            "items": [{"category": travel.id, "description": "Train", "expense_date": str(today), "amount": "1200.00"}],
        },
        format="json",
    )
    assert res.status_code == 201, res.data
    claim = res.data
    assert claim["status"] == "DRAFT"
    assert re.fullmatch(r"CLM-\d{4}-\d{4}", claim["claim_number"])
    assert claim["total_claimed"] == "1200.00"
    assert claim["allowed_actions"] == ["edit", "delete", "submit"]
    claim_id = claim["id"]

    # Submit
    res = emp.post(f"/api/claims/{claim_id}/submit/")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "SUBMITTED"
    assert res.data["submission_count"] == 1
    assert res.data["allowed_actions"] == []  # employee can't do anything now

    # Approver sees it in the queue with the right buttons
    res = apr.get(f"/api/claims/{claim_id}/")
    assert res.status_code == 200
    assert res.data["allowed_actions"] == ["approve", "reject"]

    # Full approval — no body needed
    res = apr.post(f"/api/claims/{claim_id}/approve/", {}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "APPROVED"
    assert res.data["total_approved"] == "1200.00"
    assert res.data["is_partial"] is False
    assert res.data["reviewer"]["username"] == "priya"
    assert res.data["items"][0]["approved_amount"] == "1200.00"

    # Pay
    res = apr.post(f"/api/claims/{claim_id}/pay/", {}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "PAID"
    assert res.data["payment_reference"].startswith("DEMO-PAY-")
    assert res.data["paid_by"]["username"] == "priya"

    # History
    res = emp.get(f"/api/claims/{claim_id}/events/")
    assert [e["action"] for e in res.data] == ["CREATED", "SUBMITTED", "APPROVED", "PAID"]
    assert res.data[-1]["data"]["amount"] == "1200.00"


def test_reject_reopen_fix_resubmit(client_for, employee, approver, submitted_claim):
    emp = client_for(employee)
    apr = client_for(approver)
    cid = submitted_claim.pk

    res = apr.post(f"/api/claims/{cid}/reject/", {"comment": "Attach the cab receipt."}, format="json")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "REJECTED"
    assert res.data["reviewer_comment"] == "Attach the cab receipt."
    assert res.data["allowed_actions"] == []

    # Employee sees why and can reopen
    res = emp.get(f"/api/claims/{cid}/")
    assert res.data["allowed_actions"] == ["reopen"]
    res = emp.post(f"/api/claims/{cid}/reopen/")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "DRAFT"
    assert res.data["reviewer_comment"] == "Attach the cab receipt."  # still visible while fixing

    # Fix an item, resubmit
    item_id = res.data["items"][0]["id"]
    res = emp.patch(f"/api/claims/{cid}/items/{item_id}/", {"amount": "5500.00"}, format="json")
    assert res.status_code == 200, res.data
    res = emp.post(f"/api/claims/{cid}/submit/")
    assert res.status_code == 200, res.data
    assert res.data["status"] == "SUBMITTED"
    assert res.data["submission_count"] == 2
    assert res.data["total_claimed"] == "7500.00"
    assert res.data["reviewer_comment"] == ""  # cleared for the next reviewer

    actions = [e["action"] for e in emp.get(f"/api/claims/{cid}/events/").data]
    assert actions == ["CREATED", "SUBMITTED", "REJECTED", "REOPENED", "ITEM_UPDATED", "RESUBMITTED"]


def test_draft_editing_and_delete(client_for, employee, travel, today):
    emp = client_for(employee)
    res = emp.post("/api/claims/", {"title": "Scratch"}, format="json")
    cid = res.data["id"]
    assert res.data["total_claimed"] == "0.00"

    res = emp.patch(f"/api/claims/{cid}/", {"title": "Scratch v2", "description": "notes"}, format="json")
    assert res.status_code == 200 and res.data["title"] == "Scratch v2"

    res = emp.post(
        f"/api/claims/{cid}/items/",
        {"category": travel.id, "description": "Auto", "expense_date": str(today), "amount": "150.00"},
        format="json",
    )
    assert res.status_code == 201, res.data
    item_id = res.data["id"]
    assert emp.get(f"/api/claims/{cid}/").data["total_claimed"] == "150.00"

    res = emp.delete(f"/api/claims/{cid}/items/{item_id}/")
    assert res.status_code == 204
    assert emp.get(f"/api/claims/{cid}/").data["total_claimed"] == "0.00"

    res = emp.delete(f"/api/claims/{cid}/")
    assert res.status_code == 204
    assert emp.get(f"/api/claims/{cid}/").status_code == 404
