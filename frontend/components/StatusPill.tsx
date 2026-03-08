import { ReactNode } from "react";

type Variant = "neutral" | "info" | "success" | "warning" | "danger";

interface StatusPillProps {
  label: ReactNode;
  variant?: Variant;
}

const VARIANTS: Record<Variant, string> = {
  neutral: "border-slate-200 bg-white text-slate-600",
  info: "border-cyan-200 bg-cyan-50 text-cyan-700",
  success: "border-emerald-200 bg-emerald-50 text-emerald-700",
  warning: "border-amber-200 bg-amber-50 text-amber-700",
  danger: "border-red-200 bg-red-50 text-red-700",
};

export function StatusPill({
  label,
  variant = "neutral",
}: StatusPillProps) {
  return (
    <span className={`inline-flex rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] ${VARIANTS[variant]}`}>
      {label}
    </span>
  );
}
