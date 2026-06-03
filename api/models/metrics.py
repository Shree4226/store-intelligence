from pydantic import BaseModel


class MetricsResponse(BaseModel):
    unique_visitors: int
    entry_count: int
    exit_count: int
    avg_dwell_seconds: float
    queue_depth: int
    abandonment_rate: float
