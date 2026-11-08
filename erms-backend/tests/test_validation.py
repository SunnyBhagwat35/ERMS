from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

pytestmark = pytest.mark.django_db


def test_submit_without_items(client_for, employee):
    emp = client_for(employee)
    cid = emp.post("/api/claims/", {"title": "Empty"}, format="json").data["id"]
    res = emp.post(f"/api/claims/{cid}/submit/")
    assert res.status_code == 400
    assert res.data["code"] == "validation_error"
    assert "at least one expense item" in res.data["detail"][0]


def test_create_without_title(client_for, employee):
    res = client_for(employee).post("/api/claims/", {"description": "no title"}, format="json")
    assert res.status_code == 400
    assert "title" in res.data


def test_future_expense_date(client_for, employee, travel, today):
    res = client_for(employee).post(
        "/api/claims/",
        {
            "title": "Time travel",
            "items": [
                {
                    "category": travel.id,
                    "description": "Cab",
                    "expense_date": str(today + timedelta(days=1)),
                    "amount": "100.00",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == 400
    assert any("future" in e for e in res.data["detail"])


def test_expense_too_old(client_for, employee, travel, today, settings):
    settings.CLAIM_MAX_EXPENSE_AGE_DAYS = 30
    res = client_for(employee).post(
        "/api/claims/",
        {
            "title": "Old",
            "items": [
                {
                    "category": travel.id,
                    "description": "Cab",
                    "expense_date": str(today - timedelta(days=31)),
                    "amount": "100.00",
                }
            ],
        },
        format="json",
    )
    assert res.status_code == 400
    assert any("older than 30 days" in e for e in res.data["detail"])


def test_category_cap(client_for, employee, food, today):
    res = client_for(employee).post(
        "/api/claims/",
        {
            "title": "Big lunch",
            "items": [{"category": food.id, "description": "Lunch", "expense_date": str(today), "amount": "2500.00"}],
        },
        format="json",
    )
    assert res.status_code == 400
    assert any("exceeds the FOOD limit" in e for e in res.data["detail"])


def test_inactive_category(client_for, employee, food, today):
    food.is_active = False
    food.save()
    res = client_for(employee).post(
        "/api/claims/",
        {
            "title": "Old category",
            "items": [{"category": food.id, "description": "Lunch", "expense_date": str(today), "amount": "500.00"}],
        },
        format="json",
    )
    assert res.status_code == 400
    assert any("inactive" in e for e in res.data["detail"])


def test_negative_amount_rejected_by_serializer(client_for, employee, draft_claim, travel, today):
    res = client_for(employee).post(
        f"/api/claims/{draft_claim.pk}/items/",
        {"category": travel.id, "description": "x", "expense_date": str(today), "amount": "-5.00"},
        format="json",
    )
    assert res.status_code == 400
    assert "amount" in res.data


def test_reject_requires_comment(client_for, approver, submitted_claim):
    res = client_for(approver).post(f"/api/claims/{submitted_claim.pk}/reject/", {}, format="json")
    assert res.status_code == 400
    assert "comment" in res.data

    res = client_for(approver).post(f"/api/claims/{submitted_claim.pk}/reject/", {"comment": "   "}, format="json")
    assert res.status_code == 400


def test_receipt_upload_multipart(client_for, employee, draft_claim, travel, today):
    receipt = SimpleUploadedFile("bill.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    res = client_for(employee).post(
        f"/api/claims/{draft_claim.pk}/items/",
        {"category": travel.id, "description": "Hotel", "expense_date": str(today), "amount": "900.00", "receipt": receipt},
        format="multipart",
    )
    assert res.status_code == 201, res.data
    assert res.data["receipt"].endswith("bill.pdf")


def test_receipt_wrong_extension(client_for, employee, draft_claim, travel, today):
    receipt = SimpleUploadedFile("virus.exe", b"MZ", content_type="application/octet-stream")
    res = client_for(employee).post(
        f"/api/claims/{draft_claim.pk}/items/",
        {"category": travel.id, "description": "Hotel", "expense_date": str(today), "amount": "900.00", "receipt": receipt},
        format="multipart",
    )
    assert res.status_code == 400
    assert "receipt" in res.data


def test_receipt_too_large(client_for, employee, draft_claim, travel, today, settings):
    settings.MAX_RECEIPT_SIZE_MB = 0  # anything is too big
    receipt = SimpleUploadedFile("bill.pdf", b"%PDF-1.4 fake", content_type="application/pdf")
    res = client_for(employee).post(
        f"/api/claims/{draft_claim.pk}/items/",
        {"category": travel.id, "description": "Hotel", "expense_date": str(today), "amount": "900.00", "receipt": receipt},
        format="multipart",
    )
    assert res.status_code == 400
    assert "receipt" in res.data
