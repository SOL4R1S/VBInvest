"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { APPROVED_OPINIONS } from "@/lib/research";
import { generateResearchReport, ReportGenerationError, type GeneratedResearch } from "@/lib/report-generation";

type ReportGenerationState =
  | { readonly status: "idle"; readonly report: GeneratedResearch | null; readonly message: string | null }
  | { readonly status: "generating"; readonly report: GeneratedResearch | null; readonly message: string }
  | { readonly status: "success"; readonly report: GeneratedResearch; readonly message: string }
  | { readonly status: "error"; readonly report: GeneratedResearch | null; readonly message: string };

type ResearchCardProps = {
  readonly symbol: string;
};

const INITIAL_REPORT_STATE: ReportGenerationState = {
  status: "idle",
  report: null,
  message: null,
};

export function ResearchCard({ symbol }: ResearchCardProps) {
  const [reportState, setReportState] = useState<ReportGenerationState>(INITIAL_REPORT_STATE);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setReportState(INITIAL_REPORT_STATE);
    return () => {
      abortControllerRef.current?.abort();
      abortControllerRef.current = null;
    };
  }, [symbol]);

  async function generateReport() {
    if (reportState.status === "generating") {
      return;
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    setReportState((previous) => ({
      status: "generating",
      report: previous.report,
      message: "실시간 분석 중",
    }));
    try {
      const report = await generateResearchReport(symbol, { signal: abortController.signal });
      setReportState({ status: "success", report, message: "리포트 발행 완료" });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setReportState((previous) => ({ status: "error", report: previous.report, message: "취소됨" }));
        return;
      }
      if (error instanceof ReportGenerationError) {
        setReportState((previous) => ({ status: "error", report: previous.report, message: error.userMessage }));
        return;
      }
      console.warn("report generation failed");
      setReportState((previous) => ({
        status: "error",
        report: previous.report,
        message: "리포트 발행에 실패했습니다. 설정과 백엔드 연결을 확인해주세요.",
      }));
    } finally {
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  }

  function cancelGeneration() {
    if (reportState.status !== "generating") {
      return;
    }
    abortControllerRef.current?.abort();
    setReportState((previous) => ({
      status: "error",
      report: previous.report,
      message: "취소됨",
    }));
  }

  function renderReportLinks(report: GeneratedResearch): ReactNode[] {
    const items: ReactNode[] = [];

    if (report.reportUrl) {
      items.push(
        <a key="report-url" href={report.reportUrl} target="_blank" rel="noreferrer">
          리포트 링크 보기
        </a>,
      );
    }
    if (report.reportPath) {
      items.push(
        <p key="report-path">
          리포트 경로: <span>{report.reportPath}</span>
        </p>,
      );
    }
    if (report.obsidianPath) {
      items.push(
        <p key="obsidian-path">
          Obsidian 경로: <span>{report.obsidianPath}</span>
        </p>,
      );
    }

    return items;
  }

  const isGenerating = reportState.status === "generating";

  return (
    <article className="research-card">
      <h3>리서치 의견</h3>
      {reportState.report ? (
        <div className="generated-report">
          <div className={`badge ${reportState.report.opinion}`}>투자의견 {reportState.report.opinion}</div>
          <p>{reportState.report.thesis}</p>
          <span>근거 {reportState.report.sourcesCount}개</span>
          {renderReportLinks(reportState.report)}
        </div>
      ) : (
        <p>아직 발행된 리서치가 없습니다. 현재는 DB 가격/지표를 기반으로 차트를 확인할 수 있습니다.</p>
      )}
      {reportState.message ? (
        <div className={`research-status ${reportState.status}`} role="status" aria-live="polite">
          {reportState.message}
        </div>
      ) : null}
      <button type="button" onClick={() => void generateReport()} disabled={reportState.status === "generating"}>
        {reportState.status === "generating" ? "실시간 분석 중" : "리포트 발행"}
      </button>
      {isGenerating ? (
        <div className="report-generation-backdrop" data-testid="report-generation-backdrop">
          <div className="report-generation-modal" role="dialog" aria-label="리포트 발행 중">
            <div className="research-status generating" role="status" aria-live="polite">
              실시간 분석 중
            </div>
            <button type="button" onClick={() => void cancelGeneration()}>
              취소
            </button>
          </div>
        </div>
      ) : null}
      <div className="badge-row">
        {APPROVED_OPINIONS.map((opinion) => (
          <span key={opinion} className={`badge ${opinion}`}>
            {opinion}
          </span>
        ))}
      </div>
    </article>
  );
}
