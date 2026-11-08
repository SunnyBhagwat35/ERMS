from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (("ERMS", {"fields": ("role", "employee_code", "department")}),)
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("ERMS", {"fields": ("email", "role", "employee_code", "department")}),
    )
    list_display = ("employee_code", "username", "first_name", "last_name", "role", "department", "is_active")
    list_filter = ("role", "department", "is_active")
    search_fields = ("username", "employee_code", "first_name", "last_name", "email")
