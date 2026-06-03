import { normalizeOpinion, type Opinion } from "@/lib/research";

export type GeneratedResearch = {
  readonly targetSlug: string | null;
  readonly opinion: Opinion;
  readonly thesis: string;
  readonly sourcesCount: number;
  readonly runId: string | null;
  readonly reportPath: string | null;
  readonly obsidianPath: string | null;
  readonly reportUrl: string | null;
};

export class ReportGenerationError extends Error {
  readonly userMessage: string;

  constructor(userMessage: string) {
    super(userMessage);
    this.name = "ReportGenerationError";
    this.userMessage = userMessage;
  }
}

export async function generateResearchReport(
  symbol: string,
  options: { readonly signal?: AbortSignal } = {},
): Promise<GeneratedResearch> {
  let response: Response;
  const headers = authHeaders();
  try {
    response = await fetch(`/api/research/${encodeURIComponent(symbol)}/generate`, {
      method: "POST",
      headers,
      signal: options.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw error;
    }
    if (error instanceof Error) {
      throw new ReportGenerationError("백엔드 연결을 확인해주세요. 프로그램이 실행 중인지 점검한 뒤 다시 시도해주세요.");
    }
    throw error;
  }

  const payload = await readJsonPayload(response);
  if (!response.ok) {
    throw new ReportGenerationError(safeReportErrorMessage(response.status, payload));
  }
  const research = parseGeneratedResearch(payload);
  if (research === null) {
    throw new ReportGenerationError("리포트 응답 형식이 올바르지 않습니다. 백엔드 상태를 확인해주세요.");
  }
  return research;
}

function safeReportErrorMessage(status: number, payload: unknown): string {
  const detail = readDetail(payload);
  if (status === 401) {
    return "로컬 세션 확인이 필요합니다. 프로그램을 다시 실행한 뒤 시도해주세요.";
  }
  if (status === 404) {
    return "종목 데이터가 아직 준비되지 않았습니다. 프로그램 시작 갱신 후 다시 시도해주세요.";
  }
  if (status === 503 && detail.includes("AI provider API key")) {
    return "AI API 설정이 필요합니다. 설정에서 provider 키 또는 로컬 모델을 확인해주세요.";
  }
  if (status === 503 && detail.includes("reasoning-only output without JSON content")) {
    return "로컬 AI가 JSON 리포트를 생성하지 못했습니다. Ollama 설정에서 non-reasoning/instruct 모델을 선택하거나 다른 모델로 바꿔주세요.";
  }
  if (status === 503 && detail.includes("AI provider stopped before JSON content was produced")) {
    return "로컬 AI가 리포트 JSON을 완성하기 전에 멈췄습니다. 더 작은 모델을 선택하거나 출력 토큰 제한을 늘려주세요.";
  }
  if (status === 503 && detail.includes("AI provider request timed out")) {
    return "로컬 AI 응답 시간이 초과되었습니다. 모델이 실행 중인지 확인하거나 더 가벼운 모델로 바꿔주세요.";
  }
  return "리포트 발행에 실패했습니다. 설정과 백엔드 연결을 확인해주세요.";
}

function parseGeneratedResearch(payload: unknown): GeneratedResearch | null {
  if (!isRecord(payload)) {
    return null;
  }
  if (typeof payload.thesis !== "string" || payload.thesis.trim() === "") {
    return null;
  }
  return {
    targetSlug: typeof payload.target_slug === "string" ? payload.target_slug : null,
    opinion: normalizeOpinion(typeof payload.opinion === "string" ? payload.opinion : null),
    thesis: payload.thesis,
    sourcesCount: Array.isArray(payload.sources) ? payload.sources.length : 0,
    runId: typeof payload.run_id === "string" ? payload.run_id : null,
    reportPath: stringField(payload, "report_path"),
    obsidianPath: stringField(payload, "obsidian_path"),
    reportUrl: stringField(payload, "report_url"),
  };
}

async function readJsonPayload(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch (error) {
    if (error instanceof SyntaxError) {
      return null;
    }
    throw error;
  }
}

function readDetail(payload: unknown): string {
  if (!isRecord(payload) || typeof payload.detail !== "string") {
    return "";
  }
  return payload.detail;
}

function stringField(record: Record<string, unknown>, key: string): string | null {
  const value = record[key];
  return typeof value === "string" && value.trim() !== "" ? value : null;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function authHeaders(): Record<string, string> {
  const token = localSessionToken();
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

function localSessionToken(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return window.__VBINVEST_LOCAL_SESSION_TOKEN__ ?? "";
}

declare global {
  interface Window {
    __VBINVEST_LOCAL_SESSION_TOKEN__?: string;
  }
}
