import type { AssetCard } from "@/lib/dashboard-data";
import type { LocalizedLabels } from "@/lib/i18n";
import type { Watchlist } from "@/lib/watchlists";

type SymbolSidebarProps = {
  readonly watchlist: Watchlist | null;
  readonly assetCards: Record<string, AssetCard>;
  readonly currentSymbol: string;
  readonly labels: LocalizedLabels;
  readonly onSelectSymbol: (symbol: string) => void;
  readonly onRemoveSymbol: (symbol: string) => void;
};

export function SymbolSidebar({
  watchlist,
  assetCards,
  currentSymbol,
  labels,
  onSelectSymbol,
  onRemoveSymbol,
}: SymbolSidebarProps) {
  return (
    <aside className="watchlist-card">
      <div className="card-heading">
        <h2>{watchlist?.name}</h2>
        <span>{labels.summary.assetCount(watchlist?.symbols.length ?? 0)}</span>
      </div>
      <div className="symbol-list">
        {(watchlist?.symbols ?? []).map((symbol) => {
          const item = assetCards[symbol];
          return (
            <div
              key={symbol}
              className={symbol === currentSymbol ? "symbol-row active" : "symbol-row"}
            >
              <button type="button" onClick={() => onSelectSymbol(symbol)} data-testid={`symbol-${symbol}`}>
                <strong>{item?.displayNameKo ?? symbol}</strong>
                <span>{symbol}</span>
              </button>
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  onRemoveSymbol(symbol);
                }}
                aria-label={labels.summary.removeSymbol(symbol)}
              >
                {labels.controls.removeAction}
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
