from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """One user table; `role` decides what the person may do in ERMS."""

    class Role(models.TextChoices):
        EMPLOYEE = "EMPLOYEE", "Employee"
        APPROVER = "APPROVER", "Approver"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EMPLOYEE)
    employee_code = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=64, blank=True)

    REQUIRED_FIELDS = ["email", "employee_code"]

    class Meta:
        ordering = ["employee_code"]

    @property
    def is_approver(self) -> bool:
        return self.role == self.Role.APPROVER

    @property
    def full_name(self) -> str:
        return self.get_full_name() or self.username

    def __str__(self) -> str:
        return f"{self.employee_code} {self.full_name} ({self.role})"
