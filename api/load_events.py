import json
import os
from pathlib import Path
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.request import Request, urlopen


EVENTS_PATH = Path(__file__).resolve().parents[1] / "generated" / "events" / "sample_events.jsonl"
INGEST_URL = os.getenv("INGEST_URL", "http://localhost:8000/events/ingest")


def debug(message: str) -> None:
    if os.getenv("EVENT_DEBUG") == "1":
        print(f"EVENT_DEBUG load_events {message}")


def read_events(path: Path) -> tuple[int, int, List[Dict[str, Any]]]:
    loaded_count = 0
    malformed_count = 0
    events: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as events_file:
        for line in events_file:
            if not line.strip():
                continue

            loaded_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed_count += 1
                continue

            if not isinstance(event, dict):
                malformed_count += 1
                continue

            events.append(event)

    return loaded_count, malformed_count, events


def main() -> None:
    loaded_count, malformed_count, events = read_events(EVENTS_PATH)
    debug(f"read loaded_count={loaded_count} malformed_count={malformed_count} valid_json_count={len(events)}")

    request = Request(
        INGEST_URL,
        data=json.dumps(events).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        raise RuntimeError(f"Unable to reach FastAPI ingestion endpoint at {INGEST_URL}") from exc

    debug(f"posted url={INGEST_URL} result={result}")
    accepted_count = result["accepted_count"]
    rejected_count = malformed_count + result["rejected_count"]

    print(f"Loaded {loaded_count} events")
    print(f"Accepted {accepted_count} events")
    print(f"Rejected {rejected_count} events")


if __name__ == "__main__":
    main()
