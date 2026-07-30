/**
 * HoldingsTable — per-holding returns table.
 */

import type { HoldingReturn } from "@/lib/portfolio";

function formatNumber(value: number | null, digits = 2): string {
  if (value === null) return "—";
  return value.toLocaleString("ko-KR", { maximumFractionDigits: digits });
}

function formatPct(value: number | null): string {
  if (value === null) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(2)}%`;
}

type Props = {
  readonly holdings: readonly HoldingReturn[];
};

export function HoldingsTable({ holdings }: Props) {
  if (holdings.length === 0) {
    return <p className="empty-state">보유 종목이 없습니다.</p>;
  }

  return (
    <section aria-label="보유 종목 수익률">
      <h3>보유 종목</h3>
      <table className="holdings-table">
        <thead>
          <tr>
            <th scope="col">종목</th>
            <th scope="col">수량</th>
            <th scope="col">평균단가</th>
            <th scope="col">현재가</th>
            <th scope="col">평가손익</th>
            <th scope="col">수익률</th>
            <th scope="col">비중</th>
          </tr>
        </thead>
        <tbody>
          {holdings.map((h) => {
            const pnlClass =
              h.unrealized_pnl === null ? "" : h.unrealized_pnl >= 0 ? "text-positive" : "text-negative";
            return (
              <tr key={h.symbol}>
                <td>
                  <strong>{h.display_name_ko ?? h.symbol}</strong>
                  <span className="symbol-sub">{h.symbol}</span>
                </td>
                <td>{formatNumber(h.quantity, 0)}</td>
                <td>{formatNumber(h.average_cost)}</td>
                <td>{formatNumber(h.current_price)}</td>
                <td className={pnlClass}>{formatNumber(h.unrealized_pnl)}</td>
                <td className={pnlClass}>{formatPct(h.unrealized_pnl_pct)}</td>
                <td>{formatPct(h.weight_pct)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}
