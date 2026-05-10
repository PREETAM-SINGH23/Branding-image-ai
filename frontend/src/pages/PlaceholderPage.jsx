import { useNavigate } from "react-router-dom";

export default function PlaceholderPage({ title, description }) {
  const nav = useNavigate();
  return (
    <div className="p-6">
      <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-2 max-w-xl text-slate-600">
          {description || "This area is a placeholder for a future screen. Data and APIs are not wired yet."}
        </p>
        <button
          type="button"
          onClick={() => nav("/create")}
          className="mt-6 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover"
        >
          Go to Create Creatives
        </button>
      </div>
    </div>
  );
}
