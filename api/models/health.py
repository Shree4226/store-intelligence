from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float = 0.0
