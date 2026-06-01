from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from typing import Any

import pandas as pd

BADGE_CLASS = {
    "매수": "buy",
    "아웃퍼폼": "outperform",
    "중립": "neutral",
    "언더퍼폼": "underperform",
    "매도": "sell",
}

DEFAULT_RESEARCH = {
    "opinion": "중립",
    "thesis": "아직 발행된 리서치가 없어 가격·RSI·이동평균 중심으로만 표시합니다.",
    "rationale": ["DB 가격/지표 업데이트는 완료됨", "사용자가 리포트 발행을 요청하면 정성 리서치가 생성됨"],
    "bull": "AI/메모리/장비 사이클이 예상보다 강하면 업사이드가 열립니다.",
    "base": "가격·이동평균·RSI를 기준으로 중립적 점검을 유지합니다.",
    "bear": "수요 둔화, 밸류에이션 부담, 가이던스 하향이 리스크입니다.",
    "risks": ["데이터 지연", "실적/가이던스 변동성", "거시 금리·환율 변수"],
    "triggers": ["실적 발표", "메모리 가격", "AI 서버 수요", "CAPEX 코멘트"],
}


def render_dashboard_html(items: list[dict[str, Any]], *, title: str = "VBinvest Semiconductor Dashboard") -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cards = []
    details = []
    payload = {}
    for item in items:
        asset = item["asset"]
        history: pd.DataFrame = item["history"]
        if history.empty:
            continue
        symbol = asset["symbol"]
        safe_id = safe_symbol_id(symbol)
        display = asset.get("display_name_ko") or symbol
        latest = history.iloc[-1]
        research = merged_research(item)
        opinion = research["opinion"]
        badge = BADGE_CLASS.get(opinion, "neutral")
        cards.append(
            f"""
            <a class="stock-card" href="#detail-{safe_id}">
              <div class="card-title"><strong>{escape(display)}</strong><span>{escape(symbol)}</span></div>
              <div class="price">{latest['close']:.2f}</div>
              <div class="metric">1D {pct(latest.get('return_1d'))} · 1M {pct(latest.get('return_1m'))}</div>
              <div class="metric">RSI {num(latest.get('rsi14'))} · 52W DD {pct(latest.get('drawdown_52w'))}</div>
              <div class="badge {badge}">{escape(opinion)}</div>
            </a>
            """
        )
        records = chart_records(history)
        payload[safe_id] = records
        details.append(render_detail(display, symbol, safe_id, opinion, badge, latest, research))
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{css()}</style>
</head>
<body>
<main id="top" class="page">
  <header>
    <h1>{escape(title)}</h1>
    <p>generated {escape(now)} · DB-backed · self-contained HTML · 리서치/학습용, 투자 조언 아님</p>
  </header>
  <section class="grid">{''.join(cards)}</section>
  {''.join(details)}
