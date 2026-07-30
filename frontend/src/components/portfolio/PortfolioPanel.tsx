/**
 * PortfolioPanel — main portfolio container.
 * Composes summary, holdings table, and transaction form.
 */

import { usePortfolio } from "@/hooks/usePortfolio";
import { HoldingsTable } from "@/components/portfolio/HoldingsTable";
import { PortfolioSummaryCard } from "@/components/portfolio/PortfolioSummaryCard";
import { TransactionForm } from "@/components/portfolio/TransactionForm";

export function PortfolioPanel() {
  const { holdings, returns, loading, error, refresh } = usePortfolio();

  if (loading) {
    return <p className="loading-state">포트폴리오 불러오는 중…</p>;
  }

  if (error) {
    return (
      <div className="error-state" role="alert">
        <p>{error}</p>
        <button type="button" onClick={() => void refresh()}>
          다시 시도
        </button>
      </div>
    );
  }

  return (
    <div className="portfolio-panel">
      {returns?.summary && <PortfolioSummaryCard summary={returns.summary} />}
      <HoldingsTable holdings={returns?.holdings ?? []} />
      <TransactionForm holdings={holdings} onCreated={() => void refresh()} />
    </div>
  );
}
