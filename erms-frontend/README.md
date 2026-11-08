# ERMS – frontend

React 18 + Redux Toolkit + Tailwind v4, built with Vite. Talks to the Django backend in `erms-backend`.

## 1. Run it

```bash
npm install
cp .env.example .env          # VITE_API_URL defaults to http://127.0.0.1:8000/api
npm run dev                   # http://localhost:5173
```

Start the backend first (`python manage.py runserver`); it already allows CORS from `localhost:5173`. Sign in with any demo user — the login page has one-click buttons, password `Password@123`.

`npm run build` produces `dist/` for static hosting.

## 2. Structure

```
src/
  main.jsx                   Provider + App
  App.jsx                    routes (react-router); fetchMe on refresh
  index.css                  Tailwind import, pastel tokens, .btn / .input / .card classes
  api/client.js              axios instance, token header, 401 → login, toApiError()
  app/store.js               configureStore with three slices
  features/
    auth/authSlice.js        login / fetchMe / logout
    categories/categoriesSlice.js
    claims/claimsSlice.js    list, current claim, events, every mutation
  components/                Layout, ProtectedRoute, StatusBadge, LifecycleStrip, Modal,
                             ErrorBanner, ItemForm, ApproveDialog, RejectDialog, EventTimeline
  pages/                     LoginPage, ClaimsListPage, NewClaimPage, ClaimDetailPage
  utils/format.js            money(), date(), today()
```

## 3. How data flows

1. A page dispatches a thunk: `dispatch(approveClaim({ id, body }))`.
2. The thunk calls axios. The request interceptor adds `Authorization: Token …`.
3. Success → the thunk resolves with the **fresh claim** from the API; the slice's `fulfilled` matcher writes it to `state.claims.current.claim`. Every mutation returns the full claim, so there is one reducer for all of them (`isAnyOf(...)`).
4. Failure → `toApiError()` normalises the response into `{status, message, code, currentStatus, fieldErrors}` and the thunk rejects with it; the `rejected` matcher stores it in `state.claims.action.error`, which `ErrorBanner` shows.
5. Pages call `dispatch(thunk).unwrap()` when they need to branch on success (close a dialog, navigate). On a 409 the detail page re-reads the claim, because the backend is telling us it moved.

Item add/edit/remove endpoints return the item, not the claim, so those thunks `POST` then `GET` the claim — totals live on the claim.

## 4. Things deliberately left simple

- No pagination control (page size is 20; a footer note appears when there's more).
- No optimistic updates; every mutation waits for the server and replaces the claim.
- Token in `localStorage`. Fine for a demo; a real app would use an httpOnly cookie.
- `window.confirm` for delete.
- No tests on the frontend; the behaviour that matters is tested in the backend.

## 6. Palette

Defined once in `index.css` under `@theme`: paper `#eef2f5`, ink `#243139`, mint `#7cc2af` (primary), butter `#fbf3d5` (reviewer notes), and one pastel per status — slate, sky, mint, rose, lilac. Change a token there and every `bg-mint-500` / `text-muted` follows.
