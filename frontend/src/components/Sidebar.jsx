import { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { clearToken } from "../auth.js";

const linkClass = ({ isActive }) =>
  [
    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
    isActive ? "bg-accent text-white" : "text-slate-300 hover:bg-sidebar-hover hover:text-white",
  ].join(" ");

const subLinkClass = ({ isActive }) =>
  [
    "block rounded-md py-1.5 pl-10 pr-3 text-xs transition-colors",
    isActive ? "bg-white/10 text-white" : "text-slate-400 hover:text-white",
  ].join(" ");

export default function Sidebar() {
  const nav = useNavigate();
  const [assetsOpen, setAssetsOpen] = useState(false);

  function logout() {
    clearToken();
    nav("/login", { replace: true });
  }

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-[220px] flex-col border-r border-slate-800 bg-sidebar text-slate-100">
      <div className="border-b border-slate-800 px-4 py-5">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">Dealership</div>
        <div className="text-sm font-semibold leading-snug text-white">Creative Automation Tool</div>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-4">
        <NavLink to="/dashboard" className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/create" className={linkClass}>
          Create Creatives
        </NavLink>
        <NavLink to="/history" className={linkClass}>
          Creatives History
        </NavLink>

        <div>
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-300 hover:bg-sidebar-hover hover:text-white"
            onClick={() => setAssetsOpen((o) => !o)}
          >
            <span className="w-4 text-center text-slate-500">{assetsOpen ? "▾" : "▸"}</span>
            Assets
          </button>
          {assetsOpen && (
            <div className="mt-1 space-y-0.5 pb-2">
              <NavLink to="/assets/panels" className={subLinkClass}>
                Panels
              </NavLink>
              <NavLink to="/assets/logos" className={subLinkClass}>
                Logos
              </NavLink>
            </div>
          )}
        </div>

        <NavLink to="/accounts" className={linkClass}>
          Accounts
        </NavLink>
        <NavLink to="/dealerships" className={linkClass}>
          Dealerships
        </NavLink>
        <NavLink to="/settings" className={linkClass}>
          Settings
        </NavLink>
        <NavLink to="/users" className={linkClass}>
          Users
        </NavLink>
      </nav>

      <div className="border-t border-slate-800 p-2">
        <button
          type="button"
          onClick={logout}
          className="flex w-full items-center rounded-lg px-3 py-2.5 text-left text-sm font-medium text-slate-400 hover:bg-sidebar-hover hover:text-white"
        >
          Logout
        </button>
      </div>
    </aside>
  );
}
