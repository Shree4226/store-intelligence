from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException

from models.event import EventIn, IngestResponse
from models.metrics import MetricsResponse
from services.events import get_metrics_for_store, ingest_events

router = APIRouter()


@router.post("/events/ingest", response_model=IngestResponse)
async def ingest_events_route(
    events: List[Dict[str, Any]] = Body(..., max_items=500),
) -> IngestResponse:
    if not isinstance(events, list):
        raise HTTPException(status_code=400, detail="Request body must be a list of events.")

    validated_events: List[Dict[str, Any]] = []
    for event in events:
        if not isinstance(event, dict):
            validated_events.append({})
            continue

        try:
            EventIn(**event)
        except Exception:
            pass

        validated_events.append(event)

    result = ingest_events(validated_events)
    return IngestResponse(**result)


@router.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
async def get_store_metrics(store_id: str) -> MetricsResponse:
    metrics = get_metrics_for_store(store_id)
    return MetricsResponse(**metrics)
