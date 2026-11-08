"""
Business-rule exceptions raised by the service layer, plus the DRF handler
that turns them into JSON responses. Services never import DRF; views never
decide status codes — this file is the only bridge.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    code = "domain_error"
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail, **extra):
        super().__init__(detail)
        self.detail = detail  # str or list[str]
        self.extra = extra  # e.g. current_status="APPROVED"


class ValidationFailed(DomainError):
    """Request shape is fine but a business rule is broken (missing items, amount over cap...)."""

    code = "validation_error"
    http_status = status.HTTP_400_BAD_REQUEST


class NotPermitted(DomainError):
    """Caller is authenticated but not allowed to do this to this claim."""

    code = "not_permitted"
    http_status = status.HTTP_403_FORBIDDEN


class NotFound(DomainError):
    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND


class InvalidTransition(DomainError):
    """Claim is not in the state this action needs — includes lost races and duplicate requests."""

    code = "invalid_transition"
    http_status = status.HTTP_409_CONFLICT


def domain_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response({"detail": exc.detail, "code": exc.code, **exc.extra}, status=exc.http_status)
    return drf_exception_handler(exc, context)
