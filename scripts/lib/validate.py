from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FORBIDDEN = ["긍정 관찰", "분할 관찰", "주의", "회피", "관찰", "보류", "비중확대", "비중축소", "200일선"]
REQUIRED = ["function pointsFor", "function render", "setPolyline", "function shiftWindow", "pointerdown", "addEventListener('wheel'", "줌 초기화"]


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str]


def validate_html(path: str | Path) -> ValidationResult:
    target = Path(path)
    errors: list[str] = []
    if not target.exists():
        return ValidationResult(False, [f"missing: {target}"])
    text = target.read_text(encoding="utf-8")
    if not text.rstrip().endswith("</html>"):
        errors.append("html does not end with </html>")
    for token in REQUIRED:
        if token not in text:
            errors.append(f"missing required token: {token}")
    for token in FORBIDDEN:
        if token in text:
            errors.append(f"forbidden token present: {token}")
    if "applyZoomViewBox" in text:
        errors.append("naive viewBox zoom token present: applyZoomViewBox")
    return ValidationResult(not errors, errors)
