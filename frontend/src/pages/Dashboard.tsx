import { Shield, Activity } from "lucide-react";
import { KpiGrid } from "@/components/dashboard/KpiGrid";
import { SafetySnapshot } from "@/components/dashboard/SafetySnapshot";
import { SensorRows } from "@/components/dashboard/SensorRows";
import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { PredictionSimulator } from "@/components/dashboard/PredictionSimulator";
import { AiCopilot } from "@/components/dashboard/AiCopilot";

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border/50 px-4 lg:px-6 py-3">
        <div className="max-w-[1600px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-nominal/10 flex items-center justify-center">
              <Shield size={16} strokeWidth={1.5} className="text-nominal" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-wide">System Overview: Industrial Plant — Sector 7G</h1>
              <p className="text-[10px] font-mono text-muted-foreground flex items-center gap-1">
                <Activity size={10} strokeWidth={1.5} className="text-nominal" />
                MONITORING ACTIVE · REAL-TIME FEED
              </p>
            </div>
          </div>
          <div className="hidden sm:flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-nominal status-pulse" />
            <span className="text-[10px] font-mono text-muted-foreground uppercase">System Online</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-[1600px] mx-auto p-4 lg:p-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
          {/* Left: KPI + Snapshot + Sensors + Alerts + Prediction */}
          <div className="lg:col-span-2 space-y-4 lg:space-y-6">
            <KpiGrid />
            <SafetySnapshot />
            <SensorRows />
            <AlertsPanel />
            <PredictionSimulator />
          </div>

          {/* Right: AI Copilot */}
          <div className="lg:col-span-1">
            <div className="lg:sticky lg:top-6">
              <AiCopilot />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
