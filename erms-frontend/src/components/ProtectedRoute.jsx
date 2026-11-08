import { useSelector } from "react-redux";
import { Navigate, Outlet, useLocation } from "react-router-dom";

export default function ProtectedRoute() {
  const { token, user } = useSelector((state) => state.auth);
  const location = useLocation();

  if (!token) return <Navigate to="/login" replace state={{ from: location }} />;
  if (!user) return <p className="p-8 text-muted">Loading your account…</p>;
  return <Outlet />;
}
