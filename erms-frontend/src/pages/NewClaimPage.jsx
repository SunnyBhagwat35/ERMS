import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { clearActionError, createClaim } from "../features/claims/claimsSlice";
import ErrorBanner from "../components/ErrorBanner";

export default function NewClaimPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const action = useSelector((state) => state.claims.action);
  const [form, setForm] = useState({ title: "", description: "" });

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    try {
      // unwrap() turns a rejected thunk into a thrown error so we can branch on success.
      const claim = await dispatch(createClaim(form)).unwrap();
      navigate(`/claims/${claim.id}`);
    } catch {
      // The error is already in state.claims.action.error; ErrorBanner shows it.
    }
  };

  return (
    <div className="mx-auto max-w-lg">
      <h1 className="mb-1 text-xl font-semibold">New claim</h1>
      <p className="mb-5 text-sm text-muted">Give it a title now; you add expense items on the next screen.</p>
      <ErrorBanner error={action.error} onDismiss={() => dispatch(clearActionError())} />
      <form onSubmit={onSubmit} className="card space-y-3 p-5">
        <div>
          <label className="label" htmlFor="title">Title</label>
          <input id="title" name="title" value={form.title} onChange={onChange} className="input" required maxLength={200} placeholder="Client visit – Pune" />
        </div>
        <div>
          <label className="label" htmlFor="description">Description (optional)</label>
          <textarea id="description" name="description" value={form.description} onChange={onChange} className="input" rows={3} />
        </div>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={() => navigate("/claims")} className="btn btn-secondary">Cancel</button>
          <button type="submit" className="btn btn-primary" disabled={action.status === "loading"}>Create draft</button>
        </div>
      </form>
    </div>
  );
}
