import type { LiveAlert } from "@/types/api";
import { AnomalyBadge } from "@/components/common/AnomalyBadge";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Loader2, Bell } from "lucide-react";

interface Props {
  data?: LiveAlert[];
  isLoading: boolean;
}

export function LiveAlertsFeed({ data, isLoading }: Props) {
  return (
    <div className="glass-card rounded-xl p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">Live Alerts</h3>
        {data && data.length > 0 && (
          <span className="flex items-center gap-1.5 text-xs font-mono bg-destructive/15 text-destructive px-2 py-1 rounded-md">
            <Bell className="w-3 h-3" />
            {data.length}
          </span>
        )}
      </div>
      {isLoading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
      ) : (
        <div className="space-y-2 max-h-64 overflow-y-auto scrollbar-thin">
          {(data || []).slice(0, 10).map((alert) => (
            <div
              key={alert.alert_id}
              className={`p-3 rounded-lg border transition-colors ${
                alert.risk_label?.toLowerCase() === "critical"
                  ? "border-destructive/40 bg-destructive/5"
                  : "border-border/30 bg-secondary/20"
              }`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-mono font-semibold text-foreground">{alert.asset_id}</span>
                <span className="text-[10px] text-muted-foreground font-mono">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-1.5">
                <AnomalyBadge level={alert.alert_level} />
                <RiskBadge label={alert.risk_label} />
              </div>
              {alert.reason && <p className="text-[11px] text-muted-foreground line-clamp-2">{alert.reason}</p>}
            </div>
          ))}
          {(!data || data.length === 0) && <p className="text-center text-muted-foreground py-6 text-xs">No active alerts</p>}
        </div>
      )}
    </div>
  );
}
