import { collectionStatusLabel, type CollectionAssetStatus } from "@/lib/startup-status";
import type { LocalizedLabels } from "@/lib/i18n";

type CollectionStatusStripProps = {
  readonly collectionStatus: readonly CollectionAssetStatus[];
  readonly labels: LocalizedLabels;
};

export function CollectionStatusStrip({ collectionStatus, labels }: CollectionStatusStripProps) {
  if (collectionStatus.length === 0) {
    return null;
  }
  return (
    <section className="collection-status-strip" aria-label={labels.startup.collectionAria} data-testid="collection-status">
      {collectionStatus.map((item) => (
        <span key={item.symbol} className={`collection-status-pill ${item.status}`}>
          <strong>{item.symbol}</strong>
          <span>{collectionStatusLabel(item.status, labels.collectionStatusLabels)}</span>
          <span>{labels.startup.latest} {item.latestPriceDate ?? "-"}</span>
          <span>{item.provider ?? labels.startup.noProvider}</span>
          <span>{labels.startup.price} {item.priceRows} / {labels.startup.indicator} {item.indicatorRows}</span>
        </span>
      ))}
    </section>
  );
}
