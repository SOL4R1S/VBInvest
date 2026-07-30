/**
 * TransactionForm — record a buy/sell transaction.
 */

import { useState, type FormEvent } from "react";

import { createTransaction, type PortfolioHolding, type TransactionPayload } from "@/lib/portfolio";

type Props = {
  readonly holdings: readonly PortfolioHolding[];
  readonly onCreated: () => void;
};

const TX_TYPES = [
  { value: "buy", label: "매수" },
  { value: "sell", label: "매도" },
  { value: "dividend", label: "배당" },
  { value: "split", label: "분할" },
] as const;

export function TransactionForm({ holdings, onCreated }: Props) {
  const [holdingId, setHoldingId] = useState("");
  const [txType, setTxType] = useState<TransactionPayload["transaction_type"]>("buy");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [fee, setFee] = useState("0");
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const qty = Number(quantity);
    const px = Number(price);
    if (!holdingId || !Number.isFinite(qty) || qty <= 0 || !Number.isFinite(px) || px < 0) {
      setError("종목, 수량, 단가를 올바르게 입력하세요.");
      return;
    }

    setSubmitting(true);
    const result = await createTransaction({
      holding_id: holdingId,
      transaction_type: txType,
      quantity: qty,
      price_per_unit: px,
      fee: Number(fee) || 0,
      transaction_date: date,
      note: note || null,
    });
    setSubmitting(false);

    if (result === null) {
      setError("거래 등록에 실패했습니다.");
      return;
    }
    setQuantity("");
    setPrice("");
    setFee("0");
    setNote("");
    onCreated();
  };

  return (
    <section aria-label="거래 기록">
      <h3>거래 기록</h3>
      <form onSubmit={handleSubmit} className="transaction-form">
        <div className="form-row">
          <label htmlFor="tx-holding">종목</label>
          <select id="tx-holding" value={holdingId} onChange={(e) => setHoldingId(e.target.value)} required>
            <option value="">선택…</option>
            {holdings.map((h) => (
              <option key={h.holding_id} value={h.holding_id}>
                {h.display_name_ko ?? h.symbol} ({h.symbol})
              </option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <label htmlFor="tx-type">유형</label>
          <select
            id="tx-type"
            value={txType}
            onChange={(e) => setTxType(e.target.value as TransactionPayload["transaction_type"])}
          >
            {TX_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>

        <div className="form-row">
          <label htmlFor="tx-qty">수량</label>
          <input id="tx-qty" type="number" min="0" step="any" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
        </div>

        <div className="form-row">
          <label htmlFor="tx-price">단가</label>
          <input id="tx-price" type="number" min="0" step="any" value={price} onChange={(e) => setPrice(e.target.value)} required />
        </div>

        <div className="form-row">
          <label htmlFor="tx-fee">수수료</label>
          <input id="tx-fee" type="number" min="0" step="any" value={fee} onChange={(e) => setFee(e.target.value)} />
        </div>

        <div className="form-row">
          <label htmlFor="tx-date">날짜</label>
          <input id="tx-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} required />
        </div>

        <div className="form-row">
          <label htmlFor="tx-note">메모</label>
          <input id="tx-note" type="text" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>

        {error && (
          <p className="error-text" role="alert">
            {error}
          </p>
        )}

        <button type="submit" disabled={submitting}>
          {submitting ? "등록 중…" : "거래 등록"}
        </button>
      </form>
    </section>
  );
}
