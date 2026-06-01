import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  fetchDashboardOverview,
  fetchRiskTrend,
  fetchTopRiskyAssets,
  fetchLiveAlerts,
  fetchChatbotSummary,
} from "@/lib/api";
import { AppLayout } from "@/components/layout/AppLayout";
import { KPICards } from "@/components/dashboard/KPICards";
import { RiskTrendChart } from "@/components/dashboard/RiskTrendChart";
import { TopRiskyAssetsTable } from "@/components/dashboard/TopRiskyAssetsTable";
import { LiveAlertsFeed } from "@/components/dashboard/LiveAlertsFeed";
import { ChatbotSummaryCard } from "@/components/dashboard/ChatbotSummaryCard";
import { Loader2 } from "lucide-react";

export default function Dashboard() {
  const overview = useQuery({ queryKey: ["dashboard-overview"], queryFn: fetchDashboardOverview, refetchInterval: 90000, retry: 2, refetchOnWindowFocus: false });
  const riskTrend = useQuery({ queryKey: ["risk-trend"], queryFn: fetchRiskTrend, refetchInterval: 100000, enabled: overview.isSuccess, retry: 1, refetchOnWindowFocus: false });
  const topRisky = useQuery({ queryKey: ["top-risky"], queryFn: fetchTopRiskyAssets, refetchInterval: 110000, enabled: riskTrend.isSuccess, retry: 1, refetchOnWindowFocus: false });
  const alerts = useQuery({ queryKey: ["live-alerts"], queryFn: fetchLiveAlerts, refetchInterval: 120000, enabled: topRisky.isSuccess, retry: 1, refetchOnWindowFocus: false });
  const summary = useQuery({ queryKey: ["chatbot-summary"], queryFn: fetchChatbotSummary, enabled: alerts.isSuccess, retry: 1, refetchOnWindowFocus: false });

  const isLoading = overview.isLoading;
  const hasError = overview.isError && !overview.data;

  return (
    <AppLayout title="Command Center" subtitle="Real-time industrial safety monitoring">
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
        </div>
      ) : hasError ? (
        <div className="flex flex-col items-center justify-center h-64 gap-4">
          <p className="text-destructive font-medium">Failed to connect to upstream API</p>
          <p className="text-muted-foreground text-sm">The backend may be starting up. Please wait a moment and try again.</p>
          <button onClick={() => overview.refetch()} className="px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm hover:opacity-90">
            Retry
          </button>
        </div>
      ) : (
        <div className="space-y-6">
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <KPICards data={overview.data} />
          </motion.div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            <motion.div className="xl:col-span-2" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              <RiskTrendChart data={riskTrend.data} isLoading={riskTrend.isLoading} />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
              <ChatbotSummaryCard data={summary.data} isLoading={summary.isLoading} />
            </motion.div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
              <TopRiskyAssetsTable data={topRisky.data} isLoading={topRisky.isLoading} />
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
              <LiveAlertsFeed data={alerts.data} isLoading={alerts.isLoading} />
            </motion.div>
          </div>

          {overview.data?.last_updated && (
            <p className="text-xs text-muted-foreground font-mono text-right">
              Last updated: {new Date(overview.data.last_updated).toLocaleString()}
            </p>
          )}
        </div>
      )}
    </AppLayout>
  );
}
