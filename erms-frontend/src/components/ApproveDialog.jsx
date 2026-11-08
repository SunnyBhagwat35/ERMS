import { useState } from "react";
import Modal from "./Modal";
import ErrorBanner from "./ErrorBanner";
import { money } from "../utils/format";

/**
 * Partial approval UI: one input per item (defaults to the full amount), an
 * optional claim-level override, and a comment that becomes required when the
 * approved total is below the claimed total. The backend re-validates all of it.
 */
export default function ApproveDialog({ claim, open, onClose, onConfirm, busy, error }) {
  const [amounts, setAmounts] = useState(() => Object.fromEntries(claim.items.map((i) => [i.id, i.amount])));
  const [override, setOverride] = useState("");
  const [comment, setComment] = useState("");

  const itemSum = claim.items.reduce((sum, i) => sum + Number(amounts[i.id] || 0), 0);
  const total = override !== "" ? Number(override) : itemSum;
  const isPartial = total < Number(claim.total_claimed);

  const submit = (e) => {
    e.preventDefault();
    onConfirm({
      items: claim.items.map((i) => ({ id: i.id, approved_amount: amounts[i.id] })),
      approved_override: override === "" ? null : override,
      comment,
    });
  };

  return (
    <Modal open={open} title={`Approve ${claim.claim_number}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorBanner error={error} />
        <table className="w-full text-sm">
          <thead className="text-left text-muted">
            <tr>
              <th className="pb-1 font-normal">Item</th>
              <th className="pb-1 text-right font-normal">Claimed</th>
              <th className="pb-1 text-right font-normal">Approve</th>
            </tr>
          </thead>
          <tbody>
            {claim.items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="py-2">
                  {item.description}
                  <span className="ml-1 text-xs text-muted">({item.category_code})</span>
                </td>
                <td className="py-2 text-right">{money(item.amount)}</td>
                <td className="py-2 text-right">
                  <input
                    type="number"
                    min="0"
                    max={item.amount}
                    step="0.01"
                    value={amounts[item.id]}
                    onChange={(e) => setAmounts({ ...amounts, [item.id]: e.target.value })}
                    className="input w-32 text-right"
                    aria-label={`Approved amount for ${item.description}`}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label" htmlFor="override">Override total (optional)</label>
            <input
              id="override"
              type="number"
              min="0"
              max={claim.total_claimed}
              step="0.01"
              value={override}
              onChange={(e) => setOverride(e.target.value)}
              className="input"
              placeholder="Leave blank to use item amounts"
            />
          </div>
          <div className="self-end text-sm">
            <div className="flex justify-between"><span className="text-muted">Claimed</span><span>{money(claim.total_claimed)}</span></div>
            <div className="flex justify-between font-semibold"><span>Will approve</span><span>{money(total)}</span></div>
            {isPartial && <p className="mt-1 text-xs text-muted">Partial approval — a comment is required.</p>}
          </div>
        </div>

        <div>
          <label className="label" htmlFor="comment">Comment {isPartial ? "(required)" : "(optional)"}</label>
          <textarea id="comment" value={comment} onChange={(e) => setComment(e.target.value)} className="input" rows={2} required={isPartial} />
        </div>

        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="btn btn-secondary" disabled={busy}>Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Approving…" : isPartial ? `Approve ${money(total)}` : "Approve in full"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
