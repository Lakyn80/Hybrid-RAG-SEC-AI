"use client";

import { GraphNodeViewModel } from "@/lib/graphTypes";

interface GraphNodeProps {
  node: GraphNodeViewModel;
  className?: string;
}

function getNodeStyles(state: GraphNodeViewModel["state"]) {
  switch (state) {
    case "active":
      return {
        shell: "border-cyan-400/60 bg-cyan-500/10 text-cyan-100 shadow-[0_0_0_1px_rgba(34,211,238,0.14),0_18px_44px_rgba(8,145,178,0.18)] animate-pulseGlow",
        orb: "border-cyan-300 bg-cyan-400 text-slate-950 shadow-[0_0_18px_rgba(34,211,238,0.35)]",
        accent: "text-cyan-200",
        subtitle: "text-cyan-100/80",
        badge: "border-cyan-300/40 bg-cyan-400/10 text-cyan-100",
      };
    case "completed":
      return {
        shell: "border-emerald-400/50 bg-emerald-500/10 text-emerald-100 shadow-[0_0_0_1px_rgba(16,185,129,0.12),0_18px_40px_rgba(5,150,105,0.16)]",
        orb: "border-emerald-300 bg-emerald-400 text-slate-950",
        accent: "text-emerald-200",
        subtitle: "text-emerald-100/80",
        badge: "border-emerald-300/40 bg-emerald-400/10 text-emerald-100",
      };
    case "error":
      return {
        shell: "border-red-400/60 bg-red-500/10 text-red-100 shadow-[0_0_0_1px_rgba(248,113,113,0.12),0_18px_40px_rgba(185,28,28,0.18)]",
        orb: "border-red-300 bg-red-400 text-slate-950",
        accent: "text-red-200",
        subtitle: "text-red-100/80",
        badge: "border-red-300/40 bg-red-400/10 text-red-100",
      };
    default:
      return {
        shell: "border-slate-800 bg-slate-950/75 text-slate-200",
        orb: "border-slate-700 bg-slate-900 text-slate-300",
        accent: "text-slate-500",
        subtitle: "text-slate-400",
        badge: "border-slate-700 bg-slate-900/80 text-slate-400",
      };
  }
}

function getStateLabel(state: GraphNodeViewModel["state"]) {
  switch (state) {
    case "active":
      return "Active";
    case "completed":
      return "Complete";
    case "error":
      return "Error";
    default:
      return "Idle";
  }
}

export function GraphNode({ node, className = "" }: GraphNodeProps) {
  const styles = getNodeStyles(node.state);

  return (
    <div className={`min-w-0 w-full max-w-full ${className}`}>
      <div
        className={`h-full min-w-0 rounded-[24px] border px-4 py-4 transition-all duration-300 ${styles.shell}`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div
              className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-full border font-mono text-[12px] uppercase tracking-[0.16em] ${styles.orb}`}
            >
              {String(node.order).padStart(2, "0")}
            </div>
            <div className="min-w-0">
              <p className={`font-mono text-[11px] uppercase tracking-[0.2em] ${styles.accent}`}>
                {node.accent}
              </p>
              <h3 className="mt-1 text-lg font-semibold tracking-tight text-white">{node.label}</h3>
            </div>
          </div>
          <span
            className={`shrink-0 rounded-full border px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.16em] ${styles.badge}`}
          >
            {getStateLabel(node.state)}
          </span>
        </div>

        <div className="mt-5 border-t border-current/10 pt-4">
          <p className={`text-sm leading-6 ${styles.subtitle}`}>{node.subtitle}</p>
        </div>
      </div>
    </div>
  );
}
