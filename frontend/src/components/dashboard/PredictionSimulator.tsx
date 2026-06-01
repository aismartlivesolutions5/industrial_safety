import { useState } from "react";
import { usePredict } from "@/hooks/useApi";
import { motion, AnimatePresence } from "framer-motion";
import { FlaskConical, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import type { PredictResponse } from "@/types/api";

const SAMPLE_PAYLOAD = {
  cluster_id: "CLUSTER_01",
  plant_id: "PLANT_01",
  asset_id: "ASSET_01",
  asset_type: "Boiler",
  pressure_bar_g: 14.2,
  temp_c: 225.0,
  water_level_pct: 58.0,
  lel_pct: 12.0,
  voc_ppm: 180.0,
  vibration_rms_mm_s: 6.2,
  active_alarm_count: 3,
};

function SensorSnapshotStrip({ snapshot }: { snapshot: Record<string, unknown> }) {
  const keys = ["pressure_bar_g", "temp_c", "water_level_pct", "lel_pct", "voc_ppm", "vibration_rms_mm_s", "active_alarm_count"];
  const labels: Record<string, string> = {
    pressure_bar_g: "Press.",
    temp_c: "Temp",
    water_level_pct: "Water",
    lel_pct: "LEL",
    voc_ppm: "VOC",
    vibration_rms_mm_s: "Vib.",
    active_alarm_count: "Alarms",
  };
  return (
    <div className="flex flex-wrap gap-2 mb-3">
      {keys.map((k) => {
        const v = snapshot[k];
        if (v === undefined || v === null) return null;
        return (
          <div key={k} className="bg-muted/50 rounded px-2 py-1 text-center">
            <p className="text-[8px] uppercase text-muted-foreground">{labels[k] ?? k}</p>
            <p className="text-xs font-mono tabular-nums">{typeof v === "number" ? v.toFixed(1) : String(v)}</p>
          </div>
        );
      })}
    </div>
  );
}

function ResultCard({ result }: { result: PredictResponse }) {
  const riskColor =
    result.risk.risk_label.toLowerCase() === "emergency"
      ? "text-emergency"
      : result.risk.risk_label.toLowerCase() === "critical"
      ? "text-critical"
      : "text-nominal";

  return (
    <motion.div
      layout
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
      className="mt-4 space-y-3"
    >
      {result.sensor_snapshot && <SensorSnapshotStrip snapshot={result.sensor_snapshot} />}

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Risk Label</p>
          <p className={`text-sm font-semibold ${riskColor}`}>{result.risk.risk_label}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Risk Class</p>
          <p className="text-sm font-semibold font-mono text-foreground">{result.risk.risk_class}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Anomaly</p>
          <p className="text-sm font-semibold text-foreground">{result.anomaly.anomaly_label}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Anomaly Score</p>
          <p className="text-sm font-mono tabular-nums text-foreground">{result.anomaly.anomaly_score.toFixed(4)}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Decision Score</p>
          <p className="text-sm font-mono tabular-nums text-foreground">{result.anomaly.decision_score.toFixed(4)}</p>
        </div>
        <div className="bg-muted/50 rounded-lg p-3">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-1">Threshold</p>
          <p className="text-sm font-mono tabular-nums text-foreground">{result.anomaly.threshold.toFixed(4)}</p>
        </div>
      </div>

      {/* Probabilities */}
      <div className="bg-muted/50 rounded-lg p-3">
        <p className="text-[10px] uppercase tracking-wider text-muted-foreground mb-2">Class Probabilities</p>
        <div className="space-y-1.5">
          {Object.entries(result.risk.probabilities).map(([k, v]) => (
            <div key={k} className="space-y-0.5">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-muted-foreground capitalize">{k}</span>
                <span className="tabular-nums">{(v * 100).toFixed(1)}%</span>
              </div>
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    k.toLowerCase() === "emergency" ? "bg-emergency" :
                    k.toLowerCase() === "critical" ? "bg-critical" : "bg-nominal"
                  }`}
                  style={{ width: `${Math.min(v * 100, 100)}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {result.explanations && result.explanations.top_reasons.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Explanation — Top Drivers</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {result.explanations.top_reasons.map((r, i) => (
              <div key={i} className="bg-muted/50 rounded-lg p-3 flex items-center justify-between">
                <div>
                  <p className="text-xs font-mono text-muted-foreground">{r.feature}</p>
                  <p className="text-sm font-mono tabular-nums text-foreground">{String(r.value)}</p>
                </div>
                <span className={`text-sm font-mono tabular-nums font-semibold ${r.impact > 0 ? "text-emergency" : "text-nominal"}`}>
                  {r.impact > 0 ? "+" : ""}{r.impact.toFixed(3)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </motion.div>
  );
}

export function PredictionSimulator() {
  const [isOpen, setIsOpen] = useState(false);
  const [payload, setPayload] = useState(JSON.stringify(SAMPLE_PAYLOAD, null, 2));
  const [result, setResult] = useState<PredictResponse | null>(null);
  const { mutate, isPending, isError } = usePredict();

  const handlePredict = () => {
    try {
      const parsed = JSON.parse(payload);
      mutate(
        { payload: parsed, explain: true },
        { onSuccess: (data) => setResult(data) }
      );
    } catch {
      // invalid JSON
    }
  };

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-foreground/[0.02] transition-colors"
      >
        <div className="flex items-center gap-2">
          <FlaskConical size={16} strokeWidth={1.5} className="text-nominal" />
          <h2 className="text-sm font-semibold uppercase tracking-wider">Prediction Simulator</h2>
        </div>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: "auto" }}
            exit={{ height: 0 }}
            transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-3">
              <textarea
                value={payload}
                onChange={(e) => setPayload(e.target.value)}
                className="w-full h-48 bg-muted/50 rounded-lg p-3 text-xs font-mono text-foreground resize-none focus:outline-none focus:ring-1 focus:ring-nominal/30"
                spellCheck={false}
              />
              <button
                onClick={handlePredict}
                disabled={isPending}
                className="w-full flex items-center justify-center gap-2 bg-nominal/10 hover:bg-nominal/20 text-nominal border border-nominal/20 rounded-lg py-2.5 text-xs font-semibold uppercase tracking-wider transition-colors disabled:opacity-50"
              >
                {isPending ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <FlaskConical size={14} strokeWidth={1.5} />
                )}
                Execute Prediction
              </button>

              {isError && (
                <p className="text-xs font-mono text-emergency">Error 504: Prediction request failed</p>
              )}

              <AnimatePresence>
                {result && <ResultCard result={result} />}
              </AnimatePresence>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