</main>
<script>const CHART_DATA = {json.dumps(payload, ensure_ascii=False)};\n{chart_js()}</script>
</body>
</html>"""
    return html


def merged_research(item: dict[str, Any]) -> dict[str, Any]:
    research = dict(DEFAULT_RESEARCH)
    for key in ["opinion", "thesis", "rationale", "bull", "base", "bear", "risks", "triggers", "sources", "research_date"]:
        if item.get(key) is not None:
            research[key] = item[key]
    if research["opinion"] not in BADGE_CLASS:
        research["opinion"] = "중립"
    return research


def render_detail(display: str, symbol: str, safe_id: str, opinion: str, badge: str, latest: Any, research: dict[str, Any]) -> str:
    rationale = bullets(research.get("rationale", []))
    risks = bullets(research.get("risks", []))
    triggers = bullets(research.get("triggers", []))
    return f"""
    <!-- research-detail: {escape(symbol)} start -->
    <section class="detail" id="detail-{safe_id}">
      <a class="back" href="#top">← 메인으로</a>
      <h2>{escape(display)} <small>({escape(symbol)})</small> <span class="badge {badge}">{escape(opinion)}</span></h2>
      <div class="summary-grid">
        <div><b>현재/최근 종가</b><span>{latest['close']:.2f}</span></div>
        <div><b>1개월</b><span>{pct(latest.get('return_1m'))}</span></div>
        <div><b>RSI14</b><span>{num(latest.get('rsi14'))}</span></div>
        <div><b>MA20 / MA50 / MA120</b><span>{num(latest.get('ma20'))} / {num(latest.get('ma50'))} / {num(latest.get('ma120'))}</span></div>
      </div>
      <div class="chart-shell" data-chart="{safe_id}">
        <div class="chart-toolbar">
          <button class="mode active" type="button" data-mode="line">라인</button>
          <button class="mode" type="button" data-mode="candle">캔들</button>
          <button class="reset" type="button">줌 초기화</button>
        </div>
        <svg viewBox="0 0 1200 640" role="img" aria-label="{escape(display)} 가격/RSI 차트">
          <g class="grid"></g>
          <g class="candles"></g>
          <polyline class="line close"></polyline>
          <polyline class="line ma5"></polyline>
          <polyline class="line ma20"></polyline>
          <polyline class="line ma50"></polyline>
          <polyline class="line ma120"></polyline>
          <polyline class="line rsi"></polyline>
          <line class="rsi30" x1="70" y1="560" x2="1130" y2="560"></line>
          <line class="rsi70" x1="70" y1="500" x2="1130" y2="500"></line>
          <line class="crosshair" x1="0" y1="60" x2="0" y2="600"></line>
        </svg>
        <div class="legend">종가 · 5일선 · 20일선 · 50일선 · 120일선 · RSI14 · 라인/캔들 전환 · 휠 줌 · 드래그 팬</div>
      </div>
      <div class="research">
        <h3>리서치 의견</h3>
        <p>{escape(str(research.get('thesis') or ''))}</p>
        <div class="columns">
          <div><h4>근거</h4>{rationale}</div>
          <div><h4>리스크</h4>{risks}</div>
          <div><h4>확인 트리거</h4>{triggers}</div>
        </div>
        <div class="scenario"><b>Bull</b><p>{escape(str(research.get('bull') or ''))}</p><b>Base</b><p>{escape(str(research.get('base') or ''))}</p><b>Bear</b><p>{escape(str(research.get('bear') or ''))}</p></div>
      </div>
      <p class="disclaimer">본 화면은 리서치/학습용이며 투자 조언이 아닙니다.</p>
    </section>
    <!-- research-detail: {escape(symbol)} end -->
    """


def bullets(values: Any) -> str:
    if isinstance(values, str):
        values = [values]
    values = values or []
    return "<ul>" + "".join(f"<li>{escape(str(v))}</li>" for v in values[:6]) + "</ul>"


def chart_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    cols = ["date", "open", "high", "low", "close", "ma5", "ma20", "ma50", "ma120", "rsi14"]
    recent = frame.tail(260)
    rows = []
    for record in recent[cols].to_dict("records"):
        rows.append({k: clean(v) for k, v in record.items()})
    return rows


def clean(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        return round(value, 6)
    return value


def safe_symbol_id(symbol: str) -> str:
    return symbol.replace(".", "-").replace("^", "-")


def pct(value: Any) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value) * 100:+.2f}%"


def num(value: Any) -> str:
    if pd.isna(value):
        return "n/a"
    return f"{float(value):.1f}"


def css() -> str:
    return """
    :root { color-scheme: dark; background: #08111f; color: #e5eefc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    body { margin: 0; background: radial-gradient(circle at top, #13233d, #08111f 55%); }
    .page { max-width: 1800px; width: min(1800px, calc(100vw - 48px)); margin: 0 auto; padding: 28px 0 80px; }
    header { margin-bottom: 24px; } h1 { margin: 0 0 8px; font-size: 34px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }
    .stock-card { color: inherit; text-decoration: none; border: 1px solid #263a5f; border-radius: 18px; padding: 16px; background: #0d1a2ddd; box-shadow: 0 10px 24px #0005; }
    .card-title { display:flex; justify-content:space-between; gap:12px; align-items:baseline; } .card-title span { color:#94a3b8; white-space:nowrap; }
    .price { font-size: 28px; font-weight: 800; margin: 12px 0 6px; } .metric { color:#b6c2d6; font-size:13px; }
    .badge { display:inline-block; margin-top:10px; padding:7px 11px; border-radius:999px; color:white; font-weight:900; border:1px solid #ffffff99; text-shadow:0 1px 2px #000; box-shadow:0 0 0 2px #0004; }
    .buy { background:#047857; } .outperform { background:#0369a1; } .neutral { background:#475569; } .underperform { background:#b45309; } .sell { background:#be123c; }
    .detail { margin-top: 36px; border: 1px solid #243756; border-radius: 22px; padding: 22px; background: #0b1628e8; }
    .back { color:#93c5fd; } h2 small { color:#94a3b8; }
    .summary-grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:12px; margin:16px 0; }
    .summary-grid div { background:#0f1f37; border:1px solid #243756; border-radius:14px; padding:12px; } .summary-grid b, .summary-grid span { display:block; }
    .chart-shell { position:relative; margin-top:16px; cursor:grab; } .chart-shell.dragging { cursor:grabbing; }
    .chart-toolbar { position:absolute; right:14px; top:14px; z-index:2; display:flex; gap:8px; }
    button { border:1px solid #36527c; border-radius:10px; background:#0f243f; color:#e5eefc; padding:8px 12px; } button.active { background:#2563eb; }
    svg { width:100%; height:auto; background:#07101f; border-radius:16px; border:1px solid #1f3354; }
    .line { fill:none; stroke-width:2.2; vector-effect: non-scaling-stroke; } .close { stroke:#f8fafc; stroke-width:3; } .ma5{stroke:#22c55e}.ma20{stroke:#38bdf8}.ma50{stroke:#f59e0b}.ma120{stroke:#a78bfa}.rsi{stroke:#fb7185;stroke-width:2}
    .candle-up { stroke:#22c55e; fill:#22c55e99; vector-effect:non-scaling-stroke; } .candle-down { stroke:#ef4444; fill:#ef444499; vector-effect:non-scaling-stroke; }
    .rsi30,.rsi70 { stroke:#64748b; stroke-dasharray:5 5; } .crosshair { display:none; stroke:#e2e8f0; stroke-width:1; opacity:.55; } .legend, .disclaimer { color:#9fb0ca; }
    .columns { display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; } .research li { margin:6px 0; }
    """


def chart_js() -> str:
    return r"""
function windowSlice(data, start, end) { return data.slice(start, end + 1); }
function priceBounds(slice) {
  const vals = [];
  slice.forEach(d => ['open','high','low','close','ma5','ma20','ma50','ma120'].forEach(k => { const v=d[k]; if(v!==null && Number.isFinite(v)) vals.push(v); }));
  const min = Math.min(...vals), max = Math.max(...vals), pad = ((max-min)||1)*0.06; return [min-pad, max+pad];
}
function pointsFor(data, key, start, end, width, top, height, fixedMin=null, fixedMax=null) {
  const slice = windowSlice(data,start,end);
  let min=fixedMin, max=fixedMax;
  if(min===null || max===null){ const vals = slice.map(d => d[key]).filter(v => v !== null && Number.isFinite(v)); if(!vals.length) return ''; min=Math.min(...vals); max=Math.max(...vals); }
  const span = (max - min) || 1;
  return slice.map((d, i) => {
    const v = d[key]; if (v === null || !Number.isFinite(v)) return null;
    const x = 70 + (i / Math.max(1, slice.length - 1)) * width;
    const y = top + height - ((v - min) / span) * height;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).filter(Boolean).join(' ');
}
function setPolyline(svg, klass, points) { svg.querySelector(klass).setAttribute('points', points); }
function shiftWindow(state, delta) {
  const size = state.end - state.start;
  const maxStart = Math.max(0, state.data.length - size - 1);
  state.start = Math.max(0, Math.min(maxStart, state.start + delta));
  state.end = Math.min(state.data.length - 1, state.start + size);
}
function renderCandles(svg, state, bounds) {
  const g = svg.querySelector('.candles'); g.innerHTML='';
  if(state.mode !== 'candle') return;
  const slice = windowSlice(state.data,state.start,state.end); const [min,max]=bounds; const span=(max-min)||1; const w=1060, top=60, h=380;
  const step = w / Math.max(1, slice.length - 1); const bodyW = Math.max(2, Math.min(8, step*0.55));
  slice.forEach((d,i)=>{ if([d.open,d.high,d.low,d.close].some(v=>v===null || !Number.isFinite(v))) return; const x=70+i*step; const y=v=>top+h-((v-min)/span)*h; const up=d.close>=d.open; const cls=up?'candle-up':'candle-down'; const line=document.createElementNS('http://www.w3.org/2000/svg','line'); line.setAttribute('x1',x); line.setAttribute('x2',x); line.setAttribute('y1',y(d.high)); line.setAttribute('y2',y(d.low)); line.setAttribute('class',cls); g.appendChild(line); const rect=document.createElementNS('http://www.w3.org/2000/svg','rect'); rect.setAttribute('x',x-bodyW/2); rect.setAttribute('width',bodyW); rect.setAttribute('y',Math.min(y(d.open),y(d.close))); rect.setAttribute('height',Math.max(1,Math.abs(y(d.open)-y(d.close)))); rect.setAttribute('class',cls); g.appendChild(rect); });
}
function render(shell, state) {
  const svg = shell.querySelector('svg'); const w = 1060, top = 60, h = 380; const bounds = priceBounds(windowSlice(state.data,state.start,state.end));
  setPolyline(svg, '.close', state.mode === 'line' ? pointsFor(state.data, 'close', state.start, state.end, w, top, h, bounds[0], bounds[1]) : '');
  ['ma5','ma20','ma50','ma120'].forEach(k => setPolyline(svg, '.' + k, pointsFor(state.data, k, state.start, state.end, w, top, h, bounds[0], bounds[1])));
  setPolyline(svg, '.rsi', pointsFor(state.data, 'rsi14', state.start, state.end, w, 470, 120, 0, 100));
  renderCandles(svg,state,bounds);
}
document.querySelectorAll('[data-chart]').forEach(shell => {
  const id = shell.dataset.chart; const data = CHART_DATA[id] || [];
  const state = { data, start: 0, end: Math.max(0, data.length - 1), dragging:false, lastX:0, mode:'line' };
  render(shell, state);
  shell.querySelectorAll('.mode').forEach(btn => btn.addEventListener('click', () => { state.mode=btn.dataset.mode; shell.querySelectorAll('.mode').forEach(b=>b.classList.toggle('active', b===btn)); render(shell,state); }));
  shell.querySelector('.reset').addEventListener('click', () => { state.start = 0; state.end = data.length - 1; render(shell, state); });
  shell.addEventListener('dblclick', () => { state.start = 0; state.end = data.length - 1; render(shell, state); });
  shell.addEventListener('wheel', ev => {
    ev.preventDefault(); if (data.length < 5) return;
    const rect = shell.getBoundingClientRect(); const ratio = (ev.clientX - rect.left) / Math.max(1, rect.width);
    const size = state.end - state.start + 1; const next = Math.max(20, Math.min(data.length, Math.round(size * (ev.deltaY > 0 ? 1.18 : 0.82))));
    const center = state.start + Math.round(size * ratio);
    state.start = Math.max(0, Math.min(data.length - next, center - Math.round(next * ratio)));
    state.end = Math.min(data.length - 1, state.start + next - 1); render(shell, state);
  }, { passive:false });
  shell.addEventListener('pointerdown', ev => { state.dragging=true; state.lastX=ev.clientX; shell.classList.add('dragging'); shell.setPointerCapture(ev.pointerId); });
  shell.addEventListener('pointermove', ev => { if(!state.dragging) return; const dx=ev.clientX-state.lastX; if(Math.abs(dx)>8){ shiftWindow(state, dx<0 ? 3 : -3); state.lastX=ev.clientX; render(shell,state); } });
  shell.addEventListener('pointerup', () => { state.dragging=false; shell.classList.remove('dragging'); });
});
"""
