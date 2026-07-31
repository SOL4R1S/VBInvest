/**
 * ResearchHistoryPanel — shows past research views for a symbol as a timeline list.
 */

import { useCallback, useEffect, useState } from "react";
import { fetchResearchHistory, type ResearchHistoryItem } from "@/lib/researchHistory";
import { normalizeOpinion } from "@/lib/research";

type Props = {
  readonly symbol: string;
};

const OPINION_COLORS: Record<string, string> = {
  매수: "#16a34a",
  아웃퍼폼: "#4d7c0f",
  중립: "#64748b",
  언더퍼폼: "#d97706",
  매도: "#dc2626",
};

export function ResearchHistoryPanel({ symbol }: Props) {
  const [items, setItems] = useState<readonly ResearchHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setItems(await fetchResearchHistory(symbol));
      setError(null);
    } catch {
      setError("리서치 이력을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <p className="subtle">리서치 이력 불러오는 중…</p>;
  if (error) return <p role="alert" style={{ color: "#dc2626" }}>{error}</p>;
  if (items.length === 0) return <p className="subtle">아직 리서치 이력이 없습니다.</p>;

  return (
    <div>
      <h3 style={{ margin: "0 0 0.5rem", fontSize: "0.875rem", fontWeight: 600 }}>리서치 히스토리</h3>
      <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {items.map((item, i) => {
          const opinion = normalizeOpinion(item.opinion);
          const color = OPINION_COLORS[opinion] ?? "#64748b";
          return (
            <li
              key={`${item.report_date ?? i}`}
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: "0.375rem",
                padding: "0.5rem 0.75rem",
                fontSize: "0.8125rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "0.5rem" }}>
                <span
                  style={{
                    fontWeight: 700,
                    color,
                    fontSize: "0.75rem",
                    border: `1px solid ${color}`,
                    borderRadius: "0.25rem",
                    padding: "0.1rem 0.4rem",
                  }}
                >
                  {opinion}
                </span>
                <span style={{ color: "#94a3b8", fontSize: "0.75rem" }}>
                  {item.report_date ?? "날짜 미상"}
                  {item.confidence !== null ? ` · 신뢰도 ${(item.confidence * 100).toFixed(0)}%` : ""}
                </span>
              </div>
              {item.thesis ? (
                <p style={{ margin: "0.375rem 0 0", color: "#475569", lineHeight: 1.5 }}>{item.thesis}</p>
              ) : null}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
