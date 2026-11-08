import { useState } from "react";
import Modal from "./Modal";
import ErrorBanner from "./ErrorBanner";

export default function RejectDialog({ claim, open, onClose, onConfirm, busy, error }) {
  const [comment, setComment] = useState("");

  const submit = (e) => {
    e.preventDefault();
    onConfirm(comment);
  };

  return (
    <Modal open={open} title={`Reject ${claim.claim_number}`} onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <ErrorBanner error={error} />
        <p className="text-sm text-muted">Tell the employee what to fix. They can reopen the claim, correct it and resubmit.</p>
        <div>
          <label className="label" htmlFor="reject-comment">Reason</label>
          <textarea id="reject-comment" value={comment} onChange={(e) => setComment(e.target.value)} className="input" rows={3} required />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="btn btn-secondary" disabled={busy}>Cancel</button>
          <button type="submit" className="btn btn-danger" disabled={busy || !comment.trim()}>
            {busy ? "Rejecting…" : "Reject claim"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
