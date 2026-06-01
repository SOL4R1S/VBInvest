import { normalizeOpinion, type Opinion } from "@/lib/research";

export type GeneratedResearch = {
  readonly targetSlug: string | null;
  readonly opinion: Opinion;
  readonly thesis: string;
  readonly sourcesCount: number;
};

export class ReportGenerationError extends Error {
  readonly userMessage: string;

  constructor(userMessage: string) {
    super(userMessage);
    this.name = "ReportGenerationError";
    this.userMessage = userMessage;
  }
}

export async function generateResearchReport(symbol: string): Promise<GeneratedResearch> {
  let response: Response;
  try {
    response = await fetch(`/api/backend/research/${encodeURIComponent(symbol)}/generate`, { method: "POST" });
  } catch (error) {
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
    return "로그인이 필요합니다. Google 또는 Kakao 로그인 후 다시 시도해주세요.";
  }
  if (status === 404) {
    return "종목 데이터가 아직 준비되지 않았습니다. 프로그램 시작 갱신 후 다시 시도해주세요.";
  }
  if (status === 503 && detail.includes("AI provider API key")) {
    return "AI API 설정이 필요합니다. 설정에서 provider 키 또는 로컬 모델을 확인해주세요.";
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

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
