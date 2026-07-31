/**
 * Template API client — types + fetch helpers for AI prompt templates.
 */

import { apiGet, apiPost } from "@/lib/http";

// -- types ----------------------------------------------------------------

export interface TemplateItem {
  readonly id: string;
  readonly name: string;
  readonly version: number;
  readonly system_addendum: string;
  readonly fallback_scenarios: Record<string, string>;
  readonly key_metrics: readonly string[];
  readonly author: string;
  readonly license: string;
  readonly source: "builtin" | "custom";
}

export interface TemplateCreatePayload {
  readonly id: string;
  readonly name: string;
  readonly version?: number;
  readonly system_addendum: string;
  readonly fallback_scenarios?: Record<string, string>;
  readonly key_metrics?: readonly string[];
  readonly author?: string;
  readonly license?: string;
}

// -- API ------------------------------------------------------------------

function parseTemplates(data: unknown): readonly TemplateItem[] {
  if (!Array.isArray(data)) return [];
  return data as TemplateItem[];
}

function parseTemplate(data: unknown): TemplateItem {
  return data as TemplateItem;
}

export function fetchTemplates(): Promise<readonly TemplateItem[]> {
  return apiGet("/api/templates", parseTemplates);
}

export function fetchTemplate(templateId: string): Promise<TemplateItem> {
  return apiGet(`/api/templates/${encodeURIComponent(templateId)}`, parseTemplate);
}

export function createTemplate(payload: TemplateCreatePayload): Promise<TemplateItem> {
  return apiPost("/api/templates", payload, parseTemplate);
}

export async function deleteTemplate(templateId: string): Promise<void> {
  const response = await fetch(`/api/templates/${encodeURIComponent(templateId)}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
  });
  if (!response.ok) {
    throw new Error(`Failed to delete template: ${response.status}`);
  }
}
