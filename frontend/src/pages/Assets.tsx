import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { fetchAssets } from "@/lib/api";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnomalyBadge } from "@/components/common/AnomalyBadge";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Loader2, Search, Filter } from "lucide-react";
import { motion } from "framer-motion";

export default function Assets() {
  const navigate = useNavigate();
  const { data: assets, isLoading } = useQuery({ queryKey: ["assets"], queryFn: fetchAssets });
  const [typeFilter, setTypeFilter] = useState("");
  const [alertFilter, setAlertFilter] = useState("");
  const [riskFilter, setRiskFilter] = useState("");
  const [search, setSearch] = useState("");

  const filtered = (assets || []).filter((a) => {
    if (search && !a.asset_id.toLowerCase().includes(search.toLowerCase())) return false;
    if (typeFilter && a.asset_type !== typeFilter) return false;
    if (alertFilter && a.alert_level !== alertFilter) return false;
    if (riskFilter && a.risk_label !== riskFilter) return false;
    return true;
  });

  const uniqueTypes = [...new Set((assets || []).map((a) => a.asset_type))];
  const uniqueAlerts = [...new Set((assets || []).map((a) => a.alert_level))];
  const uniqueRisks = [...new Set((assets || []).map((a) => a.risk_label))];

  return (
    <AppLayout title="Asset Inventory" subtitle="Monitor all factory assets">
      <div className="space-y-6">
        {/* Filters */}
        <div className="glass-card rounded-xl p-4">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search assets..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-4 py-2 bg-secondary/50 border border-border/50 rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-muted-foreground" />
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="bg-secondary/50 border border-border/50 rounded-lg text-xs px-3 py-2 text-foreground focus:outline-none">
                <option value="">All Types</option>
                {uniqueTypes.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <select value={alertFilter} onChange={(e) => setAlertFilter(e.target.value)} className="bg-secondary/50 border border-border/50 rounded-lg text-xs px-3 py-2 text-foreground focus:outline-none">
                <option value="">All Anomaly</option>
                {uniqueAlerts.map((a) => <option key={a} value={a}>{a}</option>)}
              </select>
              <select value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)} className="bg-secondary/50 border border-border/50 rounded-lg text-xs px-3 py-2 text-foreground focus:outline-none">
                <option value="">All Risk</option>
                {uniqueRisks.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary" /></div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="glass-card rounded-xl overflow-hidden">
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border/50 bg-secondary/30">
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Asset ID</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Type</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Anomaly Status</th>
                    <th className="text-left py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Risk Status</th>
                    <th className="text-right py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Anomaly Score</th>
                    <th className="text-right py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Risk Score</th>
                    <th className="text-right py-3 px-4 text-xs text-muted-foreground font-medium uppercase tracking-wider">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((asset, i) => (
                    <tr
                      key={asset.asset_id}
                      className="border-b border-border/20 hover:bg-secondary/20 cursor-pointer transition-colors"
                      onClick={() => navigate(`/assets/${asset.asset_id}`)}
                    >
                      <td className="py-3 px-4 font-mono font-semibold text-foreground">{asset.asset_id}</td>
                      <td className="py-3 px-4 text-muted-foreground">{asset.asset_type}</td>
                      <td className="py-3 px-4"><AnomalyBadge level={asset.alert_level} /></td>
                      <td className="py-3 px-4"><RiskBadge label={asset.risk_label} /></td>
                      <td className="py-3 px-4 text-right font-mono">{asset.anomaly_score?.toFixed(3)}</td>
                      <td className="py-3 px-4 text-right font-mono">{asset.risk_score?.toFixed(3)}</td>
                      <td className="py-3 px-4 text-right text-xs text-muted-foreground font-mono">{new Date(asset.last_updated).toLocaleTimeString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && <p className="text-center text-muted-foreground py-8 text-sm">No assets match your filters</p>}
            </div>
          </motion.div>
        )}
      </div>
    </AppLayout>
  );
}
