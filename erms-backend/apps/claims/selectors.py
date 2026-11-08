"""Filters for reading or showing on Frontend."""

from django.db.models import Count, Q

from .exceptions import ValidationFailed
from .models import Claim, ClaimStatus

TRUE_VALUES = {"1", "true", "yes"}


def claims_visible_to(user):
    qs = (
        Claim.objects.select_related("employee", "reviewer", "paid_by")
        .prefetch_related("items__category")
        .annotate(item_count=Count("items", distinct=True))
        # Meta.ordering is dropped on aggregate queries; be explicit so pagination is stable.
        .order_by("-created_at", "-id")
    )
    own = Q(employee=user)
    if user.is_approver:
        # Approvers see everything that has left Draft, plus their own claims in any state.
        return qs.filter(own | ~Q(status=ClaimStatus.DRAFT))
    return qs.filter(own)


def apply_list_filters(qs, user, params):
    raw_status = params.get("status")
    if raw_status:
        wanted = [s.strip().upper() for s in raw_status.split(",") if s.strip()]
        unknown = [s for s in wanted if s not in ClaimStatus.values]
        if unknown:
            raise ValidationFailed(f"Unknown status: {', '.join(unknown)}. Use one of {', '.join(ClaimStatus.values)}.")
        qs = qs.filter(status__in=wanted)

    if params.get("mine", "").lower() in TRUE_VALUES:
        qs = qs.filter(employee=user)

    if params.get("reviewed_by_me", "").lower() in TRUE_VALUES:
        qs = qs.filter(reviewer=user)

    return qs
