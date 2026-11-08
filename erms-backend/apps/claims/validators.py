"""
validation functions. it return a list of error strings (empty = valid)
so the same rules can be reused by the anyone
"""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone


def item_errors(*, category, amount, expense_date, description) -> list[str]:
    errors: list[str] = []

    if not (description or "").strip():
        errors.append("Description is required.")

    if amount is None or amount <= 0:
        errors.append("Amount must be greater than zero.")

    today = timezone.localdate()
    if expense_date is None:
        errors.append("Expense date is required.")
    else:
        if expense_date > today:
            errors.append("Expense date cannot be in the future.")
        max_age = settings.CLAIM_MAX_EXPENSE_AGE_DAYS
        if expense_date < today - timedelta(days=max_age):
            errors.append(f"Expenses older than {max_age} days cannot be claimed.")

    if category is None:
        errors.append("Category is required.")
    else:
        if not category.is_active:
            errors.append(f"Category {category.code} is inactive.")
        if category.max_amount is not None and amount is not None and amount > category.max_amount:
            errors.append(f"Amount exceeds the {category.code} limit of {category.max_amount}.")

    return errors


def receipt_errors(file) -> list[str]:
    if file is None:
        return []
    limit = settings.MAX_RECEIPT_SIZE_MB * 1024 * 1024
    if file.size > limit:
        return [f"Receipt must be under {settings.MAX_RECEIPT_SIZE_MB} MB."]
    return []
