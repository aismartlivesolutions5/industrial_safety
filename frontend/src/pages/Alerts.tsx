import { useQuery } from "@tanstack/react-query";
import { fetchLiveAlerts } from "@/lib/api";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnomalyBadge } from "@/components/common/AnomalyBadge";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Loader2, Bell } from "lucide-react";
import { motion } from "framer-motion";

export default function Alerts() {
  const { data: alerts, isLoading } = useQuery({
    queryKey: ["live-alerts-page"],
    queryFn: fetchLiveAlerts,
    refetchInterval: 60000,
  });

  const unread = (alerts || []).filter((a) => !a.is_acknowledged).length;

  return (
    <AppLayout title="Live Alerts" subtitle="Real-time industrial alert monitoring">
      <div className="space-y-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-4">
          <div className="glass-card rounded-xl px-5 py-3 flex items-center gap-3">
            <Bell className="w-5 h-5 text-destructive" />
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Unread Alerts</p>
              <p className="text-2xl font-bold font-mono text-destructive text-glow-destructive">{unread}</p>
            </div>
          </div>
          <div className="glass-card rounded-xl px-5 py-3">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Total Alerts</p>
            <p className="text-2xl font-bold font-mono text-foreground">{alerts?.length || 0}</p>
          </div>
        </motion.div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 bg-secondary/30">
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Time</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Asset</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Anomaly</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Risk</th>
                    <th className="text-right py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">A-Score</th>
                    <th className="text-right py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">R-Score</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {(alerts || []).map((alert) => (
                    <tr
                      key={alert.alert_id}
                      className={`border-b border-border/20 transition-colors ${
                        alert.risk_label?.toLowerCase() === "critical"
                          ? "bg-destructive/5 hover:bg-destructive/10"
                          : "hover:bg-secondary/20"
                      }`}
                    >
                      <td className="py-3 px-4 text-xs font-mono text-muted-foreground">{new Date(alert.timestamp).toLocaleTimeString()}</td>
                      <td className="py-3 px-4 font-mono font-semibold text-foreground">{alert.asset_id}</td>
                      <td className="py-3 px-4"><AnomalyBadge level={alert.alert_level} /></td>
                      <td className="py-3 px-4"><RiskBadge label={alert.risk_label} /></td>
                      <td className="py-3 px-4 text-right font-mono">{alert.anomaly_score?.toFixed(3)}</td>
                      <td className="py-3 px-4 text-right font-mono">{alert.risk_score?.toFixed(3)}</td>
                      <td className="py-3 px-4 text-xs text-muted-foreground max-w-xs truncate">{alert.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {(!alerts || alerts.length === 0) && <p className="text-center text-muted-foreground py-8 text-sm">No live alerts</p>}
            </div>
          </motion.div>
        )}
      </div>
    </AppLayout>
  );
}
