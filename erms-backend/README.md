# ERMS backend

Django 5 + Django REST Framework API for the Employee Reimbursement Management System. SQLite storage, DRF token auth, pytest.

For the product overview, data model and design decisions, see the [root README](../README.md).

---

## 1. Setup

Requires Python 3.11+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python manage.py migrate                    
python manage.py loaddata users categories 
python manage.py seed_claims                
python manage.py runserver
```

- API root: `http://127.0.0.1:8000/api/`
- Django admin: `http://127.0.0.1:8000/admin/` (user `admin`, password `Password@123`)
- Postman collection: [postman/ERMS.postman_collection.json](postman/ERMS.postman_collection.json)

**Reset the database:** `rm -rf db.sqlite3 media/`, then run the commands again from `migrate`.

### Environment variables (`.env`)
* look at [ erms-backend/.env.example ](erms-backend/.env.example )

## 2. Tests

```bash
pytest          # 37 tests
pytest -k partial
```

| File | Covers |
|------|--------|
| `test_lifecycle.py` | Happy paths: create → submit → approve → pay; reject → reopen → fix → resubmit; draft edit and delete |
| `test_partial_approval.py` | Per-item amounts, claim-level override, mandatory comment, out-of-range amounts, foreign item ids |
| `test_state_and_permissions.py` | Invalid transitions (409), duplicate requests, role and ownership checks, visibility, filters |
| `test_validation.py` | Missing title or items, future or stale dates, category caps, inactive category, receipt type and size |
| `test_concurrency.py` | Simulates two requests interleaving on the same claim; the stale one gets 409 |

## 3. API

All endpoints except login need `Authorization: Token <token>`.

| Method | Path | Who | Notes |
|--------|------|-----|-------|
| POST | `/api/auth/login/` | anyone | `{username, password}` → `{token, user}` |
| GET | `/api/auth/me/` | any user | Current user |
| POST | `/api/auth/logout/` | any user | Deletes the token |
| GET | `/api/categories/` | any user | Expense categories and caps |
| GET | `/api/claims/` | any user | Filters: `?status=SUBMITTED,APPROVED`, `?mine=true`, `?reviewed_by_me=true`. Paged at 20 |
| POST | `/api/claims/` | any user | Create a draft (optionally with `items`) |
| GET | `/api/claims/{id}/` | owner / approver | Includes `items`, totals and `allowed_actions` |
| PATCH | `/api/claims/{id}/` | owner, DRAFT | Edit title or description |
| DELETE | `/api/claims/{id}/` | owner, DRAFT | Hard delete |
| POST | `/api/claims/{id}/items/` | owner, DRAFT | Add an item (JSON or multipart with `receipt`) |
| PATCH / DELETE | `/api/claims/{id}/items/{item_id}/` | owner, DRAFT | Edit or remove an item |
| POST | `/api/claims/{id}/submit/` | owner | DRAFT → SUBMITTED |
| POST | `/api/claims/{id}/approve/` | approver, not owner | `{items: [{id, approved_amount}], approved_override?, comment}` |
| POST | `/api/claims/{id}/reject/` | approver, not owner | `{comment}` (required) |
| POST | `/api/claims/{id}/reopen/` | owner | REJECTED → DRAFT |
| POST | `/api/claims/{id}/pay/` | approver, not owner | `{payment_reference?}` |
| GET | `/api/claims/{id}/events/` | owner / approver | Full history |

### Error format

Every error has the same structure:

```json
{"detail": "Claim is APPROVED; this action requires SUBMITTED.", "code": "invalid_transition", "current_status": "APPROVED"}
```

## 4. Folder structure

```
config/                 settings (read from env), root urls
apps/accounts/          custom User (role, employee_code), login/me/logout, users fixture
apps/claims/
  models.py             ExpenseCategory, Claim, ClaimItem, ClaimEvent + DB CHECK constraints
  services.py           Has functions which performs one action. The single file to look for claim changes.
  validators.py         pure rule functions, run on add/update and again on submit
  selectors.py          queryset + list filters for claims
  serializers.py        our serializers
  views.py              gets object calls serializer calls service and sends fresh detail response
  exceptions.py         Some custom exceptions
  permissions.py        custom permission classes
  management/commands/seed_claims.py
  fixtures/categories.json
tests/                  pytest suite
postman/                Postman collection
```

## 5. Concurrency and duplicate requests

Every transition in `services.py` runs inside `transaction.atomic()` and works like this:

1. `_lock()` loads the claim with `select_for_update()`.
2. The service checks the actor, the current status and the business rules.
3. `_transition()` runs a guarded update:
   ```python
   Claim.objects.filter(pk=claim.pk, status=from_status).update(status=to_status, ...)
   ```
4. If zero rows were updated, another request moved the claim first. The service raises `InvalidTransition` (409), and the transaction rolls back everything else that request wrote (item approvals, events).

Django ignores `select_for_update()` on SQLite, so step 3 is what actually protects the data here. On PostgreSQL the row lock in step 1 also applies, with no code change. This covers double clicks (submit twice, approve twice) and two approvers acting at the same time. [tests/test_concurrency.py](tests/test_concurrency.py) reproduces the interleaving.
