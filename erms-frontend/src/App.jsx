import { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { fetchMe } from "./features/auth/authSlice";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import ClaimsListPage from "./pages/ClaimsListPage";
import NewClaimPage from "./pages/NewClaimPage";
import ClaimDetailPage from "./pages/ClaimDetailPage";

export default function App() {
  const dispatch = useDispatch();
  const { token, user } = useSelector((state) => state.auth);

  // After a page refresh the token survives in localStorage but the user object doesn't.
  useEffect(() => {
    if (token && !user) dispatch(fetchMe());
  }, [token, user, dispatch]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        {/* Nested routes: ProtectedRoute and Layout render an <Outlet/> where the child page goes. */}
        <Route element={<ProtectedRoute />}>
          <Route element={<Layout />}>
            <Route index element={<Navigate to="/claims" replace />} />
            <Route path="/claims" element={<ClaimsListPage />} />
            <Route path="/claims/new" element={<NewClaimPage />} />
            <Route path="/claims/:id" element={<ClaimDetailPage />} />
          </Route>
        </Route>
        <Route path="*" element={<Navigate to="/claims" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
