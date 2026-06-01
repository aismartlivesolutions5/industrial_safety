import type { TopRiskyAsset } from "@/types/api";
import { AnomalyBadge } from "@/components/common/AnomalyBadge";
import { RiskBadge } from "@/components/common/RiskBadge";
import { Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface Props {
  data?: TopRiskyAsset[];
  isLoading: boolean;
}

export function TopRiskyAssetsTable({ data, isLoading }: Props) {
  const navigate = useNavigate();
  return (
    <div className="glass-card rounded-xl p-6">
      <h3 className="text-sm font-semibold text-foreground mb-4">Top Risky Assets</h3>
      {isLoading ? (
        <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary" /></div>
      ) : (
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border/50">
                <th className="text-left py-2 px-3 text-muted-foreground font-medium">Asset</th>
                <th className="text-left py-2 px-3 text-muted-foreground font-medium">Anomaly</th>
                <th className="text-left py-2 px-3 text-muted-foreground font-medium">Risk</th>
                <th className="text-right py-2 px-3 text-muted-foreground font-medium">Scores</th>
              </tr>
            </thead>
            <tbody>
              {(data || []).map((asset) => (
                <tr
                  key={asset.asset_id}
                  className="border-b border-border/30 hover:bg-secondary/30 cursor-pointer transition-colors"
                  onClick={() => navigate(`/assets/${asset.asset_id}`)}
                >
                  <td className="py-2.5 px-3 font-mono font-semibold text-foreground">{asset.asset_id}</td>
                  <td className="py-2.5 px-3"><AnomalyBadge level={asset.alert_level} /></td>
                  <td className="py-2.5 px-3"><RiskBadge label={asset.risk_label} /></td>
                  <td className="py-2.5 px-3 text-right font-mono text-muted-foreground">
                    {asset.anomaly_score?.toFixed(3)} / {asset.risk_score?.toFixed(3)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {(!data || data.length === 0) && <p className="text-center text-muted-foreground py-6 text-xs">No data available</p>}
        </div>
      )}
    </div>
  );
}
