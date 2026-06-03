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
