# Decision 1: Detection model choice

## Options considered

- YOLOv8
- RT-DETR
- YOLOv9

## AI suggestion

AI suggested YOLOv8 because it is widely used, easy to run locally, and has strong support through the Ultralytics package.

## Final choice

YOLOv8.

## Reasoning

YOLOv8 was the best fit for this project because it is simple to install, has a small nano model for CPU-friendly inference, and works well for person detection in retail video. RT-DETR and YOLOv9 were considered, but they would add more complexity for this challenge without a clear benefit.

# Decision 2: Event schema design

## Options considered

- Use raw detector output directly
- Use separate schemas for each event type
- Use one shared retail analytics event schema

## AI suggestion

AI suggested using one shared event schema with consistent fields across all event types.

## Final choice

One shared retail analytics event schema.

## Reasoning

A shared schema makes ingestion, validation, metrics, funnel, and heatmap aggregation easier. Fields such as `event_id`, `store_id`, `visitor_id`, `event_type`, `timestamp`, `zone_id`, `dwell_ms`, and `metadata` are present on every event, even when some values are empty or null. This keeps downstream API logic simple and predictable.

# Decision 3: API architecture

## Options considered

- Flask API
- FastAPI API
- A script-only pipeline with no API layer

## AI suggestion

AI suggested FastAPI because it supports typed request and response models, automatic API documentation, and simple endpoint development.

## Final choice

FastAPI.

## Reasoning

FastAPI was chosen because the project needs clear API endpoints for ingestion, health checks, metrics, funnel, heatmap, and anomalies. Pydantic response models help keep responses consistent, and the built-in OpenAPI documentation makes the project easier to review and test.
