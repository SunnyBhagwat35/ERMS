# ERMS – Employee Reimbursement Management System (backend)

Django 5 + DRF backend for the intern demo. Employees file expense claims, approvers approve (fully or partially), reject, or mark them paid. No real money moves.

**Stack:** Python 3.11+, Django 5.1+, DRF 3.15+, SQLite, DRF token auth, pytest. Frontend (React + Redux + Tailwind, Vite) comes later and talks to this API over CORS.

---

## 1. Setup

```bash
python -m venv .venv && source .venv/bin/activate 
pip install -r requirements.txt
cp .env.example .env                                  

python manage.py makemigrations accounts claims
python manage.py migrate
python manage.py loaddata users categories             
python manage.py seed_claims                           
python manage.py runserver
```

API root: `http://127.0.0.1:8000/api/` · Admin: `http://127.0.0.1:8000/admin/` (login `admin`).

Run tests: `pytest` (37 tests, ~15 s).

**Rollback / reset:** `rm db.sqlite3 media -rf` and repeat from `migrate`. To undo only the app tables: `python manage.py migrate claims zero && python manage.py migrate accounts zero`.

## 2. Demo users

All passwords: `Password@123`

| Username       | Role     | 
|----------------|----------|
| `admin`        | Approver | 
| `priya.sharma` | Approver | 
| `arjun.mehta`  | Approver | 
| `rahul.verma`  | Employee |
| `neha.gupta`   | Employee |
| `vikram.singh` | Employee |

Approvers can file their own claims but can never approve, reject or pay them — another approver must.

### Error format

All errors use one format:

```json
{"detail": "Claim is APPROVED; this action requires SUBMITTED.", "code": "invalid_transition", "current_status": "APPROVED"}
```

## 4. Lifecycle

Editing (title, items) is only allowed in DRAFT.
Once submitted it can wither approved or rejected if approved reimburse partially or fully. If rejected can be reopened by the owner. Reopengin will send claims to draft 

## 5. The Folder Structure

```
config/                 settings (env-driven), urls
apps/accounts/          custom User with role + employee_code, login/me/logout, users fixture
apps/claims/
  models.py             ExpenseCategory, Claim, ClaimItem, ClaimEvent + DB CHECK constraints
  services.py           ALL writes. One function per action; nothing else mutates a claim.
  validators.py         pure rule functions, reused on add/update and again on submit
  selectors.py          visibility queryset + list filters
  serializers.py        shape/type validation only
  views.py              thin: get_object → serializer → service → fresh detail
  exceptions.py         domain exceptions → HTTP codes (the only DRF-aware bridge)
  permissions.py        IsApprover role gate
  management/commands/seed_claims.py
  fixtures/categories.json
tests/                  pytest suite (lifecycle, partial approval, validation, state/permissions, concurrency)
postman/                collection + the script that generates it
```

## 6. handelling concurrency and duplicate req

Every state transition in `services.py` runs inside `transaction.atomic()`, and we locks the row with `select_for_update()`, then applies the status change:

If zero rows match, someone else moved the claim first — we raise `InvalidTransition` (409) and the transaction rolls back everything else that request wrote (item approvals, events).

**Note:** Django silently ignores `select_for_update()` on SQLite. So i made extra changes. The guarded update is what actually handles it in _transistion(). 
It covers Duplicate clicks (submit twice, approve twice) which gets a clean 409 instead of processing it. `tests/test_concurrency.py` reproduces the interleaving.
