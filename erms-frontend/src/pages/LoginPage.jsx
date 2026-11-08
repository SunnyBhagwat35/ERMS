import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { clearAuthError, login } from "../features/auth/authSlice";
import ErrorBanner from "../components/ErrorBanner";

const DEMO_USERS = [
  { username: "rahul.verma", label: "Rahul (employee)" },
  { username: "neha.gupta", label: "Neha (employee)" },
  { username: "priya.sharma", label: "Priya (approver)" },
  { username: "arjun.mehta", label: "Arjun (approver)" },
];

export default function LoginPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { token, user, status, error } = useSelector((state) => state.auth);
  const [form, setForm] = useState({ username: "", password: "Password@123" });

  useEffect(() => {
    if (token && user) navigate("/claims", { replace: true });
  }, [token, user, navigate]);

  const onChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const onSubmit = (e) => {
    e.preventDefault();
    dispatch(login(form));
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="card w-full max-w-md p-6">
        <h1 className="text-xl font-semibold">Sign in to ERMS</h1>
        <p className="mb-5 text-sm text-muted">Expense claims for employees, reviews for approvers.</p>

        <ErrorBanner error={error} onDismiss={() => dispatch(clearAuthError())} />

        <form onSubmit={onSubmit} className="space-y-3">
          <div>
            <label className="label" htmlFor="username">Username</label>
            <input id="username" name="username" value={form.username} onChange={onChange} className="input" autoComplete="username" required autoFocus />
          </div>
          <div>
            <label className="label" htmlFor="password">Password</label>
            <input id="password" type="password" name="password" value={form.password} onChange={onChange} className="input" autoComplete="current-password" required />
          </div>
          <button type="submit" className="btn btn-primary w-full" disabled={status === "loading"}>
            {status === "loading" ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="mt-6 border-t border-line pt-4">
          <p className="mb-2 text-sm text-muted">Demo accounts (password is prefilled):</p>
          <div className="flex flex-wrap gap-2">
            {DEMO_USERS.map((u) => (
              <button key={u.username} type="button" onClick={() => setForm({ ...form, username: u.username })} className="btn btn-secondary">
                {u.label}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
