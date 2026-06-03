from typing import Any, Dict, List

from .storage import storage

EVENTS_KEY = "events"


def _get_event_store() -> Dict[str, Dict[str, Any]]:
    events = storage.get(EVENTS_KEY)
    if events is None:
        events = {}
        storage.set(EVENTS_KEY, events)
    return events


def ingest_events(events: List[Dict[str, Any]]) -> Dict[str, int]:
    event_store = _get_event_store()
    accepted_count = 0
    duplicate_count = 0
    rejected_count = 0

    for event in events:
        event_id = event.get("event_id")
        if not isinstance(event_id, str) or not event_id.strip():
            rejected_count += 1
            continue

        if event_id in event_store:
            duplicate_count += 1
            continue

        event_store[event_id] = event
        accepted_count += 1

    storage.set(EVENTS_KEY, event_store)
    return {
        "accepted_count": accepted_count,
        "duplicate_count": duplicate_count,
        "rejected_count": rejected_count,
    }


def get_all_events() -> Dict[str, Dict[str, Any]]:
    return _get_event_store()


def get_metrics_for_store(store_id: str) -> Dict[str, object]:
    events = [
        event
        for event in _get_event_store().values()
        if event.get("store_id") == store_id and not bool(event.get("is_staff", False))
    ]

    unique_visitors = len({event.get("visitor_id") for event in events if isinstance(event.get("visitor_id"), str) and event.get("visitor_id")})
    entry_count = sum(1 for event in events if isinstance(event.get("event_type"), str) and event.get("event_type").lower() == "entry")
    exit_count = sum(1 for event in events if isinstance(event.get("event_type"), str) and event.get("event_type").lower() == "exit")

    dwell_values = [
        float(event.get("dwell_ms", 0)) / 1000.0
        for event in events
        if isinstance(event.get("event_type"), str)
        and event.get("event_type").upper() == "ZONE_DWELL"
        and isinstance(event.get("dwell_ms"), (int, float))
        and event.get("dwell_ms") >= 0
    ]
    avg_dwell_seconds = sum(dwell_values) / len(dwell_values) if dwell_values else 0.0

    billing_join_events = [
        event
        for event in events
        if isinstance(event.get("event_type"), str)
        and event.get("event_type").upper() == "BILLING_QUEUE_JOIN"
    ]
    billing_abandon_count = sum(
        1
        for event in events
        if isinstance(event.get("event_type"), str)
        and event.get("event_type").upper() == "BILLING_QUEUE_ABANDON"
    )

    queue_depth = 0
    if billing_join_events:
        latest_join = max(
            billing_join_events,
            key=lambda event: event.get("timestamp", ""),
        )
        metadata = latest_join.get("metadata", {})
        queue_depth_value = metadata.get("queue_depth")
        if isinstance(queue_depth_value, int):
            queue_depth = queue_depth_value
        elif isinstance(queue_depth_value, float):
            queue_depth = int(queue_depth_value)

    total_queue_events = len(billing_join_events) + billing_abandon_count
    abandonment_rate = float(billing_abandon_count) / total_queue_events if total_queue_events > 0 else 0.0

    return {
        "unique_visitors": unique_visitors,
        "entry_count": entry_count,
        "exit_count": exit_count,
        "avg_dwell_seconds": avg_dwell_seconds,
        "queue_depth": queue_depth,
        "abandonment_rate": abandonment_rate,
    }


def get_funnel_for_store(store_id: str) -> Dict[str, object]:
    events = [
        event
        for event in _get_event_store().values()
        if event.get("store_id") == store_id and not bool(event.get("is_staff", False))
    ]

    def has_event(visitor_id: str, match_types: List[str]) -> bool:
        return any(
            isinstance(event.get("visitor_id"), str)
            and event.get("visitor_id") == visitor_id
            and isinstance(event.get("event_type"), str)
            and event.get("event_type").upper() in match_types
            for event in events
        )

    visitor_ids = {
        event.get("visitor_id")
        for event in events
        if isinstance(event.get("visitor_id"), str) and event.get("visitor_id")
    }

    entry_visitors = sum(1 for visitor_id in visitor_ids if has_event(visitor_id, ["ENTRY"]))
    zone_visitors = sum(1 for visitor_id in visitor_ids if has_event(visitor_id, ["ZONE_ENTER"]))
    billing_visitors = sum(1 for visitor_id in visitor_ids if has_event(visitor_id, ["BILLING_QUEUE_JOIN"]))
    purchase_visitors = sum(1 for visitor_id in visitor_ids if has_event(visitor_id, ["PURCHASE"]))

    dropoff_percent = (
        round((entry_visitors - purchase_visitors) / entry_visitors * 100.0, 2)
        if entry_visitors > 0
        else 0.0
    )

    return {
        "entry_visitors": entry_visitors,
        "zone_visitors": zone_visitors,
        "billing_visitors": billing_visitors,
        "purchase_visitors": purchase_visitors,
        "dropoff_percent": dropoff_percent,
    }
