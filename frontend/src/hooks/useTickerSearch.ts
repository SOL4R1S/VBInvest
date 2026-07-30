"use client";

import { useEffect } from "react";
import { tickerSearchSuggestions, type TickerSuggestion } from "@/lib/ticker-utils";
import { logStartupWarning } from "@/lib/ticker-utils";

/**
 * Handles debounced ticker search suggestions as the user types.
 * Extracted from WatchlistDashboard to reduce component complexity.
 */
export function useTickerSearch(
  query: string,
  watchlistsLoaded: boolean,
  setSuggestions: React.Dispatch<React.SetStateAction<readonly TickerSuggestion[]>>,
): void {
  useEffect(() => {
    const trimmed = query.trim();
    if (!trimmed || !watchlistsLoaded) {
      setSuggestions([]);
      return;
    }
    const controller = new AbortController();
    let cancelled = false;
    tickerSearchSuggestions(trimmed, controller.signal)
      .then((suggestions) => {
        if (!cancelled) {
          setSuggestions(suggestions);
        }
      })
      .catch((error) => {
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        logStartupWarning(error, "ticker search failed");
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [query, watchlistsLoaded]);
}
