import { useCallback, useEffect, useState } from "react";
import {
  type AlertCondition,
  type AlertRule,
  CONDITION_LABELS,
  createAlertRule,
  deleteAlertRule,
  fetchAlertRules,
  updateAlertRule,
} from "@/lib/alertRules";

type AlertRulesPanelProps = {
  readonly onClose: () => void;
};

const CONDITIONS: readonly AlertCondition[] = ["above", "below", "change_pct"];

export function AlertRulesPanel({ onClose }: AlertRulesPanelProps) {
  const [rules, setRules] = useState<readonly AlertRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [symbol, setSymbol] = useState("");
  const [condition, setCondition] = useState<AlertCondition>("change_pct");
  const [threshold, setThreshold] = useState("5");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      setRules(await fetchAlertRules());
      setError(null);
    } catch {
      setError("알림 규칙을 불러오지 못했습니다.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleCreate = async () => {
    const trimmed = symbol.trim().toUpperCase();
    const num = parseFloat(threshold);
    if (!trimmed || Number.isNaN(num) || num <= 0) {
      setError("종목과 임계값을 올바르게 입력하세요.");
      return;
    }
    try {
      setSaving(true);
      await createAlertRule({ symbol: trimmed, condition, threshold: num });
      setSymbol("");
      setThreshold("5");
      await load();
    } catch {
      setError("규칙 생성에 실패했습니다.");
    } finally {
      setSaving(false);
    }
  };

  const handleToggle = async (rule: AlertRule) => {
    try {
      await updateAlertRule(rule.rule_id, { enabled: !rule.enabled });
      await load();
    } catch {
      setError("변경에 실패했습니다.");
    }
  };

  const handleDelete = async (ruleId: string) => {
    try {
      await deleteAlertRule(ruleId);
      await load();
    } catch {
      setError("삭제에 실패했습니다.");
    }
  };

  return (
    <div
      className="settings-modal-backdrop"
      onKeyDown={(event) => {
        if (event.key === "Escape") onClose();
      }}
    >
      <div className="settings-modal" role="dialog" aria-modal="true" aria-label="가격 알림 설정">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h2 style={{ margin: 0 }}>가격 알림 설정</h2>
          <button type="button" className="hero-action-button" onClick={onClose}>
            닫기
          </button>
        </div>

        {error ? (
          <p role="alert" style={{ color: "var(--color-error, #e53e3e)" }}>
            {error}
          </p>
        ) : null}

        {/* create form */}
        <fieldset style={{ border: "none", padding: 0, margin: "1rem 0" }}>
          <legend style={{ fontWeight: 600, marginBottom: "0.5rem" }}>새 규칙 추가</legend>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "flex-end" }}>
            <label>
              종목
              <input
                type="text"
                value={symbol}
                onChange={(e) => setSymbol(e.target.value)}
                placeholder="AAPL"
                style={{ display: "block", width: "6rem" }}
                aria-label="종목 심볼"
              />
            </label>
            <label>
              조건
              <select
                value={condition}
                onChange={(e) => setCondition(e.target.value as AlertCondition)}
                style={{ display: "block" }}
                aria-label="알림 조건"
              >
                {CONDITIONS.map((c) => (
                  <option key={c} value={c}>
                    {CONDITION_LABELS[c]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              임계값
              <input
                type="number"
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                min="0"
                step="any"
                style={{ display: "block", width: "5rem" }}
                aria-label="임계값"
              />
            </label>
            <button type="button" className="hero-action-button" onClick={() => void handleCreate()} disabled={saving}>
              {saving ? "저장 중…" : "추가"}
            </button>
          </div>
        </fieldset>

        {/* rules list */}
        {loading ? (
          <p>불러오는 중…</p>
        ) : rules.length === 0 ? (
          <p className="subtle">설정된 알림 규칙이 없습니다.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left" }}>종목</th>
                <th style={{ textAlign: "left" }}>조건</th>
                <th style={{ textAlign: "right" }}>임계값</th>
                <th style={{ textAlign: "center" }}>활성</th>
                <th style={{ textAlign: "center" }}>삭제</th>
              </tr>
            </thead>
            <tbody>
              {rules.map((rule) => (
                <tr key={rule.rule_id}>
                  <td>{rule.symbol}</td>
                  <td>{CONDITION_LABELS[rule.condition]}</td>
                  <td style={{ textAlign: "right" }}>
                    {rule.condition === "change_pct" ? `±${rule.threshold}%` : rule.threshold.toLocaleString()}
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={rule.enabled}
                      onChange={() => void handleToggle(rule)}
                      aria-label={`${rule.symbol} 규칙 활성화`}
                    />
                  </td>
                  <td style={{ textAlign: "center" }}>
                    <button
                      type="button"
                      onClick={() => void handleDelete(rule.rule_id)}
                      aria-label={`${rule.symbol} 규칙 삭제`}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--color-error, #e53e3e)" }}
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
