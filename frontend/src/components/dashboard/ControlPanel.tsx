import type { LocalizedLabels } from "@/lib/i18n";
import type { Watchlist } from "@/lib/watchlists";
import type { TickerSuggestion } from "@/lib/ticker-utils";

type ControlPanelProps = {
  readonly labels: LocalizedLabels;
  readonly watchlists: readonly Watchlist[];
  readonly selectedWatchlist: Watchlist["id"] | null;
  readonly watchlistsLoaded: boolean;
  readonly hasWatchlists: boolean;
  readonly newWatchlist: string;
  readonly newSymbol: string;
  readonly watchlistValidationMessage: string;
  readonly symbolValidationMessage: string;
  readonly symbolSuggestions: readonly TickerSuggestion[];
  readonly symbolValidationPending: boolean;
  readonly schedulerSettings: { readonly weeklyPrecomputeEnabled: boolean };
  readonly schedulerLoading: boolean;
  readonly schedulerSaving: boolean;
  readonly schedulerStateError: string | null;
  readonly schedulerText: string;
  readonly onWatchlistSelect: (watchlist: Watchlist) => void;
  readonly onNewWatchlistChange: (value: string) => void;
  readonly onCreateWatchlist: () => void;
  readonly onNewSymbolChange: (value: string) => void;
  readonly onAddSymbol: () => void;
  readonly onAddSymbolValue: (symbol: string) => void;
  readonly onWeeklyPrecomputeToggle: (enabled: boolean) => void;
};

export function ControlPanel({
  labels,
  watchlists,
  selectedWatchlist,
  watchlistsLoaded,
  hasWatchlists,
  newWatchlist,
  newSymbol,
  watchlistValidationMessage,
  symbolValidationMessage,
  symbolSuggestions,
  symbolValidationPending,
  schedulerSettings,
  schedulerLoading,
  schedulerSaving,
  schedulerStateError,
  schedulerText,
  onWatchlistSelect,
  onNewWatchlistChange,
  onCreateWatchlist,
  onNewSymbolChange,
  onAddSymbol,
  onAddSymbolValue,
  onWeeklyPrecomputeToggle,
}: ControlPanelProps) {
  return (
    <section className="control-panel" aria-label="watchlist controls">
      {watchlistsLoaded && hasWatchlists ? (
        <div className="panel-column">
          <h2>{labels.controls.watchlistsHeading}</h2>
          <div className="chips">
            {watchlists.map((watchlist) => (
              <button
                key={watchlist.id}
                type="button"
                className={watchlist.id === selectedWatchlist ? "chip active" : "chip"}
                onClick={() => onWatchlistSelect(watchlist)}
              >
                {watchlist.name}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="panel-column">
        <h2>{labels.controls.addWatchlistHeading}</h2>
        <div className="inline-form">
          <input
            aria-label={labels.controls.newWatchlistLabel}
            value={newWatchlist}
            onChange={(event) => onNewWatchlistChange(event.target.value)}
            placeholder={labels.controls.watchlistNamePlaceholder}
          />
          <button type="button" onClick={onCreateWatchlist} disabled={!watchlistsLoaded}>
            {labels.controls.addWatchlistAction}
          </button>
        </div>
        {watchlistValidationMessage ? <p className="research-status error">{watchlistValidationMessage}</p> : null}
      </div>

      <div className="panel-column">
        <h2>{labels.controls.symbolHeading}</h2>
        <div className="inline-form">
          <input
            aria-label={labels.controls.newSymbolLabel}
            value={newSymbol}
            onChange={(event) => onNewSymbolChange(event.target.value)}
            placeholder={labels.controls.symbolPlaceholder}
          />
          <button
            type="button"
            onClick={onAddSymbol}
            disabled={symbolValidationPending || !watchlistsLoaded}
          >
            {symbolValidationPending ? labels.controls.symbolActionBusy : labels.controls.symbolAction}
          </button>
        </div>
        {symbolValidationMessage ? <p className="research-status error">{symbolValidationMessage}</p> : null}
        {symbolSuggestions.length > 0 ? (
          <div className="ticker-suggestions" aria-label={labels.controls.symbolSuggestionsLabel}>
            {symbolSuggestions.map((suggestion) => (
              <button
                key={suggestion.symbol}
                type="button"
                className="ticker-suggestion"
                onClick={() => onAddSymbolValue(suggestion.symbol)}
                disabled={symbolValidationPending || !watchlistsLoaded}
                aria-label={`${suggestion.symbol} ${suggestion.name} ${suggestion.exchange}`.trim()}
              >
                <span className="ticker-suggestion-symbol">{suggestion.symbol}</span>
                <span className="ticker-suggestion-name">{suggestion.name}</span>
                {suggestion.exchange ? <span className="ticker-suggestion-exchange">{suggestion.exchange}</span> : null}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      <div className="panel-column">
        <h2>{labels.controls.weeklyReportHeading}</h2>
        <div className="inline-form scheduler-toggle-row">
          <span>{labels.controls.weeklyReportCheckbox}</span>
          <input
            aria-label={labels.controls.weeklyReportCheckbox}
            type="checkbox"
            checked={schedulerSettings.weeklyPrecomputeEnabled}
            onChange={(event) => {
              onWeeklyPrecomputeToggle(event.target.checked);
            }}
            disabled={schedulerLoading || schedulerSaving}
          />
        </div>
        <p className="research-status">{labels.controls.weeklyReportDefault}</p>
        <p className="research-status">{labels.controls.weeklyReportManual}</p>
        <p className="research-status">{schedulerText}</p>
        {schedulerStateError ? <p className="research-status error">{schedulerStateError}</p> : null}
      </div>
    </section>
  );
}
