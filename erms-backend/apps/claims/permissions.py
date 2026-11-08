from rest_framework.permissions import BasePermission


class IsApprover(BasePermission):
    """Cheap role gate for approver-only endpoints. The service layer re-checks."""

    message = "Only approvers can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_approver)
