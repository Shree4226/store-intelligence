from typing import List

from pydantic import BaseModel


class AnomalyItem(BaseModel):
    anomaly_type: str
    severity: str
    message: str
    value: float


class AnomalyResponse(BaseModel):
    store_id: str
    anomalies: List[AnomalyItem]
