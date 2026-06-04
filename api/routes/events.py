from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException

from api.models.anomaly import AnomalyResponse
from api.models.event import EventIn, IngestResponse
from api.models.funnel import FunnelResponse
from api.models.heatmap import HeatmapResponse
from api.models.metrics import MetricsResponse
from api.services.events import (
    get_anomalies_for_store,
    get_funnel_for_store,
    get_heatmap_for_store,
    get_metrics_for_store,
    ingest_events,
)

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


@router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def get_store_funnel(store_id: str) -> FunnelResponse:
    funnel = get_funnel_for_store(store_id)
    return FunnelResponse(**funnel)


@router.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_store_heatmap(store_id: str) -> HeatmapResponse:
    heatmap = get_heatmap_for_store(store_id)
    return HeatmapResponse(**heatmap)


@router.get("/stores/{store_id}/anomalies", response_model=AnomalyResponse)
async def get_store_anomalies(store_id: str) -> AnomalyResponse:
    anomalies = get_anomalies_for_store(store_id)
    return AnomalyResponse(**anomalies)
