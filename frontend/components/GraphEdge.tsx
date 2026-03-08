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
  const tone = active ? "bg-cyan-400/80" : "bg-slate-700";

  if (direction === "vertical") {
    return <div className={`mx-auto h-8 w-[2px] rounded-full transition-colors ${tone} ${className}`} />;
  }

  return <div className={`h-[2px] min-w-0 flex-1 rounded-full transition-colors ${tone} ${className}`} />;
}
