/**
 * PortfolioSummaryCard — aggregate portfolio metrics.
 */

import type { PortfolioSummary } from "@/lib/portfolio";

function formatCurrency(value: number): string {
  return value.toLocaleString("ko-KR", { maximumFractionDigits: 0 });
}

function formatPct(value: number): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

type Props = {
  readonly summary: PortfolioSummary;
};

export function PortfolioSummaryCard({ summary }: Props) {
  const positive = summary.total_return >= 0;
  const colorClass = positive ? "text-positive" : "text-negative";

  return (
    <section className="portfolio-summary" aria-label="포트폴리오 요약">
      <h2>포트폴리오 요약</h2>
      {summary.currency_mixed && (
        <p className="warning-text" role="note">
          ⚠️ 혼합 통화 (KRW/USD) — 합계는 단순 합산입니다.
        </p>
      )}
      <div className="summary-grid">
        <div>
          <b>총 매입가</b>
          <span>{formatCurrency(summary.total_cost)}</span>
        </div>
        <div>
          <b>현재 가치</b>
          <span>{formatCurrency(summary.total_value)}</span>
        </div>
        <div>
          <b>평가 손익</b>
          <span className={colorClass}>{formatCurrency(summary.total_return)}</span>
        </div>
        <div>
          <b>수익률</b>
          <span className={colorClass}>{formatPct(summary.total_return_pct)}</span>
        </div>
        {summary.daily_return_pct !== null && (
          <div>
            <b>일일 수익률</b>
            <span className={summary.daily_return_pct >= 0 ? "text-positive" : "text-negative"}>
              {formatPct(summary.daily_return_pct)}
            </span>
          </div>
        )}
        <div>
          <b>보유 종목</b>
          <span>{summary.holding_count}개</span>
        </div>
      </div>
    </section>
  );
}
