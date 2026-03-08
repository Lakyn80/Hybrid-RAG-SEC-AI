import { Dashboard } from "@/components/Dashboard";

export default function HomePage() {
  return (
    <main className="min-h-screen overflow-hidden bg-canvas text-ink">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(14,116,144,0.12),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(245,158,11,0.1),_transparent_28%),linear-gradient(180deg,_rgba(255,255,255,0.4),_rgba(248,250,252,0.95))]" />
      <div className="pointer-events-none absolute inset-0 bg-hero-grid bg-[size:40px_40px] opacity-60" />
      <Dashboard />
    </main>
  );
}
