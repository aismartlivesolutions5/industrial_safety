import type { RiskTrendRow } from "@/types/api";
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { Loader2 } from "lucide-react";

interface Props {
  data?: RiskTrendRow[];
  isLoading: boolean;
}

export function RiskTrendChart({ data, isLoading }: Props) {
  return (
    <div className="glass-card rounded-xl p-6 h-full">
      <h3 className="text-sm font-semibold text-foreground mb-4">Plant Risk Trend</h3>
      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-6 h-6 animate-spin text-primary" />
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          <AreaChart data={data || []}>
            <defs>
              <linearGradient id="anomalyGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(195, 90%, 50%)" stopOpacity={0.3} />
                <stop offset="100%" stopColor="hsl(195, 90%, 50%)" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="hsl(38, 92%, 50%)" stopOpacity={0.3} />
                <stop offset="100%" stopColor="hsl(38, 92%, 50%)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 18%)" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(v) => new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              stroke="hsl(215, 15%, 40%)"
              fontSize={10}
            />
            <YAxis stroke="hsl(215, 15%, 40%)" fontSize={10} />
            <Tooltip
              contentStyle={{
                background: "hsl(220, 18%, 12%)",
                border: "1px solid hsl(220, 15%, 20%)",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelFormatter={(v) => new Date(v).toLocaleString()}
            />
            <Area type="monotone" dataKey="avg_anomaly_score" name="Anomaly Score" stroke="hsl(195, 90%, 50%)" fill="url(#anomalyGrad)" strokeWidth={2} />
            <Area type="monotone" dataKey="avg_risk_score" name="Risk Score" stroke="hsl(38, 92%, 50%)" fill="url(#riskGrad)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
