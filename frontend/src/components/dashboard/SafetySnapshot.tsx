import { useOverview } from "@/hooks/useApi";
import { motion } from "framer-motion";
import { Shield, Clock } from "lucide-react";
import { format } from "date-fns";

const FEATURE_LABELS: Record<string, string> = {
  pressure_bar_g: "Pressure (bar g)",
  temp_c: "Temperature (°C)",
  water_level_pct: "Water Level (%)",
  lel_pct: "LEL (%)",
  voc_ppm: "VOC (ppm)",
  vibration_rms_mm_s: "Vibration (mm/s)",
  active_alarm_count: "Active Alarms",
};

const FEATURE_KEYS = Object.keys(FEATURE_LABELS);

function RiskBadge({ label }: { label: string }) {
  const lower = label.toLowerCase();
  const cls =
    lower === "emergency"
      ? "bg-emergency/20 text-emergency"
      : lower === "critical"
      ? "bg-critical/20 text-critical"
      : "bg-nominal/20 text-nominal";
  return (
    <span className={`inline-block px-2.5 py-1 rounded-lg text-[10px] font-semibold uppercase tracking-wider ${cls}`}>
      {label}
    </span>
  );
}

export function SafetySnapshot() {
  const { data, isLoading, isError, refetch } = useOverview();
  const snapshot = data?.latest_dashboard_snapshot;

  if (isLoading) {
    return (
      <div className="glass-card p-5 animate-pulse">
        <div className="h-4 w-40 bg-muted rounded mb-4" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-16 bg-muted rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="glass-card p-5 text-center">
        <p className="text-xs font-mono text-muted-foreground">Failed to load safety snapshot</p>
        <button onClick={() => refetch()} className="mt-2 text-xs text-nominal hover:underline font-mono">RETRY</button>
      </div>
    );
  }

  if (!snapshot) {
    return (
      <div className="glass-card p-5 text-center">
        <p className="text-xs font-mono text-muted-foreground">No safety snapshot available</p>
      </div>
    );
  }

  let ts: string | null = null;
  try {
    if (snapshot.timestamp) ts = format(new Date(snapshot.timestamp as string), "HH:mm:ss · MMM dd, yyyy");
  } catch { /* ignore */ }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="glass-card overflow-hidden"
    >
      <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Shield size={16} strokeWidth={1.5} className="text-nominal" />
          <h2 className="text-sm font-semibold uppercase tracking-wider">Current Safety Snapshot</h2>
        </div>
        {snapshot.risk_label && <RiskBadge label={String(snapshot.risk_label)} />}
      </div>

      <div className="px-5 py-4 space-y-4">
        {/* Meta row */}
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs font-mono text-muted-foreground">
          {ts && (
            <span className="flex items-center gap-1">
              <Clock size={10} strokeWidth={1.5} /> {ts}
            </span>
          )}
          {snapshot.cluster_id && <span>Cluster: <span className="text-foreground">{String(snapshot.cluster_id)}</span></span>}
          {snapshot.plant_id && <span>Plant: <span className="text-foreground">{String(snapshot.plant_id)}</span></span>}
          {snapshot.asset_id && <span>Asset: <span className="text-nominal">{String(snapshot.asset_id)}</span></span>}
          {snapshot.asset_type && <span>Type: <span className="text-foreground">{String(snapshot.asset_type)}</span></span>}
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
          {FEATURE_KEYS.map((key) => {
            const val = snapshot[key];
            if (val === undefined || val === null) return null;
            return (
              <div key={key} className="bg-muted/50 rounded-lg p-3 text-center">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">{FEATURE_LABELS[key]}</p>
                <p className="text-lg font-semibold font-mono tabular-nums text-foreground">{typeof val === "number" ? val.toFixed(1) : String(val)}</p>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
