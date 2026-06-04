from typing import List

from pydantic import BaseModel


class ZoneHeatmapData(BaseModel):
    zone_id: str
    visit_count: int
    avg_dwell_seconds: float
    score_0_to_100: float


class HeatmapResponse(BaseModel):
    data_confidence: str
    zones: List[ZoneHeatmapData]
