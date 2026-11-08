from django.contrib import admin

from .models import Claim, ClaimEvent, ClaimItem, ExpenseCategory


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "max_amount", "is_active")
    list_filter = ("is_active",)


class ClaimItemInline(admin.TabularInline):
    model = ClaimItem
    extra = 0
    readonly_fields = ("approved_amount",)


class ClaimEventInline(admin.TabularInline):
    model = ClaimEvent
    extra = 0
    can_delete = False
    readonly_fields = ("actor", "action", "from_status", "to_status", "comment", "data", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = ("claim_number", "title", "employee", "status", "total_claimed", "total_approved", "reviewer", "updated_at")
    list_filter = ("status",)
    search_fields = ("claim_number", "title", "employee__username", "employee__employee_code")
    readonly_fields = ("claim_number", "total_claimed", "total_approved", "submission_count", "created_at", "updated_at")
    inlines = [ClaimItemInline, ClaimEventInline]


@admin.register(ClaimEvent)
class ClaimEventAdmin(admin.ModelAdmin):
    list_display = ("claim", "action", "actor", "from_status", "to_status", "created_at")
    list_filter = ("action",)
    readonly_fields = ("claim", "actor", "action", "from_status", "to_status", "comment", "data", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
