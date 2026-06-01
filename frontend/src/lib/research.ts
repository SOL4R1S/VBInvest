export const APPROVED_OPINIONS = ["매수", "아웃퍼폼", "중립", "언더퍼폼", "매도"] as const;

export type Opinion = (typeof APPROVED_OPINIONS)[number];

export type ResearchBadge = {
  opinion: Opinion;
  thesis: string;
  bull: string;
  base: string;
  bear: string;
};

export const DEFAULT_RESEARCH: ResearchBadge = {
  opinion: "중립",
  thesis: "아직 발행된 리서치가 없습니다.",
  bull: "AI/메모리 수요가 강하면 업사이드가 열립니다.",
  base: "가격과 지표를 기준으로 중립적으로 점검합니다.",
  bear: "수요 둔화와 밸류에이션 부담은 하방 리스크입니다.",
};

export function normalizeOpinion(value: string | undefined | null): Opinion {
  if (value && APPROVED_OPINIONS.includes(value as Opinion)) {
    return value as Opinion;
  }
  return "중립";
}
