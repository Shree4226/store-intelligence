import json
import logging
import re
import time
from typing import Any, Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse

from api.routes.events import router as events_router
from api.routes.health import router as health_router
from api.services.storage import StorageUnavailableError

logger = logging.getLogger("store_intelligence.api")
logging.basicConfig(level=logging.INFO, format="%(message)s")
STORE_PATH_PATTERN = re.compile(r"^/stores/([^/]+)")

app = FastAPI(
    title="Store Intelligence API",
    version="0.1.0",
    description="FastAPI service for store intelligence endpoints.",
)

app.include_router(health_router)
app.include_router(events_router)


def _find_store_id(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        store_id = value.get("store_id")
        if isinstance(store_id, str) and store_id:
            return store_id
        for nested_value in value.values():
            nested_store_id = _find_store_id(nested_value)
            if nested_store_id:
                return nested_store_id
    if isinstance(value, list):
        for item in value:
            nested_store_id = _find_store_id(item)
            if nested_store_id:
                return nested_store_id
    return None


async def _store_id_from_request(request: Request) -> Optional[str]:
    path_match = STORE_PATH_PATTERN.match(request.url.path)
    if path_match:
        return path_match.group(1)

    if request.method not in {"POST", "PUT", "PATCH"}:
        return None

    try:
        body = await request.json()
    except Exception:
        return None
    return _find_store_id(body)


@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    trace_id = request.headers.get("x-trace-id") or str(uuid4())
    request.state.trace_id = trace_id
    store_id = await _store_id_from_request(request)
    start_time = time.perf_counter()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        log_record = {
            "trace_id": trace_id,
            "endpoint": request.url.path,
            "latency_ms": latency_ms,
            "status_code": status_code,
        }
        if store_id:
            log_record["store_id"] = store_id
        logger.info(json.dumps(log_record, separators=(",", ":")))


@app.exception_handler(StorageUnavailableError)
async def storage_unavailable_handler(request: Request, exc: StorageUnavailableError) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", str(uuid4()))
    return JSONResponse(
        status_code=503,
        content={
            "error": "SERVICE_UNAVAILABLE",
            "message": "Service temporarily unavailable",
            "trace_id": trace_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    trace_id = getattr(request.state, "trace_id", str(uuid4()))
    logger.error(json.dumps({"trace_id": trace_id, "error": exc.__class__.__name__}, separators=(",", ":")))
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Internal server error",
            "trace_id": trace_id,
        },
    )


@app.get("/", response_model=dict)
async def root() -> dict:
    return {"status": "ok", "message": "Store Intelligence API"}
