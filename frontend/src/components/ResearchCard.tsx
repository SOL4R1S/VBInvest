"use client";

import { useEffect, useState } from "react";
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

  useEffect(() => {
    setReportState(INITIAL_REPORT_STATE);
  }, [symbol]);

  async function generateReport() {
    if (reportState.status === "generating") {
      return;
    }
    setReportState((previous) => ({
      status: "generating",
      report: previous.report,
      message: "실시간 분석 중입니다.",
    }));
    try {
      const report = await generateResearchReport(symbol);
      setReportState({ status: "success", report, message: "리포트 발행 완료" });
    } catch (error) {
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
    }
  }

  return (
    <article className="research-card">
      <h3>리서치 의견</h3>
      {reportState.report ? (
        <div className="generated-report">
          <div className={`badge ${reportState.report.opinion}`}>투자의견 {reportState.report.opinion}</div>
          <p>{reportState.report.thesis}</p>
          <span>근거 {reportState.report.sourcesCount}개</span>
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
      <div className="badge-row">
        {APPROVED_OPINIONS.map((opinion) => (
          <span key={opinion} className={`badge ${opinion}`}>{opinion}</span>
        ))}
      </div>
    </article>
  );
}
