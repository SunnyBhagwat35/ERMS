from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.claims import services
from apps.claims.models import ExpenseCategory

User = get_user_model()


@pytest.fixture(autouse=True)
def _media_tmp(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"  # never write receipts into the repo during tests


@pytest.fixture
def travel(db):
    return ExpenseCategory.objects.create(code="TRAVEL", name="Travel", max_amount=Decimal("25000.00"))


@pytest.fixture
def food(db):
    return ExpenseCategory.objects.create(code="FOOD", name="Meals", max_amount=Decimal("2000.00"))


def _user(username, role, code):
    return User.objects.create_user(
        username=username,
        password="Password@123",
        email=f"{username}@erms.local",
        role=role,
        employee_code=code,
        first_name=username.title(),
    )


@pytest.fixture
def employee(db):
    return _user("rahul", User.Role.EMPLOYEE, "EMP001")


@pytest.fixture
def employee2(db):
    return _user("neha", User.Role.EMPLOYEE, "EMP002")


@pytest.fixture
def approver(db):
    return _user("priya", User.Role.APPROVER, "APR001")


@pytest.fixture
def approver2(db):
    return _user("arjun", User.Role.APPROVER, "APR002")


@pytest.fixture
def client_for():
    """client_for(user) -> APIClient authenticated with that user's token."""

    def make(user):
        client = APIClient()
        token, _ = Token.objects.get_or_create(user=user)
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    return make


@pytest.fixture
def today():
    return timezone.localdate()


@pytest.fixture
def draft_claim(employee, travel, food, today):
    """8,000 total: 5,000 travel + 3,000 food... food is capped at 2,000, so use 6,000 + 2,000."""
    return services.create_claim(
        employee=employee,
        title="Client visit",
        items=[
            {"category": travel, "description": "Cab", "expense_date": today, "amount": Decimal("6000.00")},
            {"category": food, "description": "Lunch", "expense_date": today, "amount": Decimal("2000.00")},
        ],
    )


@pytest.fixture
def submitted_claim(draft_claim, employee):
    return services.submit_claim(claim_id=draft_claim.pk, actor=employee)
