import { cn } from "@/lib/utils";

interface RiskBadgeProps {
  label: string;
  className?: string;
}

const riskConfig: Record<string, { display: string; className: string }> = {
  low: { display: "Low Risk", className: "badge-risk-low" },
  medium: { display: "Medium Risk", className: "badge-risk-medium" },
  high: { display: "High Risk", className: "badge-risk-high" },
  critical: { display: "Critical Risk", className: "badge-risk-critical" },
};

export function RiskBadge({ label, className }: RiskBadgeProps) {
  const config = riskConfig[label?.toLowerCase()] || riskConfig.low;
  return (
    <span className={cn("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide", config.className, className)}>
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {config.display}
    </span>
  );
}
