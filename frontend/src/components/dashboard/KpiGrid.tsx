import { AlertTriangle, ShieldAlert, Activity, Bell } from "lucide-react";
import { useOverview } from "@/hooks/useApi";
import { motion } from "framer-motion";

interface KpiCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  variant: "emergency" | "critical" | "nominal" | "default";
  suffix?: string;
}

function KpiCard({ label, value, icon, variant, suffix }: KpiCardProps) {
  const cardClass =
    variant === "emergency"
      ? "glass-card-emergency"
      : variant === "critical"
      ? "glass-card-critical"
      : variant === "nominal"
      ? "glass-card-nominal"
      : "glass-card";

  const valueColor =
    variant === "emergency"
      ? "text-emergency"
      : variant === "critical"
      ? "text-critical"
      : variant === "nominal"
      ? "text-nominal"
      : "text-foreground";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
      className={`${cardClass} p-5`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          {label}
        </span>
        <div className={`${valueColor} opacity-60`}>{icon}</div>
      </div>
      <div className={`text-3xl font-semibold font-mono ${valueColor} tabular-nums`}>
        {value}
        {suffix && <span className="text-lg ml-1">{suffix}</span>}
      </div>
    </motion.div>
  );
}

function KpiCardSkeleton() {
  return (
    <div className="glass-card p-5 animate-pulse">
      <div className="flex items-center justify-between mb-3">
        <div className="h-3 w-20 bg-muted rounded" />
        <div className="h-5 w-5 bg-muted rounded" />
      </div>
      <div className="h-9 w-16 bg-muted rounded" />
    </div>
  );
}

export function KpiGrid() {
  const { data, isLoading, isError, refetch } = useOverview();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <KpiCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="glass-card p-5 text-center">
        <p className="text-muted-foreground text-sm font-mono">
          Error 504: Failed to fetch overview metrics
        </p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-xs text-nominal hover:underline font-mono"
        >
          RETRY CONNECTION
        </button>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard
        label="Emergency"
        value={data.emergency_count}
        icon={<ShieldAlert size={18} strokeWidth={1.5} />}
        variant={data.emergency_count > 0 ? "emergency" : "nominal"}
      />
      <KpiCard
        label="Critical"
        value={data.critical_count}
        icon={<AlertTriangle size={18} strokeWidth={1.5} />}
        variant={data.critical_count > 0 ? "critical" : "nominal"}
      />
      <KpiCard
        label="Anomaly Rate"
        value={data.anomaly_rate_pct.toFixed(1)}
        suffix="%"
        icon={<Activity size={18} strokeWidth={1.5} />}
        variant={data.anomaly_rate_pct > 10 ? "critical" : "nominal"}
      />
      <KpiCard
        label="Recent Alerts"
        value={data.recent_alerts_count}
        icon={<Bell size={18} strokeWidth={1.5} />}
        variant="default"
      />
    </div>
  );
}
