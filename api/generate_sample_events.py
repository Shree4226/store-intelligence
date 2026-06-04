import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4


OUTPUT_PATH = Path(__file__).resolve().parents[1] / "generated" / "events" / "sample_events.jsonl"
STORE_ID = "STORE_BLR_002"
CAMERA_ID = "CAM1"
EVENT_COUNT = 100
VISITOR_COUNT = 20

EVENT_TYPES = [
    "ENTRY",
    "ZONE_ENTER",
    "ZONE_DWELL",
    "ZONE_EXIT",
    "BILLING_QUEUE_JOIN",
    "BILLING_QUEUE_ABANDON",
    "EXIT",
]

ZONE_IDS = [
    "ENTRANCE",
    "AISLE_GROCERY",
    "AISLE_BEAUTY",
    "AISLE_DAIRY",
    "PROMO_ENDCAP",
    "BILLING_QUEUE",
    "EXIT_GATE",
]

SKU_ZONES = {
    "AISLE_GROCERY": "packaged_foods",
    "AISLE_BEAUTY": "personal_care",
    "AISLE_DAIRY": "chilled_dairy",
    "PROMO_ENDCAP": "seasonal_promo",
}


def _metadata(queue_depth: Optional[int], sku_zone: Optional[str], session_seq: int) -> Dict[str, Any]:
    return {
        "queue_depth": queue_depth,
        "sku_zone": sku_zone,
        "session_seq": session_seq,
    }


def _event(
    visitor_id: str,
    event_type: str,
    timestamp: datetime,
    zone_id: str,
    session_seq: int,
    dwell_ms: int = 0,
    queue_depth: Optional[int] = None,
    sku_zone: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "event_id": str(uuid4()),
        "store_id": STORE_ID,
        "camera_id": CAMERA_ID,
        "visitor_id": visitor_id,
        "event_type": event_type,
        "timestamp": timestamp.isoformat(),
        "zone_id": zone_id,
        "dwell_ms": dwell_ms,
        "is_staff": False,
        "confidence": round(random.uniform(0.88, 0.98), 2),
        "metadata": _metadata(queue_depth, sku_zone, session_seq),
    }


def generate_events() -> List[Dict[str, Any]]:
    random.seed(42)
    start_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)
    visitors = [f"VISITOR_{index:03d}" for index in range(1, VISITOR_COUNT + 1)]
    events: List[Dict[str, Any]] = []

    for index, visitor_id in enumerate(visitors):
        session_start = start_time + timedelta(minutes=index * 5, seconds=random.randint(0, 90))
        session_seq = index + 1
        shopping_zone = random.choice(["AISLE_GROCERY", "AISLE_BEAUTY", "AISLE_DAIRY", "PROMO_ENDCAP"])

        events.extend(
            [
                _event(visitor_id, "ENTRY", session_start, "ENTRANCE", session_seq),
                _event(
                    visitor_id,
                    "ZONE_ENTER",
                    session_start + timedelta(minutes=random.randint(2, 8)),
                    shopping_zone,
                    session_seq,
                    sku_zone=SKU_ZONES[shopping_zone],
                ),
                _event(
                    visitor_id,
                    "ZONE_DWELL",
                    session_start + timedelta(minutes=random.randint(9, 18)),
                    shopping_zone,
                    session_seq,
                    dwell_ms=random.randint(45_000, 420_000),
                    sku_zone=SKU_ZONES[shopping_zone],
                ),
                _event(
                    visitor_id,
                    "ZONE_EXIT",
                    session_start + timedelta(minutes=random.randint(19, 28)),
                    shopping_zone,
                    session_seq,
                    sku_zone=SKU_ZONES[shopping_zone],
                ),
            ]
        )

    for index, visitor_id in enumerate(visitors[:10]):
        session_seq = index + 1
        base_time = start_time + timedelta(minutes=index * 5 + 36, seconds=random.randint(0, 90))
        events.append(
            _event(
                visitor_id,
                "BILLING_QUEUE_JOIN",
                base_time,
                "BILLING_QUEUE",
                session_seq,
                queue_depth=random.randint(1, 8),
            )
        )

    for index, visitor_id in enumerate(visitors[:5]):
        session_seq = index + 1
        base_time = start_time + timedelta(minutes=index * 5 + 48, seconds=random.randint(0, 90))
        events.append(
            _event(
                visitor_id,
                "BILLING_QUEUE_ABANDON",
                base_time,
                "BILLING_QUEUE",
                session_seq,
                queue_depth=random.randint(3, 10),
            )
        )

    for index, visitor_id in enumerate(visitors[5:10], start=5):
        session_seq = index + 1
        base_time = start_time + timedelta(minutes=index * 5 + 58, seconds=random.randint(0, 90))
        events.append(_event(visitor_id, "EXIT", base_time, "EXIT_GATE", session_seq))

    events.sort(key=lambda event: event["timestamp"])
    if len(events) != EVENT_COUNT:
        raise RuntimeError(f"Expected {EVENT_COUNT} events, generated {len(events)}.")

    return events


def main() -> None:
    events = generate_events()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as output_file:
        for event in events:
            output_file.write(json.dumps(event, separators=(",", ":")) + "\n")

    print(f"Total events generated: {len(events)}")


if __name__ == "__main__":
    main()
