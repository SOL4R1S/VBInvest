import {
  providerSummaryLabel,
  startupStatusLabel,
  type ProviderSummary,
  type StartupRefreshView,
} from "@/lib/startup-status";
import type { LocalizedLabels } from "@/lib/i18n";

type StartupStatusStripProps = {
  readonly startupRefresh: StartupRefreshView;
  readonly providerSummary: ProviderSummary | null;
  readonly labels: LocalizedLabels;
};

export function StartupStatusStrip({ startupRefresh, providerSummary, labels }: StartupStatusStripProps) {
  return (
    <section className={`startup-status-strip ${startupRefresh.status}`} aria-label="startup source status" data-testid="startup-status">
      <strong>{startupStatusLabel(startupRefresh.status, labels.startupStatusLabels)}</strong>
      <span>{labels.startup.queued} {startupRefresh.queued} · {labels.startup.running} {startupRefresh.running} · {labels.startup.success} {startupRefresh.succeeded} · {labels.startup.failed} {startupRefresh.failed}</span>
      <span>{labels.startup.price} {startupRefresh.priceRows} · {labels.startup.indicator} {startupRefresh.indicatorRows}</span>
      <span>{labels.startup.news} {startupRefresh.newsItems} · {labels.startup.disclosure} {startupRefresh.disclosures}</span>
      {startupRefresh.tickerCatalog ? (
        <span>{labels.startup.tickerCatalog} {startupRefresh.tickerCatalog.count}</span>
      ) : null}
      {providerSummary ? <span>{providerSummaryLabel(providerSummary, labels.providerSummaryLabels)}</span> : null}
      {startupRefresh.providerDisabled.length > 0 ? (
        <span>{labels.startup.providerDisabled} {startupRefresh.providerDisabled.length}</span>
      ) : null}
    </section>
  );
}
