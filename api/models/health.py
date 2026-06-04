from typing import Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    stores_monitored: int
    events_received: int
    last_event_timestamp: Optional[str] = None
    warning: Optional[str] = None
