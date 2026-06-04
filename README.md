# Store Intelligence

Store Intelligence is a retail analytics prototype that detects people in store video, tracks visitor sessions, generates structured events, and exposes analytics through a FastAPI backend.

It covers detection, event generation, ingestion, health checks, metrics, funnel analysis, heatmap aggregation, anomaly output, Docker support, structured logging, and tests.

## Architecture

```text
Store Videos
    |
    v
YOLOv8 Person Detection
    |
    v
ByteTrack Visitor Tracking
    |
    v
Session Manager + Zone Manager
    |
    v
Retail Event JSONL
    |
    v
FastAPI Ingestion API
    |
    v
In-Memory Event Store
    |
    v
Metrics / Funnel / Heatmap / Anomalies
```

## Setup

Run exactly these 5 commands from the project root:

```powershell
python -m venv venv
.\venv\Scripts\activate
python -m pip install -r api\requirements.txt
python -m pip install -r requirements-dev.txt
python api\generate_sample_events.py
```

## Running Detection Pipeline

Run the entry camera event pipeline:

```powershell
python -m detection.event_generator
```

This reads the configured entry video, tracks people, creates visitor sessions, and writes events to `generated/events/store1_entry_events.jsonl`.

## Running API

Run locally:

```powershell
uvicorn api.main:app --reload
```

Run with Docker:

```powershell
docker compose up --build
```

The API runs on `http://127.0.0.1:8000`.

## Running Tests

```powershell
python -m pytest tests -q
```

## Project Structure

```text
api/
  main.py                 FastAPI app, middleware, exception handlers
  routes/                 API route definitions
  services/               In-memory storage and analytics logic
  models/                 Pydantic response models
  generate_sample_events.py
  load_events.py

detection/
  detect.py               YOLOv8 person detection
  tracker.py              ByteTrack-based tracking
  event_generator.py      Entry, exit, zone, dwell, billing event generation
  session_manager.py      Visitor session tracking
  zone_manager.py         Zone polygon lookup
  tools/                  Helper scripts

config/
  store_layout.json       Store zone layout

generated/
  events/                 Generated JSONL events and sessions
  debug/                  Debug frames and videos

tests/
  test_api.py             Pytest coverage for API readiness
```

## Sample API Requests

Health:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Ingest events:

```powershell
$lines = Get-Content generated\events\sample_events.jsonl
$body = "[" + ($lines -join ",") + "]"
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/events/ingest -ContentType "application/json" -Body $body
```

Metrics:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/stores/STORE_BLR_002/metrics
```

Funnel:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/stores/STORE_BLR_002/funnel
```

Heatmap:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/stores/STORE_BLR_002/heatmap
```

Anomalies:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/stores/STORE_BLR_002/anomalies
```

## Known Limitations

- Storage is in-memory, so events reset when the API process restarts.
- The detection pipeline is CPU-friendly but can be slow on longer videos.
- The current anomaly endpoint returns simple rule-based anomalies only.
- Generated outputs are ignored by git and should be regenerated locally.
- No persistent database, authentication, or production queue is included.

## Challenge Mapping

### Part A

Detection pipeline using YOLOv8 and ByteTrack, visitor tracking, session management, zone detection, and JSONL event generation.

### Part B

FastAPI ingestion and analytics endpoints for health, metrics, funnel, heatmap, and anomalies.

### Part C

Production readiness features: Docker support, structured JSON request logging, idempotent ingestion, graceful error handling, and pytest coverage.

### Part D

Documentation and decision rationale through `README.md`, `DESIGN.md`, and `CHOICES.md`.
