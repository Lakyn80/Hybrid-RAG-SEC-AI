import { ReactNode } from "react";

type Variant = "neutral" | "info" | "success" | "warning" | "danger";

interface StatusPillProps {
  label: ReactNode;
  variant?: Variant;
}

const VARIANTS: Record<Variant, string> = {
  neutral: "border-line bg-white/5 text-slate-300",
  info: "border-[#f5d15a]/30 bg-[#f5d15a]/10 text-[#f6db7d]",
  success: "border-slate-400 bg-slate-200/10 text-slate-100",
  warning: "border-amber-500/35 bg-amber-500/10 text-amber-200",
  danger: "border-red-500/35 bg-red-500/10 text-red-200",
};

export function StatusPill({
  label,
  variant = "neutral",
}: StatusPillProps) {
  return (
    <span className={`inline-flex rounded-[2px] border px-3 py-1 font-mono text-[11px] uppercase tracking-[0.16em] ${VARIANTS[variant]}`}>
      {label}
    </span>
  );
}
