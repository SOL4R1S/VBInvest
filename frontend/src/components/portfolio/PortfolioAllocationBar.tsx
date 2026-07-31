/**
 * PortfolioAllocationBar — horizontal stacked bar showing holding weights.
 * Pure CSS, no chart library needed.
 */

import type { HoldingReturn } from "@/lib/portfolio";

type Props = {
  readonly holdings: readonly HoldingReturn[];
};

const BAR_COLORS = [
  "#2563eb",
  "#16a34a",
  "#d97706",
  "#dc2626",
  "#7c3aed",
  "#0891b2",
  "#be185d",
  "#4d7c0f",
] as const;

export function PortfolioAllocationBar({ holdings }: Props) {
  const withWeight = holdings.filter((h) => h.weight_pct !== null && h.weight_pct > 0);

  if (withWeight.length === 0) {
    return <p className="subtle">자산 배분 정보가 없습니다.</p>;
  }

  return (
    <div>
      <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.875rem", fontWeight: 600 }}>자산 배분</h3>
      <div
        style={{ display: "flex", height: "1.5rem", borderRadius: "0.375rem", overflow: "hidden" }}
        role="img"
        aria-label={`자산 배분: ${withWeight.map((h) => `${h.symbol} ${h.weight_pct?.toFixed(1)}%`).join(", ")}`}
      >
        {withWeight.map((h, i) => (
          <div
            key={h.symbol}
            style={{
              width: `${h.weight_pct}%`,
              backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
              minWidth: h.weight_pct! > 3 ? undefined : "2px",
            }}
            title={`${h.display_name_ko ?? h.symbol} — ${h.weight_pct?.toFixed(1)}%`}
          />
        ))}
      </div>
      <ul style={{ listStyle: "none", padding: 0, margin: "0.5rem 0 0", display: "flex", flexWrap: "wrap", gap: "0.75rem" }}>
        {withWeight.map((h, i) => (
          <li key={h.symbol} style={{ display: "flex", alignItems: "center", gap: "0.25rem", fontSize: "0.75rem" }}>
            <span
              style={{
                display: "inline-block",
                width: "0.625rem",
                height: "0.625rem",
                borderRadius: "2px",
                backgroundColor: BAR_COLORS[i % BAR_COLORS.length],
              }}
            />
            {h.display_name_ko ?? h.symbol} {h.weight_pct?.toFixed(1)}%
          </li>
        ))}
      </ul>
    </div>
  );
}
