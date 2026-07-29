/**
 * Shared runtime type guards and field extractors.
 *
 * Every API response is parsed through these helpers so that
 * no `as` casts are needed and malformed payloads degrade gracefully.
 */

export type JsonObject = Record<string, unknown>;

export function isRecord(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function stringField(record: JsonObject, key: string): string | null {
  const value = record[key];
  return typeof value === "string" ? value : null;
}

export function nonEmptyStringField(record: JsonObject, key: string): string | null {
  const value = record[key];
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

export function numberField(record: JsonObject, key: string): number | null {
  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function boolField(record: JsonObject, key: string): boolean | null {
  const value = record[key];
  return typeof value === "boolean" ? value : null;
}

export function stringOrEmpty(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function numberValue(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

export function stringOrNull(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

export async function readJsonPayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    if (error instanceof SyntaxError) {
      return null;
    }
    throw error;
  }
}

export function readDetail(payload: unknown): string {
  if (!isRecord(payload) || typeof payload.detail !== "string") {
    return "";
  }
  return payload.detail;
}
