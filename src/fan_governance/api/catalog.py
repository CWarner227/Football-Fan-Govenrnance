"""Derive browser configuration metadata directly from registered Python factories."""

import inspect
from dataclasses import MISSING, is_dataclass
from dataclasses import fields as dataclass_fields
from typing import Any, get_args, get_type_hints

from pydantic import ConfigDict, Field, create_model

from fan_governance.core.config import ModelSpec
from fan_governance.core.registry import ModelRegistry, default_registry
from fan_governance.economics.config import ShockSpec
from fan_governance.integrations.interfaces import integration_catalog
from fan_governance.scenarios.config import ScenarioConfig
from fan_governance.scenarios.registry import default_scenario_registry


def parameter_model(factory):
    """Use declared validation models, falling back to typed constructor signatures."""
    model = getattr(factory, "parameter_model", None)
    if model is None:
        signature = inspect.signature(factory)
        try:
            hints = get_type_hints(factory.__init__ if inspect.isclass(factory) else factory)
        except (NameError, TypeError):
            hints = {}
        fields = {}
        declared = {f.name: f for f in dataclass_fields(factory)} if is_dataclass(factory) else {}
        for name, parameter in signature.parameters.items():
            if parameter.kind in (parameter.VAR_KEYWORD, parameter.VAR_POSITIONAL):
                continue
            annotation = hints.get(name, parameter.annotation)
            if annotation is inspect.Parameter.empty:
                annotation = Any
            default = parameter.default
            if name in declared and declared[name].default_factory is not MISSING:
                default = Field(default_factory=declared[name].default_factory)
            fields[name] = (annotation, ... if default is inspect.Parameter.empty else default)
        # Hybrid's runtime constructor accepts nested ModelSpec or shorthand names.
        if "default_strategy" in fields and "proposal_rules" in fields:
            fields["default_strategy"] = (str | ModelSpec, "equal")
            fields["proposal_rules"] = (dict[str, str | ModelSpec] | None, None)
        model = create_model("ModelParameters", __config__=ConfigDict(extra="forbid"), **fields)
    return model


def parameter_schema(factory) -> tuple[dict, dict]:
    model = parameter_model(factory)
    schema = model.model_json_schema()
    defaults = {
        name: field.get_default(call_default_factory=True)
        for name, field in model.model_fields.items()
        if not field.is_required()
    }
    # JSON serialization handles nested Pydantic models, dates and tuples consistently.
    from pydantic import TypeAdapter

    defaults = TypeAdapter(dict[str, Any]).dump_python(defaults, mode="json")
    return schema, defaults


def catalog(*, registry: ModelRegistry | None = None) -> dict:
    models = []
    for source in (registry or default_registry(), default_scenario_registry()):
        for category, group in sorted(source.factories().items()):
            for identifier, factory in sorted(group.items()):
                schema, defaults = parameter_schema(factory)
                models.append(
                    {
                        "id": identifier,
                        "name": identifier.replace("_", " ").title(),
                        "category": category,
                        "description": inspect.getdoc(factory) or "",
                        "schema": schema,
                        "defaults": defaults,
                    }
                )
    for identifier in get_args(ShockSpec.model_fields["name"].annotation):
        schema = ShockSpec.model_json_schema()
        schema["properties"]["name"] = {"const": identifier, "type": "string"}
        models.append(
            {
                "id": identifier,
                "name": identifier.replace("_", " ").title(),
                "category": "shock",
                "description": "Monthly economic shock with recovery.",
                "schema": schema,
                "defaults": ShockSpec(name=identifier).model_dump(mode="json"),
            }
        )
    return {"models": models}


def capabilities() -> dict:
    from fan_governance import __version__
    from fan_governance.api.validation import LIMITS

    defaults = ScenarioConfig.model_validate(
        {"simulation": {"population": {"size": 100}}, "experiment": {"trials": 1}}
    )
    return {
        "version": __version__,
        "schema": ScenarioConfig.model_json_schema(),
        "defaults": defaults.model_dump(mode="json"),
        "limits": dict(LIMITS),
        "integrations": integration_catalog(),
    }
