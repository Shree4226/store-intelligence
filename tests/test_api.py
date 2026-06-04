import asyncio

from fastapi import Request

from api.main import storage_unavailable_handler
from api.routes.events import get_store_metrics, ingest_events_route
from api.routes.health import health
from api.services.storage import StorageUnavailableError
from api.services.storage import storage


def setup_function() -> None:
    storage.clear()


def _event(event_id: str) -> dict:
    return {
        "event_id": event_id,
        "store_id": "STORE_BLR_002",
        "camera_id": "CAM1",
        "visitor_id": "VISITOR_001",
        "event_type": "ENTRY",
        "timestamp": "2026-06-04T10:00:00Z",
        "zone_id": "ENTRANCE",
        "dwell_ms": 0,
        "is_staff": False,
        "confidence": 0.9,
        "metadata": {
            "queue_depth": None,
            "sku_zone": None,
            "session_seq": 1,
        },
    }


def test_duplicate_ingestion() -> None:
    response = asyncio.run(ingest_events_route([_event("evt-1"), _event("evt-1")]))

    assert response.model_dump() == {
        "accepted_count": 1,
        "duplicate_count": 1,
        "rejected_count": 0,
    }


def test_empty_event_list() -> None:
    response = asyncio.run(ingest_events_route([]))

    assert response.model_dump() == {
        "accepted_count": 0,
        "duplicate_count": 0,
        "rejected_count": 0,
    }


def test_empty_store_metrics() -> None:
    response = asyncio.run(get_store_metrics("STORE_BLR_002"))

    assert response.model_dump() == {
        "unique_visitors": 0,
        "entry_count": 0,
        "exit_count": 0,
        "avg_dwell_seconds": 0.0,
        "queue_depth": 0,
        "abandonment_rate": 0.0,
    }


def test_health_endpoint() -> None:
    response = asyncio.run(health())

    assert response.model_dump(exclude_none=True) == {
        "status": "healthy",
        "stores_monitored": 0,
        "events_received": 0,
    }


def test_storage_unavailable_handler() -> None:
    scope = {"type": "http", "method": "GET", "path": "/health", "headers": []}
    request = Request(scope)
    request.state.trace_id = "trace-test"

    response = asyncio.run(storage_unavailable_handler(request, StorageUnavailableError()))

    assert response.status_code == 503
    assert response.body == (
        b'{"error":"SERVICE_UNAVAILABLE","message":"Service temporarily unavailable","trace_id":"trace-test"}'
    )
