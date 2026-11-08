import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  addItem,
  approveClaim,
  clearActionError,
  clearCurrent,
  deleteClaim,
  fetchClaim,
  fetchEvents,
  payClaim,
  rejectClaim,
  removeItem,
  reopenClaim,
  submitClaim,
  updateClaim,
  updateItem,
} from "../features/claims/claimsSlice";
import { fetchCategories } from "../features/categories/categoriesSlice";
import StatusBadge from "../components/StatusBadge";
import LifecycleStrip from "../components/LifecycleStrip";
import ErrorBanner from "../components/ErrorBanner";
import ItemForm from "../components/ItemForm";
import ApproveDialog from "../components/ApproveDialog";
import RejectDialog from "../components/RejectDialog";
import EventTimeline from "../components/EventTimeline";
import { date, dateTime, money } from "../utils/format";

export default function ClaimDetailPage() {
  const { id } = useParams();
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { claim, events, status, error } = useSelector((state) => state.claims.current);
  const action = useSelector((state) => state.claims.action);
  const categories = useSelector((state) => state.categories.items);

  const [dialog, setDialog] = useState(null); // "approve" | "reject" | null
  const [editingHeader, setEditingHeader] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [paymentRef, setPaymentRef] = useState("");

  useEffect(() => {
    dispatch(fetchClaim(id));
    dispatch(fetchEvents(id));
    dispatch(fetchCategories());
    return () => dispatch(clearCurrent()); // don't show a stale claim when navigating to another id
  }, [dispatch, id]);

  // The backend tells us which buttons this user may use right now.
  const can = (name) => Boolean(claim?.allowed_actions?.includes(name));
  const busy = action.status === "loading";

  // Run a mutation, then refresh the timeline. Any error ends up in state.claims.action.error.
  // On a 409 the claim moved under us, so re-read it instead of showing stale buttons.
  const run = async (thunk) => {
    try {
      await dispatch(thunk).unwrap();
      dispatch(fetchEvents(id));
      return true;
    } catch (err) {
      if (err?.status === 409) {
        dispatch(fetchClaim(id));
        dispatch(fetchEvents(id));
      }
      return false;
    }
  };

  const onDelete = async () => {
    if (!window.confirm("Delete this draft? This cannot be undone.")) return;
    try {
      await dispatch(deleteClaim(id)).unwrap();
      navigate("/claims");
    } catch {
      // error shown by ErrorBanner
    }
  };

  const onItemSubmit = async (body) => {
    const ok = editingItem
      ? await run(updateItem({ id, itemId: editingItem.id, body }))
      : await run(addItem({ id, body }));
    if (ok) setEditingItem(null);
    return ok;
  };

  if (status === "loading" && !claim) return <p className="text-muted">Loading claim…</p>;
  if (error && !claim) return <ErrorBanner error={error} />;
  if (!claim) return null;

  const isEditable = can("edit");
  const showApproved = ["APPROVED", "PAID"].includes(claim.status);

  return (
    <div className="space-y-5">
      <Link to="/claims" className="text-sm text-muted hover:text-ink">← All claims</Link>

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">{claim.claim_number}</p>
          <h1 className="text-2xl font-semibold">{claim.title}</h1>
          <p className="text-sm text-muted">
            {claim.employee.full_name} ({claim.employee.department || claim.employee.employee_code}), created {date(claim.created_at)}
            {claim.submission_count > 1 && `, submitted ${claim.submission_count} times`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <StatusBadge status={claim.status} />
          {isEditable && (
            <button type="button" onClick={() => setEditingHeader((v) => !v)} className="btn btn-secondary">
              {editingHeader ? "Close" : "Edit details"}
            </button>
          )}
        </div>
      </div>

      <LifecycleStrip status={claim.status} />

      <ErrorBanner error={action.error} onDismiss={() => dispatch(clearActionError())} />

      {claim.reviewer_comment && (
        <div className={`rounded-md border px-3 py-2 text-sm ${claim.status === "REJECTED" ? "border-rose-pastel bg-rose-pastel/40" : "border-butter-300 bg-butter-100"}`}>
          <span className="font-medium">{claim.reviewer?.full_name ?? "Reviewer"}:</span> {claim.reviewer_comment}
        </div>
      )}

      {editingHeader && (
        <HeaderForm
          claim={claim}
          busy={busy}
          onSave={async (body) => {
            const ok = await run(updateClaim({ id, body }));
            if (ok) setEditingHeader(false);
          }}
        />
      )}

      {claim.description && <p className="text-sm">{claim.description}</p>}

      {/* Totals */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat label="Claimed" value={money(claim.total_claimed)} />
        {showApproved && (
          <Stat label={claim.is_partial ? "Approved (partial)" : "Approved"} value={money(claim.total_approved)} highlight={claim.is_partial} />
        )}
        {claim.submitted_at && <Stat label="Submitted" value={dateTime(claim.submitted_at)} />}
        {claim.paid_at && <Stat label="Paid" value={`${dateTime(claim.paid_at)} (${claim.payment_reference})`} />}
      </div>

      {/* Items */}
      <section className="card">
        <div className="flex items-center justify-between border-b border-line px-4 py-3">
          <h2 className="font-semibold">Expense items</h2>
          {isEditable && <span className="text-xs text-muted">Draft: you can add, edit and remove items</span>}
        </div>
        <table className="w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="px-4 py-2 font-normal">Category</th>
              <th className="px-4 py-2 font-normal">Description</th>
              <th className="px-4 py-2 font-normal">Date</th>
              <th className="px-4 py-2 text-right font-normal">Amount</th>
              {showApproved && <th className="px-4 py-2 text-right font-normal">Approved</th>}
              <th className="px-4 py-2 font-normal">Receipt</th>
              {isEditable && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {claim.items.length === 0 && (
              <tr><td colSpan={7} className="px-4 py-4 text-center text-muted">No items yet. Add at least one before submitting.</td></tr>
            )}
            {claim.items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="px-4 py-2">{item.category_name}</td>
                <td className="px-4 py-2">{item.description}</td>
                <td className="px-4 py-2">{date(item.expense_date)}</td>
                <td className="px-4 py-2 text-right">{money(item.amount)}</td>
                {showApproved && (
                  <td className={`px-4 py-2 text-right ${Number(item.approved_amount) < Number(item.amount) ? "text-mint-700 font-medium" : ""}`}>
                    {money(item.approved_amount)}
                  </td>
                )}
                <td className="px-4 py-2">
                  {item.receipt ? <a href={item.receipt} target="_blank" rel="noreferrer" className="text-mint-700 underline">View</a> : <span className="text-muted">—</span>}
                </td>
                {isEditable && (
                  <td className="px-4 py-2 text-right whitespace-nowrap">
                    <button type="button" onClick={() => setEditingItem(item)} className="mr-2 text-sm text-mint-700 hover:underline" disabled={busy}>Edit</button>
                    <button type="button" onClick={() => run(removeItem({ id, itemId: item.id }))} className="text-sm text-muted hover:text-ink hover:underline" disabled={busy}>Remove</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {isEditable && (
          <div className="border-t border-line bg-slate-pastel/40 px-4 py-4">
            <h3 className="mb-3 text-sm font-medium">{editingItem ? `Edit item: ${editingItem.description}` : "Add an item"}</h3>
            <ItemForm
              categories={categories}
              initial={editingItem}
              onSubmit={onItemSubmit}
              onCancel={() => setEditingItem(null)}
              busy={busy}
            />
          </div>
        )}
      </section>

      {/* Actions */}
      {claim.allowed_actions.length > 0 && (
        <section className="card flex flex-wrap items-center gap-2 px-4 py-3">
          {can("submit") && (
            <button type="button" onClick={() => run(submitClaim(id))} className="btn btn-primary" disabled={busy || claim.items.length === 0}>
              Submit for approval
            </button>
          )}
          {can("delete") && (
            <button type="button" onClick={onDelete} className="btn btn-danger" disabled={busy}>Delete draft</button>
          )}
          {can("approve") && (
            <button type="button" onClick={() => setDialog("approve")} className="btn btn-primary" disabled={busy}>Approve</button>
          )}
          {can("reject") && (
            <button type="button" onClick={() => setDialog("reject")} className="btn btn-danger" disabled={busy}>Reject</button>
          )}
          {can("reopen") && (
            <button type="button" onClick={() => run(reopenClaim(id))} className="btn btn-primary" disabled={busy}>Reopen and fix</button>
          )}
          {can("pay") && (
            <>
              <input
                value={paymentRef}
                onChange={(e) => setPaymentRef(e.target.value)}
                placeholder="Payment reference (optional)"
                className="input w-64"
                aria-label="Payment reference"
              />
              <button type="button" onClick={() => run(payClaim({ id, payment_reference: paymentRef }))} className="btn btn-primary" disabled={busy}>
                Mark as paid
              </button>
            </>
          )}
        </section>
      )}

      {/* History */}
      <section className="card p-4">
        <h2 className="mb-3 font-semibold">History</h2>
        <EventTimeline events={events} />
      </section>

      {/* Dialogs are keyed so their internal state resets each time they open. */}
      {dialog === "approve" && (
        <ApproveDialog
          key={`approve-${claim.id}`}
          claim={claim}
          open
          busy={busy}
          error={action.error}
          onClose={() => { setDialog(null); dispatch(clearActionError()); }}
          onConfirm={async (body) => {
            const ok = await run(approveClaim({ id, body }));
            if (ok) setDialog(null);
          }}
        />
      )}
      {dialog === "reject" && (
        <RejectDialog
          key={`reject-${claim.id}`}
          claim={claim}
          open
          busy={busy}
          error={action.error}
          onClose={() => { setDialog(null); dispatch(clearActionError()); }}
          onConfirm={async (comment) => {
            const ok = await run(rejectClaim({ id, comment }));
            if (ok) setDialog(null);
          }}
        />
      )}
    </div>
  );
}

function Stat({ label, value, highlight }) {
  return (
    <div className={`card px-3 py-2 ${highlight ? "border-mint-300 bg-mint-100" : ""}`}>
      <p className="text-xs text-muted">{label}</p>
      <p className="text-sm font-medium">{value}</p>
    </div>
  );
}

function HeaderForm({ claim, busy, onSave }) {
  const [form, setForm] = useState({ title: claim.title, description: claim.description });
  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });
  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSave(form); }}
      className="card space-y-3 p-4"
    >
      <div>
        <label className="label" htmlFor="edit-title">Title</label>
        <input id="edit-title" name="title" value={form.title} onChange={onChange} className="input" required maxLength={200} />
      </div>
      <div>
        <label className="label" htmlFor="edit-description">Description</label>
        <textarea id="edit-description" name="description" value={form.description} onChange={onChange} className="input" rows={2} />
      </div>
      <div className="flex justify-end">
        <button type="submit" className="btn btn-primary" disabled={busy}>Save details</button>
      </div>
    </form>
  );
}
