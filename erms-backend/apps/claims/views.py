from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from . import services
from .models import ExpenseCategory
from .permissions import IsApprover
from .selectors import TRUE_VALUES, apply_list_filters, claims_visible_to
from .serializers import (
    ApproveSerializer,
    ClaimCreateSerializer,
    ClaimDetailSerializer,
    ClaimEventSerializer,
    ClaimItemSerializer,
    ClaimListSerializer,
    ClaimUpdateSerializer,
    ExpenseCategorySerializer,
    PaySerializer,
    RejectSerializer,
)


class ExpenseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExpenseCategorySerializer
    pagination_class = None

    def get_queryset(self):
        qs = ExpenseCategory.objects.all()
        if self.request.query_params.get("all", "").lower() not in TRUE_VALUES:
            qs = qs.filter(is_active=True)
        return qs


class ClaimViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    for ref:
    /api/claims/                     GET list, POST create
    /api/claims/{id}/                GET, PATCH (draft only), DELETE (draft only)
    /api/claims/{id}/items/          POST add item (JSON or multipart)
    /api/claims/{id}/items/{item}/   PATCH, DELETE
    /api/claims/{id}/submit|approve|reject|reopen|pay/   POST
    /api/claims/{id}/events/         GET history
    """

    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    approver_perms = [IsAuthenticated, IsApprover]

    def get_queryset(self):
        return claims_visible_to(self.request.user)

    def get_serializer_class(self):
        return ClaimListSerializer if self.action == "list" else ClaimDetailSerializer

    def _detail(self, claim_id, http_status=status.HTTP_200_OK):
        """Returning Response with updated claims"""
        claim = get_object_or_404(self.get_queryset(), pk=claim_id)
        return Response(ClaimDetailSerializer(claim, context=self.get_serializer_context()).data, status=http_status)

    # Proper Claim API's 

    def list(self, request, *args, **kwargs):
        qs = apply_list_filters(self.get_queryset(), request.user, request.query_params)
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = ClaimCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        claim = services.create_claim(employee=request.user, **serializer.validated_data)
        return self._detail(claim.pk, status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        services.update_claim(claim_id=claim.pk, actor=request.user, **serializer.validated_data)
        return self._detail(claim.pk)

    def destroy(self, request, pk=None):
        claim = self.get_object()
        services.delete_claim(claim_id=claim.pk, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Claim item apis

    @action(detail=True, methods=["post"], url_path="items")
    def add_item(self, request, pk=None):
        claim = self.get_object()
        serializer = ClaimItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = services.add_item(claim_id=claim.pk, actor=request.user, **serializer.validated_data)
        return Response(
            ClaimItemSerializer(item, context=self.get_serializer_context()).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["patch", "delete"], url_path=r"items/(?P<item_id>\d+)")
    def item_detail(self, request, pk=None, item_id=None):
        claim = self.get_object()
        if request.method == "DELETE":
            services.remove_item(claim_id=claim.pk, item_id=int(item_id), actor=request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = ClaimItemSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = services.update_item(
            claim_id=claim.pk, item_id=int(item_id), actor=request.user, **serializer.validated_data
        )
        return Response(ClaimItemSerializer(item, context=self.get_serializer_context()).data)

    # Clain actions api

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        claim = self.get_object()
        services.submit_claim(claim_id=claim.pk, actor=request.user)
        return self._detail(claim.pk)

    @action(detail=True, methods=["post"], permission_classes=approver_perms)
    def approve(self, request, pk=None):
        claim = self.get_object()
        serializer = ApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services.approve_claim(
            claim_id=claim.pk,
            actor=request.user,
            item_decisions=data["items"],
            approved_override=data["approved_override"],
            comment=data["comment"],
        )
        return self._detail(claim.pk)

    @action(detail=True, methods=["post"], permission_classes=approver_perms)
    def reject(self, request, pk=None):
        claim = self.get_object()
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject_claim(claim_id=claim.pk, actor=request.user, comment=serializer.validated_data["comment"])
        return self._detail(claim.pk)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        claim = self.get_object()
        services.reopen_claim(claim_id=claim.pk, actor=request.user)
        return self._detail(claim.pk)

    @action(detail=True, methods=["post"], permission_classes=approver_perms)
    def pay(self, request, pk=None):
        claim = self.get_object()
        serializer = PaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.mark_paid(
            claim_id=claim.pk, actor=request.user, payment_reference=serializer.validated_data["payment_reference"]
        )
        return self._detail(claim.pk)

    # For history API

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        claim = self.get_object()
        events = claim.events.select_related("actor")
        return Response(ClaimEventSerializer(events, many=True).data)
