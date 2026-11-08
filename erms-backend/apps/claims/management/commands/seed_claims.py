"""
Creates sample claims in every lifecycle state, going through the service
layer so totals and event history are exactly what the real API would produce.

    python manage.py loaddata users categories
    python manage.py seed_claims
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.claims import services
from apps.claims.models import Claim, ExpenseCategory

User = get_user_model()


class Command(BaseCommand):
    help = "Seed demo claims (draft, submitted, partially approved, rejected, paid)."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Seed even if claims already exist.")

    def handle(self, *args, **options):
        if Claim.objects.exists() and not options["force"]:
            self.stdout.write(self.style.WARNING("Claims already exist; nothing done. Use --force to add more."))
            return

        try:
            rahul = User.objects.get(username="rahul.verma")
            neha = User.objects.get(username="neha.gupta")
            priya = User.objects.get(username="priya.sharma")
            arjun = User.objects.get(username="arjun.mehta")
            travel = ExpenseCategory.objects.get(code="TRAVEL")
            food = ExpenseCategory.objects.get(code="FOOD")
            hotel = ExpenseCategory.objects.get(code="ACCOMMODATION")
            internet = ExpenseCategory.objects.get(code="INTERNET")
        except ObjectDoesNotExist as exc:
            raise CommandError("Fixtures missing. Run: python manage.py loaddata users categories") from exc

        today = timezone.localdate()

        def day(n):
            return today - timedelta(days=n)

        def item(category, description, days_ago, amount):
            return {
                "category": category,
                "description": description,
                "expense_date": day(days_ago),
                "amount": Decimal(amount),
            }

        # 1. Draft — Rahul is still adding items
        services.create_claim(
            employee=rahul,
            title="Client visit – Pune",
            description="Two-day onsite with the Pune client.",
            items=[item(travel, "Mumbai–Pune cab", 3, "2800.00"), item(food, "Team lunch", 3, "1450.00")],
        )

        # 2. Submitted — waiting in the approver queue
        c2 = services.create_claim(
            employee=neha,
            title="Marketing conference – Bengaluru",
            items=[
                item(travel, "Flight BOM–BLR return", 10, "9800.00"),
                item(hotel, "2 nights hotel", 9, "8400.00"),
                item(food, "Meals during conference", 9, "1900.00"),
            ],
        )
        services.submit_claim(claim_id=c2.pk, actor=neha)

        # 3. Partially approved — hotel capped by Priya
        c3 = services.create_claim(
            employee=rahul,
            title="Onsite support – Hyderabad",
            items=[item(travel, "Train fare", 20, "2200.00"), item(hotel, "Hotel 1 night", 19, "5800.00")],
        )
        services.submit_claim(claim_id=c3.pk, actor=rahul)
        services.approve_claim(
            claim_id=c3.pk,
            actor=priya,
            item_decisions=[{"id": c3.items.get(category=hotel).id, "approved_amount": Decimal("4300.00")}],
            comment="Hotel reimbursed at policy rate of ₹4,300/night.",
        )

        # 4. Rejected — missing receipt, Neha needs to reopen and fix
        c4 = services.create_claim(
            employee=neha,
            title="Home internet – October",
            items=[item(internet, "Broadband bill", 25, "1299.00")],
        )
        services.submit_claim(claim_id=c4.pk, actor=neha)
        services.reject_claim(claim_id=c4.pk, actor=arjun, comment="Please attach the broadband invoice and resubmit.")

        # 5. Paid — full cycle done
        c5 = services.create_claim(
            employee=rahul,
            title="Local travel – September",
            items=[item(travel, "Auto/cab for client meetings", 40, "1650.00")],
        )
        services.submit_claim(claim_id=c5.pk, actor=rahul)
        services.approve_claim(claim_id=c5.pk, actor=arjun)
        services.mark_paid(claim_id=c5.pk, actor=arjun, payment_reference="DEMO-NEFT-000921")

        # 6. Approver's own claim — Priya cannot review this one; Arjun can
        c6 = services.create_claim(
            employee=priya,
            title="Finance offsite – Lonavala",
            items=[item(travel, "Shared cab", 6, "1200.00"), item(food, "Dinner", 6, "900.00")],
        )
        services.submit_claim(claim_id=c6.pk, actor=priya)

        self.stdout.write(self.style.SUCCESS("Seeded 6 claims: draft, submitted x2, partially approved, rejected, paid."))
