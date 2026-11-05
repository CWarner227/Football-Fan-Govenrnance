"""Typed HTTP request envelopes, separate from scientific configuration schemas."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    configuration: dict[str, Any]


class ConfigurationRequest(ValidationRequest):
    name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=10000)


class RunRequest(ConfigurationRequest):
    kind: Literal["simulation", "experiment"] = "simulation"


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_ids: list[str] = Field(min_length=2, max_length=4)
