"use client";

interface GraphEdgeProps {
  active: boolean;
  direction?: "horizontal" | "vertical";
  className?: string;
}

export function GraphEdge({
  active,
  direction = "horizontal",
  className = "",
}: GraphEdgeProps) {
  const tone = active
    ? "bg-gradient-to-r from-cyan-400/90 via-sky-300/80 to-emerald-300/80 shadow-[0_0_20px_rgba(34,211,238,0.18)]"
    : "bg-slate-800";

  if (direction === "vertical") {
    return <div className={`mx-auto h-8 w-[3px] rounded-full transition-all duration-300 ${tone} ${className}`} />;
  }

  return <div className={`h-[3px] min-w-0 flex-1 rounded-full transition-all duration-300 ${tone} ${className}`} />;
}
