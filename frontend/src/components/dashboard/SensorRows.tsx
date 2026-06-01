import { useOverview } from "@/hooks/useApi";
import { motion } from "framer-motion";
import { Database, RefreshCw } from "lucide-react";
import { format } from "date-fns";

const FEATURE_KEYS = [
  "pressure_bar_g",
  "temp_c",
  "water_level_pct",
  "lel_pct",
  "voc_ppm",
  "vibration_rms_mm_s",
  "active_alarm_count",
];

const FEATURE_SHORT: Record<string, string> = {
  pressure_bar_g: "Press.",
  temp_c: "Temp",
  water_level_pct: "Water",
  lel_pct: "LEL",
  voc_ppm: "VOC",
  vibration_rms_mm_s: "Vib.",
  active_alarm_count: "Alarms",
};

function RiskBadge({ label }: { label: string }) {
  const lower = label.toLowerCase();
  const cls =
    lower === "emergency"
      ? "bg-emergency/20 text-emergency"
      : lower === "critical"
      ? "bg-critical/20 text-critical"
      : lower === "low" || lower === "nominal" || lower === "normal"
      ? "bg-nominal/20 text-nominal"
      : "bg-muted text-muted-foreground";
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider ${cls}`}>
      {label}
    </span>
  );
}

function formatVal(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toFixed(1);
  return String(v);
}

// Mobile card view
function SensorCard({ row, index }: { row: Record<string, unknown>; index: number }) {
  let ts = "—";
  try { if (row.timestamp) ts = format(new Date(row.timestamp as string), "HH:mm:ss · MMM dd"); } catch { /* */ }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.2 }}
      className="bg-muted/30 rounded-lg p-3 space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-muted-foreground">{ts}</span>
        {row.risk_label && <RiskBadge label={String(row.risk_label)} />}
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs font-mono">
        {row.plant_id && <span className="text-foreground">{String(row.plant_id)}</span>}
        {row.asset_id && <span className="text-nominal">{String(row.asset_id)}</span>}
        {row.asset_type && <span className="text-muted-foreground">{String(row.asset_type)}</span>}
      </div>
      <div className="grid grid-cols-4 gap-2">
        {FEATURE_KEYS.map((k) => (
          <div key={k}>
            <p className="text-[9px] uppercase text-muted-foreground">{FEATURE_SHORT[k]}</p>
            <p className="text-xs font-mono tabular-nums">{formatVal(row[k])}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

export function SensorRows() {
  const { data, isLoading, isError, refetch } = useOverview();
  const rows = data?.latest_dashboard_rows;

  if (isLoading) {
    return (
      <div className="glass-card p-5 animate-pulse">
        <div className="h-4 w-40 bg-muted rounded mb-4" />
        <div className="space-y-2">
          {Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-10 bg-muted rounded" />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="glass-card p-5 text-center">
        <p className="text-xs font-mono text-muted-foreground">Failed to load sensor data</p>
        <button onClick={() => refetch()} className="mt-2 text-xs text-nominal hover:underline font-mono">RETRY</button>
      </div>
    );
  }

  if (!rows || rows.length === 0) {
    return (
      <div className="glass-card p-5 text-center">
        <p className="text-xs font-mono text-muted-foreground">No recent sensor data available</p>
      </div>
    );
  }

  return (
    <div className="glass-card overflow-hidden">
      <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-2">
          <Database size={16} strokeWidth={1.5} className="text-nominal" />
          <h2 className="text-sm font-semibold uppercase tracking-wider">Recent Sensor Rows</h2>
        </div>
        <button onClick={() => refetch()} className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground">
          <RefreshCw size={14} strokeWidth={1.5} />
        </button>
      </div>

      {/* Desktop table */}
      <div className="hidden md:block max-h-[400px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-xs text-muted-foreground uppercase tracking-wider">
              <th className="text-left py-2 px-4 font-medium">Timestamp</th>
              <th className="text-left py-2 px-4 font-medium">Plant</th>
              <th className="text-left py-2 px-4 font-medium">Asset</th>
              <th className="text-left py-2 px-4 font-medium">Type</th>
              <th className="text-left py-2 px-4 font-medium">Risk</th>
              {FEATURE_KEYS.map((k) => (
                <th key={k} className="text-right py-2 px-3 font-medium">{FEATURE_SHORT[k]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => {
              let ts = "—";
              try { if (row.timestamp) ts = format(new Date(row.timestamp as string), "HH:mm:ss · MMM dd"); } catch { /* */ }
              return (
                <motion.tr
                  key={i}
                  initial={{ opacity: 0, y: -8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.02, duration: 0.2 }}
                  className="border-b border-border/50 hover:bg-foreground/[0.03] transition-colors"
                >
                  <td className="py-2.5 px-4 text-xs font-mono text-muted-foreground whitespace-nowrap">{ts}</td>
                  <td className="py-2.5 px-4 text-xs font-mono text-foreground">{String(row.plant_id ?? "—")}</td>
                  <td className="py-2.5 px-4 text-xs font-mono text-nominal">{String(row.asset_id ?? "—")}</td>
                  <td className="py-2.5 px-4 text-[10px] uppercase text-muted-foreground">{String(row.asset_type ?? "—")}</td>
                  <td className="py-2.5 px-4">{row.risk_label ? <RiskBadge label={String(row.risk_label)} /> : "—"}</td>
                  {FEATURE_KEYS.map((k) => (
                    <td key={k} className="py-2.5 px-3 text-right text-xs font-mono tabular-nums">{formatVal(row[k])}</td>
                  ))}
                </motion.tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <div className="md:hidden max-h-[400px] overflow-y-auto p-3 space-y-2">
        {rows.map((row, i) => (
          <SensorCard key={i} row={row} index={i} />
        ))}
      </div>
    </div>
  );
}
