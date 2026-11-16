from fastapi import APIRouter
from ..schemas.common import AnalyticsResponse
from ..services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("", response_model=AnalyticsResponse)
async def get_analytics():
    """
    Retrieve platform-level aggregate execution analytics, tool performance, and cost.
    """
    return await AnalyticsService.get_analytics()
