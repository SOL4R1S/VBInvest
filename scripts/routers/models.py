"""Pydantic request/response models for VBinvest API routers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, StrictBool

from scripts.lib.config import DatabaseMode, ExportMode


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    symbols: list[str] = Field(default_factory=list)


class WatchlistAssetChange(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)


class PortfolioHoldingCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    quantity: float = Field(gt=0)
    average_cost: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class PortfolioHoldingUpdate(BaseModel):
    quantity: float | None = Field(default=None, gt=0)
    average_cost: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class PortfolioTransactionCreate(BaseModel):
    holding_id: str = Field(min_length=1, max_length=64)
    transaction_type: str = Field(pattern=r"^(buy|sell|dividend|split)$")
    quantity: float = Field(gt=0)
    price_per_unit: float = Field(ge=0)
    fee: float = Field(default=0, ge=0)
    transaction_date: str = Field(min_length=10, max_length=10, description="YYYY-MM-DD")
    note: str | None = Field(default=None, max_length=500)


class FirstRunDatabasePayload(BaseModel):
    mode: DatabaseMode = DatabaseMode.SQLITE
    sqlite_path: str | None = Field(default=None, max_length=1000)
    postgres_url: str = Field(default="", max_length=1000)


class FirstRunObsidianPayload(BaseModel):
    vault_path: str = Field(min_length=1, max_length=1000)
    export_mode: ExportMode = ExportMode.DIRECT


class FirstRunProviderPayload(BaseModel):
    opendart_api_key: str = Field(default="", max_length=200)
    ai_mode: str = Field(default="none", max_length=40)
    ai_provider_name: str = Field(default="", max_length=80)
    ai_base_url: str = Field(default="", max_length=500)
    ai_model: str = Field(default="", max_length=160)
    ai_context_size: int = Field(default=8192, ge=1024, le=262144)
    ai_api_key: str = Field(default="", max_length=500)


class FirstRunSetupPayload(BaseModel):
    language: str = Field(default="ko", max_length=10)
    data_directory: str = Field(min_length=1, max_length=1000)
    database: FirstRunDatabasePayload = Field(default_factory=FirstRunDatabasePayload)
    obsidian: FirstRunObsidianPayload
    providers: FirstRunProviderPayload = Field(default_factory=FirstRunProviderPayload)


class LanguageSettingsPayload(BaseModel):
    language: Literal["ko", "en"]


class SchedulerSettingsPayload(BaseModel):
    daily_refresh_enabled: StrictBool | None = None
    weekly_precompute_enabled: StrictBool | None = None
    watchlist: str | None = Field(default=None, max_length=1000)
    include_news: StrictBool | None = None


class ShutdownBeaconPayload(BaseModel):
    token: str = Field(default="", max_length=200)
