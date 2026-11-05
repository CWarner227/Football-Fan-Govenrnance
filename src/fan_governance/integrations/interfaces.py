"""Descriptive extension contract; no blockchain services are enabled."""

from typing import Protocol


class IntegrationModule(Protocol):
    id: str
    name: str
    enabled: bool
    capabilities: list[str]


def integration_catalog() -> list[dict]:
    return [
        {
            "id": "blockchain",
            "name": "Blockchain governance",
            "enabled": False,
            "capabilities": [],
            "status": "planned",
        }
    ]
