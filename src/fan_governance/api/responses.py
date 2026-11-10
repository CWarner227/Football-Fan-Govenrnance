"""OpenAPI response contracts for the local research API."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: str
    version: str


class PageResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int
    offset: int = 0
    limit: int = 100


class TableResponse(PageResponse):
    columns: list[str] = Field(default_factory=list)


class ProgressResponse(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    completed_trials: int | None
    total_trials: int
    percentage: float | None = Field(ge=0, le=100)
    estimated_remaining_seconds: float | None = Field(default=None, ge=0)
    phase: Literal["simulating", "finalizing", "completed", "failed", "cancelled"] | None = None


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    name: str
    description: str
    kind: Literal["simulation", "experiment"]
    status: Literal["queued", "running", "completed", "failed", "cancelled"]
    created_at: str
    started_at: str | None
    completed_at: str | None
    elapsed_seconds: float
    configuration: dict[str, Any]
    seed: int
    engine_version: str
    error: str | None
    progress: ProgressResponse


class ConfigurationResponse(BaseModel):
    id: str
    name: str
    description: str
    configuration: dict[str, Any]
    created_at: str


class ValidationResponse(BaseModel):
    valid: bool
    configuration: dict[str, Any]
    workload: dict[str, Any]


class ComparisonResponse(BaseModel):
    runs: list[dict[str, Any]]
    warnings: list[str]
    differences: list[dict[str, Any]]
    paired_differences: list[dict[str, Any]]
