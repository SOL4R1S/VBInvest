import { APPROVED_OPINIONS, normalizeOpinion } from "@/lib/research";

export { APPROVED_OPINIONS, normalizeOpinion };

export function rangeWindow(total: number, desired: number, anchor: number) {
  const size = Math.max(1, Math.min(total, desired));
  const lead = Math.floor(size / 4);
  const maxStart = Math.max(0, total - size);
  const start = Math.max(0, Math.min(maxStart, anchor - lead));
  return { start, end: Math.min(total - 1, start + size - 1) };
}
