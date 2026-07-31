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

export async function fetchTemplates(): Promise<readonly TemplateItem[]> {
  return (await apiGet("/api/templates", parseTemplates)) ?? [];
}

export async function fetchTemplate(templateId: string): Promise<TemplateItem> {
  const result = await apiGet(`/api/templates/${encodeURIComponent(templateId)}`, parseTemplate);
  if (result === null) throw new Error(`template '${templateId}' not found`);
  return result;
}

export async function createTemplate(payload: TemplateCreatePayload): Promise<TemplateItem> {
  const result = await apiPost("/api/templates", payload, parseTemplate);
  if (result === null) throw new Error("failed to create template");
  return result;
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
