import { dateTime, money } from "../utils/format";

const LABEL = {
  CREATED: "Created",
  UPDATED: "Details updated",
  ITEM_ADDED: "Item added",
  ITEM_UPDATED: "Item updated",
  ITEM_REMOVED: "Item removed",
  SUBMITTED: "Submitted for approval",
  RESUBMITTED: "Resubmitted",
  APPROVED: "Approved in full",
  PARTIALLY_APPROVED: "Partially approved",
  REJECTED: "Rejected",
  REOPENED: "Reopened for correction",
  PAID: "Marked as paid",
};

// One short, human line per event built from the JSON snapshot the backend stored.
function summary(event) {
  const d = event.data || {};
  switch (event.action) {
    case "ITEM_ADDED":
    case "ITEM_REMOVED":
      return d.item ? `${d.item.description} — ${money(d.item.amount)}` : null;
    case "ITEM_UPDATED":
      return d.changes ? Object.entries(d.changes).map(([k, v]) => `${k}: ${v.from} → ${v.to}`).join(", ") : null;
    case "UPDATED":
      return d.changes ? Object.keys(d.changes).join(", ") + " changed" : null;
    case "SUBMITTED":
    case "RESUBMITTED":
      return `Total ${money(d.total_claimed)}`;
    case "APPROVED":
    case "PARTIALLY_APPROVED":
      return `${money(d.total_approved)} of ${money(d.total_claimed)}`;
    case "PAID":
      return `${money(d.amount)} (ref ${d.payment_reference})`;
    default:
      return null;
  }
}

export default function EventTimeline({ events }) {
  if (!events.length) return <p className="text-sm text-muted">No history yet.</p>;
  return (
    <ol className="space-y-3">
      {events.map((event) => (
        <li key={event.id} className="flex gap-3 text-sm">
          <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-mint-500" aria-hidden="true" />
          <div>
            <p>
              <span className="font-medium">{LABEL[event.action] ?? event.action}</span>
              <span className="text-muted"> by {event.actor?.full_name ?? "system"}, {dateTime(event.created_at)}</span>
            </p>
            {summary(event) && <p className="text-muted">{summary(event)}</p>}
            {event.comment && <p className="mt-1 rounded bg-butter-100 px-2 py-1">“{event.comment}”</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
