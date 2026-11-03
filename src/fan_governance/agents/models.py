"""Synthetic traits carry no claim of real-world measurement."""

from typing import Literal, Self

from pydantic import Field, model_validator

from fan_governance.core.config import Nonnegative, Probability, ValidatedModel


class Supporter(ValidatedModel):
    supporter_id: str = Field(min_length=1)
    wealth: Nonnegative = 0
    contribution: Nonnegative = 0
    loyalty: Probability = 0.5
    knowledge: Probability = 0.5
    membership_age_days: int = Field(default=0, ge=0)
    participation_probability: Probability = 0.6
    is_adversarial: bool = False
    forecast_accuracy: Probability | None = None
    forecast_sample_count: int = Field(default=0, ge=0)
    forecast_correct_count: int = Field(default=0, ge=0)
    forecast_history_source: Literal["synthetic"] = "synthetic"
    preferred_policy: str = "neutral"
    allow_unfunded_contributions: bool = False
    attributes: dict[str, float | str | bool] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data):
        if isinstance(data, dict):
            data = dict(data)
            for alias, canonical in (
                ("fan_id", "supporter_id"),
                ("participation_rate", "participation_probability"),
                ("knowledge_score", "knowledge"),
            ):
                if alias in data:
                    value = data.pop(alias)
                    if canonical in data and data[canonical] != value:
                        raise ValueError(f"Conflicting {alias} and {canonical}")
                    data[canonical] = value
        return data

    @model_validator(mode="after")
    def validate_history_and_finances(self) -> Self:
        if self.forecast_correct_count > self.forecast_sample_count:
            raise ValueError("forecast_correct_count cannot exceed forecast_sample_count")
        if self.contribution > self.wealth and not self.allow_unfunded_contributions:
            raise ValueError("contribution cannot exceed wealth without an explicit override")
        return self

    @property
    def fan_id(self) -> str:
        return self.supporter_id

    @property
    def participation_rate(self) -> float:
        return self.participation_probability

    @property
    def knowledge_score(self) -> float:
        return self.knowledge
