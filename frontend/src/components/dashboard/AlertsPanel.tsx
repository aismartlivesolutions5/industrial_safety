import { useState, useEffect } from "react";
import { useRecentAlerts, useLast24hAlerts } from "@/hooks/useApi";
import { motion, AnimatePresence } from "framer-motion";
import { Clock, RefreshCw } from "lucide-react";
import type { Alert } from "@/types/api";
import { format } from "date-fns";

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

function AlertRow({ alert, index }: { alert: Alert; index: number }) {
  let ts: string;
  try {
    ts = format(new Date(alert.timestamp), "HH:mm:ss · MMM dd");
  } catch {
    ts = alert.timestamp;
  }

  return (
    <motion.tr
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03, duration: 0.2, ease: [0.2, 0, 0, 1] }}
      className="border-b border-border/50 hover:bg-foreground/[0.03] transition-colors"
    >
      <td className="py-3 px-4 text-xs font-mono text-muted-foreground whitespace-nowrap">{ts}</td>
      <td className="py-3 px-4 text-xs font-mono text-foreground">{alert.plant_id ?? "—"}</td>
      <td className="py-3 px-4 text-xs font-mono text-nominal">{alert.asset_id ?? "—"}</td>
      <td className="py-3 px-4"><RiskBadge label={alert.risk_label} /></td>
      <td className="py-3 px-4"><RiskBadge label={alert.anomaly_label} /></td>
      <td className="py-3 px-4 text-right font-mono text-sm tabular-nums">
        {alert.anomaly_score.toFixed(4)}
      </td>
    </motion.tr>
  );
}

export function AlertsPanel() {
  const [mode, setMode] = useState<"recent" | "24h">("recent");
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const recentQuery = useRecentAlerts(60, 20);
  const last24hQuery = useLast24hAlerts(20);

  const query = mode === "recent" ? recentQuery : last24hQuery;
  const { data, isLoading, isError, refetch, dataUpdatedAt } = query;

  useEffect(() => {
    if (dataUpdatedAt) setLastRefresh(new Date(dataUpdatedAt));
  }, [dataUpdatedAt]);

  return (
    <div className="glass-card overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-border/50">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-foreground">
          Alert Feed
        </h2>
        <div className="flex items-center gap-3">
          <div className="flex bg-muted rounded-lg p-0.5">
            <button
              onClick={() => setMode("recent")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "recent" ? "bg-secondary text-foreground" : "text-muted-foreground"
              }`}
            >
              Last 60 Min
            </button>
            <button
              onClick={() => setMode("24h")}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                mode === "24h" ? "bg-secondary text-foreground" : "text-muted-foreground"
              }`}
            >
              Last 24 Hours
            </button>
          </div>
          <button
            onClick={() => refetch()}
            className="p-1.5 rounded-md hover:bg-muted transition-colors text-muted-foreground"
          >
            <RefreshCw size={14} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="max-h-[400px] overflow-y-auto">
        {isLoading ? (
          <div className="p-8 text-center">
            <div className="inline-block w-5 h-5 border-2 border-nominal/30 border-t-nominal rounded-full animate-spin" />
            <p className="mt-2 text-xs font-mono text-muted-foreground">SCANNING...</p>
          </div>
        ) : isError ? (
          <div className="p-8 text-center">
            <p className="text-xs font-mono text-muted-foreground">Error 504: Upstream Connection Timeout</p>
            <button onClick={() => refetch()} className="mt-2 text-xs text-nominal hover:underline font-mono">
              RETRY CONNECTION
            </button>
          </div>
        ) : !data || data.alerts.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-xs font-mono text-muted-foreground">
              No anomalies detected in the last {mode === "recent" ? "60 minutes" : "24 hours"}.
            </p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border/50 text-xs text-muted-foreground uppercase tracking-wider">
                <th className="text-left py-2 px-4 font-medium">Timestamp</th>
                <th className="text-left py-2 px-4 font-medium">Plant</th>
                <th className="text-left py-2 px-4 font-medium">Asset ID</th>
                <th className="text-left py-2 px-4 font-medium">Risk</th>
                <th className="text-left py-2 px-4 font-medium">Anomaly</th>
                <th className="text-right py-2 px-4 font-medium">Score</th>
              </tr>
            </thead>
            <tbody>
              <AnimatePresence>
                {data.alerts.map((alert, i) => (
                  <AlertRow key={`${alert.timestamp}-${i}`} alert={alert} index={i} />
                ))}
              </AnimatePresence>
            </tbody>
          </table>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2 px-5 py-2.5 border-t border-border/50 text-[10px] font-mono text-muted-foreground">
        <Clock size={10} strokeWidth={1.5} />
        <span>Last updated: {format(lastRefresh, "HH:mm:ss")}</span>
        {data && <span className="ml-auto">{data.count} alert{data.count !== 1 ? "s" : ""}</span>}
      </div>
    </div>
  );
}
