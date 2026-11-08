import { useDispatch, useSelector } from "react-redux";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { logout } from "../features/auth/authSlice";

const navClass = ({ isActive }) =>
  `rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-mint-100 text-mint-700" : "text-muted hover:text-ink"}`;

export default function Layout() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const user = useSelector((state) => state.auth.user);

  const onLogout = async () => {
    await dispatch(logout());
    navigate("/login");
  };

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-4 px-4 py-3">
          <Link to="/claims" className="text-lg font-semibold">
            ERMS
          </Link>
          <nav className="flex gap-1">
            <NavLink to="/claims" end className={navClass}>
              Claims
            </NavLink>
            <NavLink to="/claims/new" className={navClass}>
              New claim
            </NavLink>
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            <span>{user.full_name}</span>
            <span className={`rounded-full px-2 py-0.5 text-xs ${user.role === "APPROVER" ? "bg-lilac-pastel" : "bg-sky-pastel"}`}>
              {user.role === "APPROVER" ? "Approver" : "Employee"}
            </span>
            <button type="button" onClick={onLogout} className="btn btn-secondary">
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
