import { Outlet } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-canvas">
      <Sidebar />
      <div className="min-h-screen pl-[220px]">
        <Outlet />
      </div>
    </div>
  );
}
