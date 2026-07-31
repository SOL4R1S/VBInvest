"""Community template routes — list, get, create AI prompt templates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from scripts.lib.ai_prompt_templates import SECTOR_TEMPLATES
from scripts.routers.deps import current_user

router = APIRouter()

# Custom templates stored as JSON files in data directory
_CUSTOM_TEMPLATES_DIR = Path.home() / ".vbinvest" / "templates"


class TemplateResponse(BaseModel):
    id: str
    name: str
    version: int
    system_addendum: str
    fallback_scenarios: dict[str, str]
    key_metrics: list[str]
    author: str
    license: str
    source: str = "builtin"  # "builtin" | "custom"


class TemplateCreate(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    name: str = Field(min_length=1, max_length=100)
    version: int = Field(default=1, ge=1)
    system_addendum: str = Field(min_length=1)
    fallback_scenarios: dict[str, str] = Field(default_factory=dict)
    key_metrics: list[str] = Field(default_factory=list)
    author: str = Field(default="user")
    license: str = Field(default="MIT")


def _builtin_to_response(sector_key: str) -> TemplateResponse:
    t = SECTOR_TEMPLATES[sector_key]
    return TemplateResponse(
        id=f"{sector_key}-v1",
        name=f"{sector_key} 섹터 분석",
        version=1,
        system_addendum=t.system_addendum,
        fallback_scenarios={"bull": t.fallback_bull, "base": t.fallback_base, "bear": t.fallback_bear},
        key_metrics=t.key_metrics,
        author="vbinvest",
        license="MIT",
        source="builtin",
    )


@router.get("/api/templates")
def list_templates(user=Depends(current_user)) -> list[TemplateResponse]:
    """List all available templates (builtin + custom)."""
    results: list[TemplateResponse] = [_builtin_to_response(k) for k in SECTOR_TEMPLATES]

    # Load custom templates
    if _CUSTOM_TEMPLATES_DIR.is_dir():
        for f in sorted(_CUSTOM_TEMPLATES_DIR.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                results.append(TemplateResponse(**data, source="custom"))
            except (json.JSONDecodeError, ValueError):
                continue

    return results


@router.get("/api/templates/{template_id}")
def get_template(template_id: str, user=Depends(current_user)) -> TemplateResponse:
    """Get a single template by ID."""
    # Check builtin first
    sector_key = template_id.removesuffix("-v1")
    if sector_key in SECTOR_TEMPLATES:
        return _builtin_to_response(sector_key)

    # Check custom
    custom_path = _CUSTOM_TEMPLATES_DIR / f"{template_id}.json"
    if custom_path.is_file():
        try:
            data = json.loads(custom_path.read_text(encoding="utf-8"))
            return TemplateResponse(**data, source="custom")
        except (json.JSONDecodeError, ValueError) as exc:
            raise HTTPException(status_code=500, detail=f"corrupt template file: {exc}") from exc

    raise HTTPException(status_code=404, detail=f"template '{template_id}' not found")


@router.post("/api/templates", status_code=201)
def create_template(body: TemplateCreate, user=Depends(current_user)) -> TemplateResponse:
    """Create a custom template (stored as local JSON file)."""
    _CUSTOM_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    path = _CUSTOM_TEMPLATES_DIR / f"{body.id}.json"
    if path.exists():
        raise HTTPException(status_code=409, detail=f"template '{body.id}' already exists")

    data: dict[str, Any] = body.model_dump()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return TemplateResponse(**data, source="custom")


@router.delete("/api/templates/{template_id}", status_code=204)
def delete_template(template_id: str, user=Depends(current_user)) -> None:
    """Delete a custom template."""
    custom_path = _CUSTOM_TEMPLATES_DIR / f"{template_id}.json"
    if not custom_path.is_file():
        raise HTTPException(status_code=404, detail=f"custom template '{template_id}' not found")
    custom_path.unlink()
