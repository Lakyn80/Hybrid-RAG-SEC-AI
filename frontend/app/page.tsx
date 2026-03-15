import { Dashboard } from "@/components/Dashboard";

export default function HomePage() {
  return (
    <main className="min-h-screen overflow-hidden bg-canvas text-ink">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(248,250,252,0.08),_transparent_26%),linear-gradient(180deg,_rgba(255,255,255,0.02),_rgba(0,0,0,0))]" />
      <div className="pointer-events-none absolute inset-0 bg-hero-grid bg-[size:48px_48px] opacity-30" />
      <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-[linear-gradient(180deg,_rgba(248,250,252,0.08),_transparent)]" />
      <Dashboard />
    </main>
  );
}
