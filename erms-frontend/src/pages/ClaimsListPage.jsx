import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate } from "react-router-dom";
import { fetchClaims } from "../features/claims/claimsSlice";
import StatusBadge from "../components/StatusBadge";
import ErrorBanner from "../components/ErrorBanner";
import { dateTime, money } from "../utils/format";

// Each tab maps to query params the API understands (see selectors.py on the backend).
const EMPLOYEE_TABS = [
  { key: "all", label: "All", params: {} },
  { key: "DRAFT", label: "Drafts", params: { status: "DRAFT" } },
  { key: "SUBMITTED", label: "Submitted", params: { status: "SUBMITTED" } },
  { key: "APPROVED", label: "Approved", params: { status: "APPROVED" } },
  { key: "REJECTED", label: "Rejected", params: { status: "REJECTED" } },
  { key: "PAID", label: "Paid", params: { status: "PAID" } },
];

const APPROVER_TABS = [
  { key: "queue", label: "To review", params: { status: "SUBMITTED" } },
  { key: "APPROVED", label: "Approved", params: { status: "APPROVED" } },
  { key: "PAID", label: "Paid", params: { status: "PAID" } },
  { key: "REJECTED", label: "Rejected", params: { status: "REJECTED" } },
  { key: "reviewed", label: "Reviewed by me", params: { reviewed_by_me: "true" } },
  { key: "mine", label: "My own claims", params: { mine: "true" } },
];

// we are driving pagination by API's next/prev this is just to calculate things
const PAGE_SIZE = 20;

export default function ClaimsListPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useSelector((state) => state.auth.user);
  const { items, count, hasNext, hasPrevious, status, error } = useSelector((state) => state.claims.list);

  const isApprover = user.role === "APPROVER";
  const tabs = isApprover ? APPROVER_TABS : EMPLOYEE_TABS;
  const [tabKey, setTabKey] = useState(tabs[0].key);
  const [page, setPage] = useState(1);
  const tab = tabs.find((t) => t.key === tabKey) ?? tabs[0];

  useEffect(() => {
    dispatch(fetchClaims({ ...tab.params, page }));
  }, [dispatch, tab, page]);

  // DRF returns 404 "Invalid page." if the page no longer exists (e.g. claims moved
  // out of this tab). Fall back to page 1 instead of showing an error.
  useEffect(() => {
    if (status === "failed" && error?.status === 404 && page > 1) setPage(1);
  }, [status, error, page]);

  const selectTab = (key) => {
    setTabKey(key);
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  const firstShown = (page - 1) * PAGE_SIZE + 1;
  const lastShown = firstShown + items.length - 1;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">{isApprover ? "Claims to review" : "My claims"}</h1>
        <Link to="/claims/new" className="btn btn-primary">New claim</Link>
      </div>

      <div className="mb-4 flex flex-wrap gap-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => selectTab(t.key)}
            className={`rounded-md px-3 py-1.5 text-sm ${t.key === tab.key ? "bg-mint-100 text-mint-700 font-medium" : "text-muted hover:text-ink"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <ErrorBanner error={error} />

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-pastel/60 text-left text-muted">
            <tr>
              <th className="px-4 py-2 font-normal">Claim</th>
              {isApprover && <th className="px-4 py-2 font-normal">Employee</th>}
              <th className="px-4 py-2 font-normal">Status</th>
              <th className="px-4 py-2 text-right font-normal">Claimed</th>
              <th className="px-4 py-2 text-right font-normal">Approved</th>
              <th className="px-4 py-2 font-normal">Updated</th>
            </tr>
          </thead>
          <tbody>
            {status === "loading" && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-muted">Loading…</td></tr>
            )}
            {status === "succeeded" && items.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-6 text-center text-muted">Nothing here yet.</td></tr>
            )}
            {items.map((claim) => (
              <tr
                key={claim.id}
                onClick={() => navigate(`/claims/${claim.id}`)}
                className="cursor-pointer border-t border-line hover:bg-mint-100/50"
              >
                <td className="px-4 py-2">
                  <div className="font-medium">{claim.title}</div>
                  <div className="text-xs text-muted">{claim.claim_number}, {claim.item_count} item{claim.item_count === 1 ? "" : "s"}</div>
                </td>
                {isApprover && <td className="px-4 py-2">{claim.employee.full_name}</td>}
                <td className="px-4 py-2">
                  <StatusBadge status={claim.status} />
                  {claim.is_partial && <span className="ml-1 text-xs text-muted">partial</span>}
                </td>
                <td className="px-4 py-2 text-right">{money(claim.total_claimed)}</td>
                <td className="px-4 py-2 text-right">{money(claim.total_approved)}</td>
                <td className="px-4 py-2 text-muted">{dateTime(claim.updated_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {count > 0 && (hasNext || hasPrevious) && (
        <div className="mt-3 flex items-center justify-between text-sm">
          <span className="text-muted">
            {status === "succeeded" ? `Showing ${firstShown}–${lastShown} of ${count}` : " "}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!hasPrevious || status === "loading"}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Previous
            </button>
            <span className="text-muted">Page {page} of {totalPages}</span>
            <button
              type="button"
              className="btn btn-secondary"
              disabled={!hasNext || status === "loading"}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
