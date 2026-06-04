from fastapi import APIRouter

from api.models.health import HealthResponse
from api.services.events import get_health_summary

router = APIRouter()


@router.get("/health", response_model=HealthResponse, response_model_exclude_none=True)
async def health() -> HealthResponse:
    return HealthResponse(**get_health_summary())
