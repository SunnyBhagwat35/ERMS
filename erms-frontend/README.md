# ERMS frontend

React 18 + Redux Toolkit + Tailwind v4, built with Vite. It talks only to the Django API in [erms-backend](../erms-backend/). For the overview and design decisions, see the [root README](../README.md).

## 1. Run it

Requires Node 18+. Start the backend first (`python manage.py runserver`); it already allows CORS from `localhost:5173`.

```bash
npm install
cp .env.example .env    # VITE_API_URL defaults to http://127.0.0.1:8000/api
npm run dev             # http://localhost:5173
```

Sign in with any demo user. The login page has one-click buttons, and the password is `Password@123`.

`npm run build` writes a static bundle to `dist/`.

## 2. Screens

| Page | Employee | Approver |
|------|----------|----------|
| **Claims list** | Tabs: All / Drafts / Submitted / Approved / Rejected / Paid | Tabs: To review / Approved / Paid / Rejected / Reviewed by me / My own claims |
| **New claim** | Title, description, expense items with receipts | Same (approvers can file their own claims) |
| **Claim detail** | Edit, delete, submit drafts; reopen rejected claims; history timeline | Approve (full or partial per item, or an override total), reject with comment, mark paid |

Buttons come from the API's `allowed_actions` list. The UI never decides on its own whether an action is allowed.

## 3. Structure

```
src/
  main.jsx                   Provider + App
  App.jsx                    routes (react-router); fetchMe on refresh
  index.css                  Tailwind import, theme tokens, .btn / .input / .card classes
  api/client.js              axios instance, token header, 401 → login, toApiError()
  app/store.js               configureStore with three slices
  features/
    auth/authSlice.js        login / fetchMe / logout
    categories/categoriesSlice.js
    claims/claimsSlice.js    list, current claim, events, every mutation
  components/                Layout, ProtectedRoute, StatusBadge, LifecycleStrip, Modal,
                             ErrorBanner, ItemForm, ApproveDialog, RejectDialog, EventTimeline
  pages/                     LoginPage, ClaimsListPage, NewClaimPage, ClaimDetailPage
  utils/format.js            money() (INR), date(), today()
```

## 4. How data flows

1. A page dispatches a thunk, for example `dispatch(approveClaim({ id, body }))`.
2. The thunk calls axios, and the request interceptor adds `Authorization: Token …`.
3. **Success:** every mutation endpoint returns the **fresh claim**. One shared `fulfilled` matcher (`isAnyOf(...)`) writes it to `state.claims.current.claim`, so there is one reducer for all mutations.
4. **Failure:** `toApiError()` normalises the response into `{status, message, code, currentStatus, fieldErrors}`. The `rejected` matcher stores it in `state.claims.action.error`, and `ErrorBanner` displays it.
5. When a page needs to act on the result (close a dialog, navigate), it calls `.unwrap()`. On a **409** the detail page fetches the claim again, because the backend is saying the claim changed underneath us.

The item add/edit/remove endpoints return the item rather than the claim, so those thunks `POST` and then `GET` the claim. The totals live on the claim.

Money arrives as decimal strings. It is formatted for display only and never used in floating-point arithmetic. The approve dialog's running total is only a preview, and the backend computes the real total.

## 5. Kept simple on purpose

- The API pages at 20, and a footer note appears when there are more.
- The token lives in `localStorage`.
- `window.confirm` for delete.
