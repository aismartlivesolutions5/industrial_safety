import { cn } from "@/lib/utils";

interface AnomalyBadgeProps {
  level: string;
  className?: string;
}

const levelConfig: Record<string, { label: string; className: string }> = {
  normal: { label: "Normal", className: "badge-anomaly-normal" },
  watch: { label: "Watch", className: "badge-anomaly-watch" },
  high: { label: "High", className: "badge-anomaly-high" },
  critical: { label: "Critical", className: "badge-anomaly-critical" },
};

export function AnomalyBadge({ level, className }: AnomalyBadgeProps) {
  const config = levelConfig[level?.toLowerCase()] || levelConfig.normal;
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide", config.className, className)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse-glow" />
      {config.label}
    </span>
  );
}
