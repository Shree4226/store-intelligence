from pydantic import BaseModel


class FunnelResponse(BaseModel):
    entry_visitors: int
    zone_visitors: int
    billing_visitors: int
    purchase_visitors: int
    dropoff_percent: float
