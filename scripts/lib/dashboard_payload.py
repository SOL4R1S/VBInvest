from __future__ import annotations

from typing import Any

import pandas as pd


def serialize_dashboard_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    payload = []
    for item in items:
        history = _serialize_history(item["history"])
        if not history:
            continue
        payload.append(
            {
                "asset": item["asset"],
                "latest": history[-1],
                "history": history,
                "opinion": item.get("opinion", "중립"),
                "thesis": item.get("thesis"),
            }
        )
    return payload


def _serialize_history(frame: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        if row.get("source") == "synthetic" or row.get("provider") == "synthetic":
            continue
        rows.append({key: _json_value(value) for key, value in row.items()})
    return rows


def _json_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value
