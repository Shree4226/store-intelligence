import json
from pathlib import Path
from typing import Any, Dict, List

from services.events import ingest_events


EVENTS_PATH = Path(__file__).resolve().parents[1] / "generated" / "events" / "sample_events.jsonl"


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
    result = ingest_events(events)
    accepted_count = result["accepted_count"]
    rejected_count = malformed_count + result["rejected_count"] + result["duplicate_count"]

    print(f"Loaded {loaded_count} events")
    print(f"Accepted {accepted_count} events")
    print(f"Rejected {rejected_count} events")


if __name__ == "__main__":
    main()
