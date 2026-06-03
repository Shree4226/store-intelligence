from typing import Any, Dict

from pydantic import BaseModel, Field


class EventIn(BaseModel):
    event_id: str = Field(..., min_length=1)

    class Config:
        extra = "allow"


class IngestResponse(BaseModel):
    accepted_count: int
    duplicate_count: int
    rejected_count: int
