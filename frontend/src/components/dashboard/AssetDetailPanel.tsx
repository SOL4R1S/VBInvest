import { ChartShell } from "@/components/ChartShell";
import { ResearchCard } from "@/components/ResearchCard";
import { ResearchHistoryPanel } from "@/components/ResearchHistoryPanel";
import { formatMa, formatNumber, type AssetCard, type ChartPoint } from "@/lib/dashboard-data";
import type { LocalizedLabels } from "@/lib/i18n";

type AssetDetailPanelProps = {
  readonly asset: AssetCard;
  readonly points: ChartPoint[];
  readonly labels: LocalizedLabels;
};

export function AssetDetailPanel({ asset, points, labels }: AssetDetailPanelProps) {
  return (
    <section className="detail-card">
      <div className="detail-header">
        <div>
          <h2>{asset.displayNameKo}</h2>
          <p>{asset.symbol}</p>
        </div>
        <div className={`badge ${asset.opinion}`}>
          {asset.opinion}
        </div>
      </div>

      <div className="summary-grid">
        <div><b>{labels.summary.price}</b><span>{asset.price.toLocaleString()}</span></div>
        <div><b>{labels.summary.oneDay}</b><span>{asset.delta1d}</span></div>
        <div><b>{labels.summary.oneMonth}</b><span>{asset.delta1m}</span></div>
        <div><b>{labels.summary.rsi14}</b><span>{formatNumber(asset.rsi14)}</span></div>
        <div><b>{labels.summary.ma}</b><span>{formatMa(asset)}</span></div>
      </div>

      <ChartShell symbol={asset.symbol} points={points} labels={labels.chart} />

      <ResearchCard symbol={asset.symbol} labels={labels.report} />

      <ResearchHistoryPanel symbol={asset.symbol} />
    </section>
  );
}
