"""Canonical API contract models for versioned Flask boundaries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def as_utc_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat()


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaginationQuery(ContractModel):
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class PaginationMeta(ContractModel):
    limit: int
    offset: int = 0
    total: int
    next_offset: int | None = None


class ProvenanceMeta(ContractModel):
    provider: str
    fetched_at: str
    stale: bool
    synthetic: bool
    demo: bool
    quality_status: str


class ApiMeta(ContractModel):
    version: Literal["v1"] = "v1"
    timestamp: str = Field(default_factory=utc_now_iso)
    pagination: PaginationMeta | None = None
    provenance: ProvenanceMeta
    compatibility_alias: str | None = None


class ApiSuccessEnvelope(ContractModel):
    success: Literal[True] = True
    data: Any
    meta: ApiMeta


class ApiErrorEnvelope(ContractModel):
    success: Literal[False] = False
    error: str
    code: str
    meta: ApiMeta


class StockDTO(ContractModel):
    symbol: str
    name: str | None = None
    exchange: str | None = None
    display: str | None = None
    price: float | None = None
    current_price: float | None = None
    change_value: float | None = None
    change_percent: float | None = None
    source_type: str | None = None
    provider: str | None = None
    model_version: str | None = None
    is_synthetic: bool = False
    is_demo: bool = False
    data_quality: str = "unavailable"


class PortfolioPositionDTO(ContractModel):
    symbol: str | None = None
    quantity: float | None = None
    avg_price: float | None = None
    current_price: float | None = None
    market_value: float | None = None


class PortfolioDTO(ContractModel):
    positions: list[PortfolioPositionDTO]
    account_metrics: dict[str, Any]
    data_quality: str


class PredictionDTO(ContractModel):
    symbol: str | None = None
    horizon: str | None = None
    as_of: str | None = None
    signal: str | None = None
    current_price: float | None = None
    target_price: float | None = None
    expected_return: float | None = None
    confidence: float | None = None
    risk: str | None = None
    source_type: str | None = None
    provider: str | None = None
    model_version: str | None = None
    feature_version: str | None = None
    is_synthetic: bool = False
    is_demo: bool = False
    fingerprint: str | None = None
    idempotency_key: str | None = None
    data_quality: str = "unavailable"


class DashboardDTO(ContractModel):
    live_indices: list[dict[str, Any]]
    top_stocks: list[StockDTO]
    positions: list[PortfolioPositionDTO]
    portfolio: PortfolioDTO
    data_quality: str


class NewsArticleDTO(ContractModel):
    title: str | None = None
    summary: str | None = None
    url: str | None = None
    published_at: str | None = None
    source: str | None = None


class NewsDTO(ContractModel):
    articles: list[NewsArticleDTO]
    source: str
    data_quality: str


class ResearchDTO(ContractModel):
    research_reports: list[dict[str, Any]]
    ai_insights: list[dict[str, Any]]
    model_performance: dict[str, Any]
    live_stats: dict[str, Any]
    message: str | None = None
    data_quality: str


class SystemDTO(ContractModel):
    status: str
    version: str | None = None
    ai_features: dict[str, Any]
    models_loaded: list[str]
    data_sources: list[str]
    performance: dict[str, Any]
    cache_status: dict[str, Any]
    worker_status: dict[str, Any]
    startup_checks: dict[str, Any]


class ContractSchemaDTO(ContractModel):
    envelopes: dict[str, Any]
    dto_schemas: dict[str, Any]


def provenance(
    *,
    provider: str = "local",
    fetched_at: Any = None,
    stale: bool = True,
    synthetic: bool = False,
    demo: bool = False,
    quality_status: str = "unavailable",
) -> ProvenanceMeta:
    return ProvenanceMeta(
        provider=provider,
        fetched_at=as_utc_iso(fetched_at) or utc_now_iso(),
        stale=stale,
        synthetic=synthetic,
        demo=demo,
        quality_status=quality_status,
    )


def model_payload(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json", exclude_none=False)


def success_payload(
    data: BaseModel | dict[str, Any] | list[Any],
    *,
    provenance_meta: ProvenanceMeta,
    pagination: PaginationMeta | None = None,
    compatibility_alias: str | None = None,
) -> dict[str, Any]:
    envelope = ApiSuccessEnvelope(
        data=model_payload(data) if isinstance(data, BaseModel) else data,
        meta=ApiMeta(
            pagination=pagination,
            provenance=provenance_meta,
            compatibility_alias=compatibility_alias,
        ),
    )
    return model_payload(envelope)


def error_payload(
    message: str,
    *,
    code: str,
    provenance_meta: ProvenanceMeta | None = None,
) -> dict[str, Any]:
    envelope = ApiErrorEnvelope(
        error=message,
        code=code,
        meta=ApiMeta(provenance=provenance_meta or provenance()),
    )
    return model_payload(envelope)


def parse_pagination(args: Any, *, default_limit: int = 20) -> PaginationQuery:
    return PaginationQuery(
        limit=args.get("limit", default_limit) or default_limit,
        offset=args.get("offset", 0) or 0,
    )


def paginated_slice(rows: list[Any], query: PaginationQuery) -> tuple[list[Any], PaginationMeta]:
    total = len(rows)
    start = min(query.offset, total)
    stop = min(start + query.limit, total)
    next_offset = stop if stop < total else None
    return rows[start:stop], PaginationMeta(limit=query.limit, offset=query.offset, total=total, next_offset=next_offset)


def contract_schemas() -> ContractSchemaDTO:
    envelope_models = [ApiSuccessEnvelope, ApiErrorEnvelope, ApiMeta, PaginationMeta, ProvenanceMeta]
    dto_models = [
        StockDTO,
        PredictionDTO,
        PortfolioDTO,
        PortfolioPositionDTO,
        DashboardDTO,
        NewsDTO,
        ResearchDTO,
        SystemDTO,
    ]
    return ContractSchemaDTO(
        envelopes={model.__name__: model.model_json_schema() for model in envelope_models},
        dto_schemas={model.__name__: model.model_json_schema() for model in dto_models},
    )
