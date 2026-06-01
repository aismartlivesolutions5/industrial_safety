import type { DashboardOverview } from "@/types/api";
import {
  Server,
  AlertTriangle,
  Activity,
  TrendingUp,
  Wrench,
  ShieldAlert,
} from "lucide-react";

interface KPICardsProps {
  data?: DashboardOverview;
}

const kpis = [
  { key: "total_assets", label: "Total Assets", icon: Server, format: (v: number) => v },
  { key: "critical_assets", label: "Critical Assets", icon: ShieldAlert, format: (v: number) => v, critical: true },
  { key: "active_anomalies", label: "Active Anomalies", icon: AlertTriangle, format: (v: number) => v, warning: true },
  { key: "avg_anomaly_score", label: "Avg Anomaly Score", icon: Activity, format: (v: number) => v?.toFixed(3) },
  { key: "avg_risk_score", label: "Avg Risk Score", icon: TrendingUp, format: (v: number) => v?.toFixed(3) },
  { key: "maintenance_due_assets", label: "Maintenance Due", icon: Wrench, format: (v: number) => v },
] as const;

export function KPICards({ data }: KPICardsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
      {kpis.map((kpi) => {
        const value = data?.[kpi.key as keyof DashboardOverview];
        const isCritical = "critical" in kpi && kpi.critical && typeof value === "number" && value > 0;
        const isWarning = "warning" in kpi && kpi.warning && typeof value === "number" && value > 0;

        return (
          <div
            key={kpi.key}
            className={`glass-card rounded-xl p-4 transition-all duration-300 ${
              isCritical ? "border-destructive/40 shadow-destructive/10" : isWarning ? "border-warning/40 shadow-warning/10" : ""
            }`}
          >
            <div className="flex items-center gap-2 mb-3">
              <kpi.icon
                className={`w-4 h-4 ${
                  isCritical ? "text-destructive" : isWarning ? "text-warning" : "text-primary"
                }`}
              />
              <span className="text-[11px] text-muted-foreground font-medium uppercase tracking-wide">{kpi.label}</span>
            </div>
            <p
              className={`text-2xl font-bold font-mono ${
                isCritical ? "text-destructive text-glow-destructive" : isWarning ? "text-warning text-glow-warning" : "text-foreground"
              }`}
            >
              {value != null ? kpi.format(value as number) : "—"}
            </p>
          </div>
        );
      })}
    </div>
  );
}
