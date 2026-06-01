import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchAssetLatest, fetchAssetTimeseries, fetchExplainability } from "@/lib/api";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnomalyBadge } from "@/components/common/AnomalyBadge";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Loader2, ArrowLeft, Gauge, Thermometer, Wind, Activity, AlertTriangle, Wrench } from "lucide-react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

const sensorFields = [
  { key: "boiler_pressure_bar", label: "Pressure (bar)", icon: Gauge },
  { key: "boiler_temperature_c", label: "Temperature (°C)", icon: Thermometer },
  { key: "voc_ppm", label: "VOC (ppm)", icon: Wind },
  { key: "nh3_ppm", label: "NH₃ (ppm)", icon: Wind },
  { key: "h2s_ppm", label: "H₂S (ppm)", icon: Wind },
  { key: "lel_percent", label: "LEL (%)", icon: AlertTriangle },
  { key: "vibration_rms", label: "Vibration RMS", icon: Activity },
  { key: "active_alarm_count", label: "Active Alarms", icon: AlertTriangle },
  { key: "days_since_last_maintenance", label: "Days Since Maintenance", icon: Wrench },
] as const;

const chartFields = [
  "boiler_pressure_bar", "boiler_temperature_c", "voc_ppm", "nh3_ppm",
  "h2s_ppm", "lel_percent", "vibration_rms", "anomaly_score", "risk_score",
];

export default function AssetDetail() {
  const { assetId } = useParams<{ assetId: string }>();
  const navigate = useNavigate();

  const latest = useQuery({ queryKey: ["asset-latest", assetId], queryFn: () => fetchAssetLatest(assetId!), enabled: !!assetId });
  const timeseries = useQuery({ queryKey: ["asset-ts", assetId], queryFn: () => fetchAssetTimeseries(assetId!), enabled: !!assetId });
  const explain = useQuery({ queryKey: ["explain", assetId], queryFn: () => fetchExplainability(assetId!), enabled: !!assetId });

  const d = latest.data;

  return (
    <AppLayout title={assetId || "Asset Detail"} subtitle="Detailed asset monitoring & explainability">
      <div className="space-y-6">
        <button onClick={() => navigate("/assets")} className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Assets
        </button>

        {latest.isLoading ? (
          <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
        ) : d ? (
          <>
            {/* Header */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-card rounded-xl p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold font-mono text-foreground">{d.asset_id}</h2>
                  <p className="text-xs text-muted-foreground font-mono mt-1">{new Date(d.timestamp).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-center">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Anomaly Status</p>
                    <AnomalyBadge level={d.alert_level} />
                  </div>
                  <div className="text-center">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Risk Status</p>
                    <RiskBadge label={d.risk_label} />
                  </div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-border/30">
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase">Anomaly Score</p>
                  <p className="text-xl font-bold font-mono text-foreground">{d.anomaly_score?.toFixed(4)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase">Risk Score</p>
                  <p className="text-xl font-bold font-mono text-foreground">{d.risk_score?.toFixed(4)}</p>
                </div>
              </div>
            </motion.div>

            {/* Sensors */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <h3 className="text-sm font-semibold text-foreground mb-3">Latest Sensor Readings</h3>
              <div className="grid grid-cols-3 md:grid-cols-5 xl:grid-cols-9 gap-3">
                {sensorFields.map((s) => (
                  <div key={s.key} className="glass-card rounded-lg p-3 text-center">
                    <s.icon className="w-4 h-4 text-primary mx-auto mb-1.5" />
                    <p className="text-lg font-bold font-mono text-foreground">{(d as any)[s.key] != null ? Number((d as any)[s.key]).toFixed(2) : "—"}</p>
                    <p className="text-[9px] text-muted-foreground mt-1 leading-tight">{s.label}</p>
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Charts */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <h3 className="text-sm font-semibold text-foreground mb-3">60-Minute Trends</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {chartFields.map((field) => (
                  <div key={field} className="glass-card rounded-xl p-4">
                    <p className="text-[11px] text-muted-foreground uppercase tracking-wide mb-2">{field.replace(/_/g, " ")}</p>
                    {timeseries.isLoading ? (
                      <div className="h-32 flex items-center justify-center"><Loader2 className="w-4 h-4 animate-spin text-primary" /></div>
                    ) : (
                      <ResponsiveContainer width="100%" height={120}>
                        <LineChart data={timeseries.data || []}>
                          <CartesianGrid strokeDasharray="3 3" stroke="hsl(220, 15%, 15%)" />
                          <XAxis dataKey="timestamp" hide />
                          <YAxis width={40} fontSize={9} stroke="hsl(215, 15%, 35%)" />
                          <Tooltip
                            contentStyle={{ background: "hsl(220, 18%, 12%)", border: "1px solid hsl(220, 15%, 20%)", borderRadius: "6px", fontSize: "11px" }}
                            labelFormatter={(v) => new Date(v).toLocaleTimeString()}
                          />
                          <Line
                            type="monotone"
                            dataKey={field}
                            stroke={field.includes("risk") ? "hsl(38, 92%, 50%)" : field.includes("anomaly") ? "hsl(0, 72%, 51%)" : "hsl(195, 90%, 50%)"}
                            strokeWidth={1.5}
                            dot={false}
                          />
                        </LineChart>
                      </ResponsiveContainer>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>

            {/* Explainability */}
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
              <h3 className="text-sm font-semibold text-foreground mb-3">AI Explainability (SHAP)</h3>
              <div className="glass-card rounded-xl p-6">
                {explain.isLoading ? (
                  <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
                ) : explain.data?.features ? (
                  <div className="space-y-2">
                    {Object.entries(explain.data.features)
                      .sort(([, a], [, b]) => Math.abs(b as number) - Math.abs(a as number))
                      .map(([feature, value]) => {
                        const v = value as number;
                        const maxVal = Math.max(...Object.values(explain.data!.features).map(Math.abs));
                        const pct = maxVal > 0 ? (Math.abs(v) / maxVal) * 100 : 0;
                        return (
                          <div key={feature} className="flex items-center gap-3">
                            <span className="text-xs text-muted-foreground w-48 truncate font-mono">{feature}</span>
                            <div className="flex-1 h-5 bg-secondary/50 rounded overflow-hidden relative">
                              <div
                                className={`h-full rounded ${v >= 0 ? "bg-destructive/60" : "bg-primary/60"}`}
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono w-16 text-right text-muted-foreground">{v.toFixed(4)}</span>
                          </div>
                        );
                      })}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No explainability data available for this asset.</p>
                )}
              </div>
            </motion.div>
          </>
        ) : (
          <p className="text-muted-foreground">Asset not found.</p>
        )}
      </div>
    </AppLayout>
  );
}
