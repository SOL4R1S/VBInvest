"use client";

import { type ReactNode, useEffect, useRef, useState } from "react";
import { APPROVED_OPINIONS } from "@/lib/research";
import { generateResearchReport, ReportGenerationError, type GeneratedResearch } from "@/lib/report-generation";
import type { LocalizedLabels } from "@/lib/i18n";

type ReportGenerationState =
  | { readonly status: "idle"; readonly report: GeneratedResearch | null; readonly message: string | null }
  | { readonly status: "generating"; readonly report: GeneratedResearch | null; readonly message: string }
  | { readonly status: "success"; readonly report: GeneratedResearch; readonly message: string }
  | { readonly status: "error"; readonly report: GeneratedResearch | null; readonly message: string };

type ResearchCardProps = {
  readonly symbol: string;
  readonly labels: LocalizedLabels["report"];
};

const INITIAL_REPORT_STATE: ReportGenerationState = {
  status: "idle",
  report: null,
  message: null,
};

export function ResearchCard({ symbol, labels }: ResearchCardProps) {
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
      message: labels.generating,
    }));
    try {
      const report = await generateResearchReport(symbol, { signal: abortController.signal });
      setReportState({ status: "success", report, message: labels.generated });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        setReportState((previous) => ({ status: "error", report: previous.report, message: labels.canceled }));
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
        message: labels.defaultError,
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
      message: labels.canceled,
    }));
  }

  function renderReportLinks(report: GeneratedResearch): ReactNode[] {
    const items: ReactNode[] = [];

    if (report.reportUrl) {
      items.push(
        <a key="report-url" href={report.reportUrl} target="_blank" rel="noreferrer">
          {labels.reportLink}
        </a>,
      );
    }
    if (report.reportPath) {
      items.push(
        <p key="report-path">
          {labels.reportPath}: <span>{report.reportPath}</span>
        </p>,
      );
    }
    if (report.obsidianPath) {
      items.push(
        <p key="obsidian-path">
          {labels.obsidianPath}: <span>{report.obsidianPath}</span>
        </p>,
      );
    }

    return items;
  }

  const isGenerating = reportState.status === "generating";

  return (
    <article className="research-card">
      <h3>{labels.heading}</h3>
      {reportState.report ? (
        <div className="generated-report">
          <div className={`badge ${reportState.report.opinion}`}>{labels.opinionPrefix} {reportState.report.opinion}</div>
          <p>{reportState.report.thesis}</p>
          <span>
            {labels.sources(reportState.report.sourcesCount)}
          </span>
          {renderReportLinks(reportState.report)}
        </div>
      ) : (
        <p>{labels.noReport}</p>
      )}
      {reportState.message ? (
        <div className={`research-status ${reportState.status}`} role="status" aria-live="polite">
          {reportState.message}
        </div>
      ) : null}
      <button type="button" onClick={() => void generateReport()} disabled={reportState.status === "generating"}>
        {reportState.status === "generating" ? labels.generating : labels.generateAction}
      </button>
      {isGenerating ? (
        <div className="report-generation-backdrop" data-testid="report-generation-backdrop">
          <div className="report-generation-modal" role="dialog" aria-label={labels.modalTitle}>
            <div className="research-status generating" role="status" aria-live="polite">
              {labels.generating}
            </div>
            <button type="button" onClick={() => void cancelGeneration()}>
              {labels.cancelAction}
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
