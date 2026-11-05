"""Local FastAPI application: transport only, with all science in Python services."""

import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from fan_governance import __version__
from fan_governance.api.catalog import capabilities, catalog
from fan_governance.api.jobs import JobManager
from fan_governance.api.responses import (
    ComparisonResponse,
    ConfigurationResponse,
    HealthResponse,
    PageResponse,
    RunResponse,
    TableResponse,
    ValidationResponse,
)
from fan_governance.api.results import TABLES, ResultsService
from fan_governance.api.scenarios import population_profiles, scenario_catalog
from fan_governance.api.schemas import (
    ComparisonRequest,
    ConfigurationRequest,
    RunRequest,
    ValidationRequest,
)
from fan_governance.api.validation import validate_configuration
from fan_governance.storage.filesystem import FileRepository

PROJECT = Path(__file__).resolve().parents[3]


def create_app(data_dir=None, *, scenarios_dir=None, max_concurrent=1, timeout_seconds=1800):
    root = Path(data_dir or os.environ.get("FAN_GOVERNANCE_DATA", PROJECT / "data" / "dashboard"))
    scenarios = Path(
        scenarios_dir or os.environ.get("FAN_GOVERNANCE_CONFIGS", PROJECT / "configs" / "scenarios")
    )
    repository = FileRepository(root)
    results = ResultsService(repository)

    @asynccontextmanager
    async def lifespan(application):
        application.state.jobs = JobManager(
            repository, max_concurrent=max_concurrent, timeout_seconds=timeout_seconds
        )
        try:
            yield
        finally:
            application.state.jobs.shutdown()

    application = FastAPI(
        title="Fan Governance Research API", version=__version__, lifespan=lifespan
    )
    application.state.repository = repository
    application.state.results = results
    application.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "[::1]", "testserver"]
    )

    @application.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("origin")
            if origin and urlparse(origin).hostname not in (
                "localhost",
                "127.0.0.1",
                "::1",
                "testserver",
            ):
                return JSONResponse(
                    {"detail": "Only trusted local browser origins may modify research data"},
                    status_code=403,
                )
            content_length = request.headers.get("content-length")
            try:
                if content_length and int(content_length) > 2 * 1024 * 1024:
                    return JSONResponse({"detail": "Request exceeds 2 MiB"}, status_code=413)
            except ValueError:
                return JSONResponse({"detail": "Invalid content length"}, status_code=400)
            length = 0
            chunks = []
            async for chunk in request.stream():
                length += len(chunk)
                if length > 2 * 1024 * 1024:
                    return JSONResponse({"detail": "Request exceeds 2 MiB"}, status_code=413)
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @application.exception_handler(ValidationError)
    async def validation_error(request, error):
        return JSONResponse(
            {"detail": error.errors(include_context=False, include_url=False, include_input=False)},
            status_code=422,
        )

    @application.exception_handler(ValueError)
    async def bad_input(request, error):
        return JSONResponse({"detail": str(error)}, status_code=400)

    @application.exception_handler(KeyError)
    async def missing(request, error):
        return JSONResponse(
            {"detail": "Requested record or artifact was not found"}, status_code=404
        )

    @application.exception_handler(RuntimeError)
    async def conflict(request, error):
        return JSONResponse({"detail": str(error)}, status_code=409)

    prefix = "/api/v1"

    @application.get(prefix + "/health", response_model=HealthResponse)
    def health():
        return {"status": "ok", "version": __version__}

    @application.get(prefix + "/capabilities", response_model=dict)
    def get_capabilities():
        response = capabilities()
        response["limits"] = response["limits"] | {
            "max_concurrent_runs": max_concurrent,
            "timeout_seconds": timeout_seconds,
        }
        return response

    @application.get(prefix + "/models", response_model=dict)
    def models():
        return catalog()

    @application.get(prefix + "/scenarios", response_model=PageResponse)
    def get_scenarios():
        items = scenario_catalog(scenarios)
        return {"items": items, "total": len(items), "limit": len(items)}

    @application.get(prefix + "/profiles", response_model=PageResponse)
    def profiles():
        items = population_profiles(PROJECT / "configs" / "profiles")
        return {"items": items, "total": len(items), "limit": len(items)}

    @application.get(prefix + "/scenarios/{identifier}", response_model=dict)
    def get_scenario(identifier: str):
        for item in scenario_catalog(scenarios):
            if item["id"] == identifier:
                return item
        raise HTTPException(404, "Scenario not found")

    @application.post(prefix + "/configurations/validate", response_model=ValidationResponse)
    def validate(body: ValidationRequest):
        config, workload = validate_configuration(body.configuration)
        return {
            "valid": True,
            "configuration": config.model_dump(mode="json"),
            "workload": workload,
        }

    @application.post(
        prefix + "/configurations/save", response_model=ConfigurationResponse, status_code=201
    )
    def save_configuration(body: ConfigurationRequest):
        config, _ = validate_configuration(body.configuration)
        record = {
            "id": uuid4().hex,
            "name": body.name or config.name,
            "description": body.description,
            "created_at": datetime.now(UTC).isoformat(),
            "configuration": config.model_dump(mode="json"),
        }
        repository.save("configurations", record["id"], record)
        return record

    @application.get(prefix + "/configurations", response_model=PageResponse)
    def configurations(
        offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=500), search: str = ""
    ):
        items = repository.list("configurations")
        items = [
            item
            for item in items
            if search.casefold() in (item["name"] + " " + item["description"]).casefold()
        ]
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "offset": offset,
            "limit": limit,
        }

    @application.get(prefix + "/configurations/{identifier}", response_model=ConfigurationResponse)
    def configuration(identifier: str):
        return repository.get("configurations", identifier)

    @application.delete(prefix + "/configurations/{identifier}", status_code=204)
    def delete_configuration(identifier: str):
        repository.get("configurations", identifier)
        repository.delete("configurations", identifier)
        return Response(status_code=204)

    @application.post(prefix + "/runs", response_model=RunResponse, status_code=202)
    def submit(body: RunRequest, request: Request):
        return request.app.state.jobs.submit(
            body.configuration, body.name, body.description, body.kind
        )

    @application.get(prefix + "/runs", response_model=PageResponse)
    def runs(
        request: Request,
        offset: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=500),
        status: str = "",
        kind: str = "",
        search: str = "",
    ):
        items = request.app.state.jobs.list()
        items = [
            r
            for r in items
            if (not status or r["status"] == status)
            and (not kind or r["kind"] == kind)
            and search.casefold() in (r["name"] + " " + r["description"]).casefold()
        ]
        items.sort(key=lambda r: r["created_at"], reverse=True)
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "offset": offset,
            "limit": limit,
        }

    @application.get(prefix + "/overview", response_model=dict)
    def overview(request: Request):
        records = request.app.state.jobs.list()
        completed = [r for r in records if r["status"] == "completed"]
        return {
            "completed_simulations": sum(r["kind"] == "simulation" for r in completed),
            "total_experiments": sum(r["kind"] == "experiment" for r in records),
            "total_runs": len(records),
            "active_runs": sum(r["status"] in ("queued", "running") for r in records),
            "last_execution_seconds": max(completed, key=lambda r: r["completed_at"])[
                "elapsed_seconds"
            ]
            if completed
            else None,
            "recent_runs": sorted(records, key=lambda r: r["created_at"], reverse=True)[:8],
        }

    @application.get(prefix + "/runs/{identifier}", response_model=RunResponse)
    def run(identifier: str, request: Request):
        return request.app.state.jobs.get(identifier)

    @application.post(prefix + "/runs/{identifier}/cancel", response_model=RunResponse)
    def cancel(identifier: str, request: Request):
        return request.app.state.jobs.cancel(identifier)

    @application.delete(prefix + "/runs/{identifier}", status_code=204)
    def delete_run(identifier: str, request: Request):
        request.app.state.jobs.delete(identifier)
        return Response(status_code=204)

    def query(
        identifier,
        table,
        offset,
        limit,
        search,
        sort,
        descending,
        grid_id,
        voting_model,
        variant,
        metric="",
    ):
        return results.page(
            identifier,
            table,
            offset=offset,
            limit=limit,
            search=search,
            sort=sort,
            descending=descending,
            filters={
                "grid_id": grid_id,
                "voting_model": voting_model,
                "variant": variant,
                "metric": metric,
            },
        )

    @application.get(prefix + "/runs/{identifier}/results", response_model=TableResponse)
    def table(
        identifier: str,
        table: str = "summary",
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(100, ge=1, le=500),
        search: str = Query("", max_length=500),
        sort: str = "",
        descending: bool = False,
        grid_id: str = "",
        voting_model: str = "",
        variant: str = "",
        metric: str = "",
    ):
        return query(
            identifier,
            table,
            offset,
            limit,
            search,
            sort,
            descending,
            grid_id,
            voting_model,
            variant,
            metric,
        )

    @application.get(prefix + "/runs/{identifier}/events", response_model=TableResponse)
    def events(
        identifier: str,
        offset: int = Query(0, ge=0, le=100000),
        limit: int = Query(100, ge=1, le=500),
        search: str = "",
    ):
        return results.page(identifier, "events", offset=offset, limit=limit, search=search)

    @application.get(prefix + "/runs/{identifier}/charts", response_model=TableResponse)
    def charts(
        identifier: str,
        table: str = "summary",
        grid_id: str = "",
        voting_model: str = "",
        variant: str = "",
        metric: str = "",
        limit: int = Query(2000, ge=1, le=5000),
    ):
        return query(
            identifier, table, 0, limit, "", "", False, grid_id, voting_model, variant, metric
        )

    @application.get(prefix + "/runs/{identifier}/export")
    def export(identifier: str, format: str = "zip", table: str = "summary"):
        if table not in TABLES:
            raise ValueError("Unknown result table")
        if format == "zip":
            return FileResponse(
                results.archive(identifier),
                media_type="application/zip",
                filename=f"{identifier}.zip",
            )
        stream = results.export_rows(identifier, table, format)
        return StreamingResponse(
            stream,
            media_type="text/csv" if format == "csv" else "application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{identifier}-{table}.{format}"'
            },
        )

    @application.get(prefix + "/runs/{identifier}/facets", response_model=dict)
    def facets(identifier: str, table: str = "summary"):
        return results.facets(identifier, table)

    @application.post(prefix + "/comparisons", response_model=ComparisonResponse)
    def comparisons(body: ComparisonRequest):
        return results.compare(body.run_ids)

    frontend = PROJECT / "frontend" / "dist"
    if (frontend / "assets").is_dir():
        application.mount(
            "/assets", StaticFiles(directory=frontend / "assets"), name="frontend-assets"
        )

    @application.get("/{path:path}", include_in_schema=False)
    def frontend_page(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API endpoint not found")
        index = frontend / "index.html"
        if index.is_file():
            return FileResponse(index)
        return JSONResponse(
            {
                "message": "Start the frontend development server in frontend/ with npm run dev.",
                "api_docs": "/docs",
            }
        )

    return application


app = create_app()
