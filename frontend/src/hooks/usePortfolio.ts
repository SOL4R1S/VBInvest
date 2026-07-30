/**
 * usePortfolio — portfolio data fetching hook.
 */

import { useCallback, useEffect, useState } from "react";

import {
  fetchHoldings,
  fetchReturns,
  fetchTransactions,
  type PortfolioHolding,
  type PortfolioReturns,
  type PortfolioTransaction,
} from "@/lib/portfolio";

type PortfolioState = {
  holdings: PortfolioHolding[];
  transactions: PortfolioTransaction[];
  returns: PortfolioReturns | null;
  loading: boolean;
  error: string | null;
};

const INITIAL: PortfolioState = {
  holdings: [],
  transactions: [],
  returns: null,
  loading: true,
  error: null,
};

export function usePortfolio() {
  const [state, setState] = useState<PortfolioState>(INITIAL);

  const refresh = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const [holdings, transactions, returns] = await Promise.all([
        fetchHoldings(),
        fetchTransactions(),
        fetchReturns(),
      ]);
      setState({
        holdings: holdings ?? [],
        transactions: transactions ?? [],
        returns,
        loading: false,
        error: null,
      });
    } catch {
      setState((prev) => ({ ...prev, loading: false, error: "포트폴리오 데이터를 불러오지 못했습니다." }));
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { ...state, refresh };
}
