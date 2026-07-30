import { isRecord } from "@/lib/guards";
import { apiFetch } from "@/lib/http";
import type { LocalizedLabels } from "@/lib/i18n";

export type TickerSuggestion = {
  readonly symbol: string;
  readonly name: string;
  readonly exchange: string;
  readonly quoteType: string;
};

export type TickerValidationFailure = {
  readonly message: string;
  readonly suggestions: readonly TickerSuggestion[];
};

export function optionalString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

export function parseTickerSuggestion(value: unknown): TickerSuggestion | null {
  if (!isRecord(value)) {
    return null;
  }
  const symbol = optionalString(value["symbol"]);
  if (!symbol) {
    return null;
  }
  const name = optionalString(value["name"]) || optionalString(value["suggestion_label"]) || symbol;
  return {
    symbol,
    name,
    exchange: optionalString(value["exchange"]),
    quoteType: optionalString(value["quote_type"]) || optionalString(value["quoteType"]),
  };
}

export function parseTickerSuggestions(value: unknown): readonly TickerSuggestion[] {
  if (!Array.isArray(value)) {
    return [];
  }
  const suggestions: TickerSuggestion[] = [];
  for (const item of value) {
    const suggestion = parseTickerSuggestion(item);
    if (suggestion !== null) {
      suggestions.push(suggestion);
    }
  }
  return suggestions;
}

export async function tickerValidationFailure(response: Response, labels: LocalizedLabels): Promise<TickerValidationFailure> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof TypeError) {
      return { message: labels.errors.invalidSymbol, suggestions: [] };
    }
    throw error;
  }
  const detail = isRecord(payload) ? payload["detail"] : null;
  if (!isRecord(detail)) {
    return { message: labels.errors.invalidSymbol, suggestions: [] };
  }
  const suggestions = parseTickerSuggestions(detail["suggestions"]);
  if (suggestions.length > 0) {
    return {
      message: labels.errors.symbolSuggestion(suggestions[0].name, suggestions[0].symbol),
      suggestions,
    };
  }
  const suggestion = optionalString(detail["suggestion"]);
  const label = optionalString(detail["suggestion_label"]) || suggestion;
  if (suggestion) {
    return {
      message: labels.errors.symbolSuggestion(label, suggestion),
      suggestions: [{ symbol: suggestion, name: label, exchange: "", quoteType: "" }],
    };
  }
  return { message: labels.errors.invalidSymbol, suggestions: [] };
}

export async function validatedTickerSymbol(response: Response, fallbackSymbol: string): Promise<string> {
  let payload: unknown;
  try {
    payload = await response.json();
  } catch (error) {
    if (error instanceof SyntaxError || error instanceof TypeError) {
      return fallbackSymbol;
    }
    throw error;
  }
  if (!isRecord(payload)) {
    return fallbackSymbol;
  }
  const symbol = optionalString(payload["symbol"]);
  return symbol || fallbackSymbol;
}

export async function tickerSearchSuggestions(query: string, signal: AbortSignal): Promise<readonly TickerSuggestion[]> {
  const response = await apiFetch(`/api/tickers/search?query=${encodeURIComponent(query)}&limit=8`, { signal });
  if (!response.ok) {
    return [];
  }
  const payload: unknown = await response.json();
  if (!isRecord(payload)) {
    return [];
  }
  return parseTickerSuggestions(payload["suggestions"]);
}

export function logStartupWarning(error: unknown, fallback: string): void {
  if (error instanceof Error) {
    console.warn(error.message);
    return;
  }
  console.warn(fallback);
}
