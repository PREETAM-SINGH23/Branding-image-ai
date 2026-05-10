import { useEffect } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./auth.js";
import DashboardLayout from "./layouts/DashboardLayout.jsx";
import Login from "./pages/Login.jsx";
import PlaceholderPage from "./pages/PlaceholderPage.jsx";
import Studio from "./pages/Studio.jsx";

function PrivateRoute({ children }) {
  return getToken() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  useEffect(() => {
    function onLogout() {
      window.location.href = "/login";
    }
    window.addEventListener("auth:logout", onLogout);
    return () => window.removeEventListener("auth:logout", onLogout);
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          element={
            <PrivateRoute>
              <DashboardLayout />
            </PrivateRoute>
          }
        >
          <Route path="/" element={<Navigate to="/create" replace />} />
          <Route path="/create" element={<Studio />} />
          <Route
            path="/dashboard"
            element={<PlaceholderPage title="Dashboard" description="Overview widgets and KPIs can go here." />}
          />
          <Route
            path="/history"
            element={<PlaceholderPage title="Creatives History" description="Past jobs and downloads will be listed here." />}
          />
          <Route
            path="/assets/panels"
            element={<PlaceholderPage title="Assets — Panels" description="Upload and manage dealership panel PNGs." />}
          />
          <Route
            path="/assets/logos"
            element={<PlaceholderPage title="Assets — Logos" description="Manage brand logos per account." />}
          />
          <Route
            path="/accounts"
            element={<PlaceholderPage title="Accounts" description="CRUD for brands / accounts." />}
          />
          <Route
            path="/dealerships"
            element={<PlaceholderPage title="Dealerships" description="Global dealership directory (optional extension)." />}
          />
          <Route path="/settings" element={<PlaceholderPage title="Settings" />} />
          <Route path="/users" element={<PlaceholderPage title="Users" />} />
        </Route>
        <Route path="*" element={<Navigate to="/create" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
