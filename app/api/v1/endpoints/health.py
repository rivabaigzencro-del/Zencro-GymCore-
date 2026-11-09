from typing import Optional
from fastapi import APIRouter, status, Response
from pydantic import BaseModel
from app.core.config import settings
from app.core.database import check_database_connection, engine
import app.main as app_main

router = APIRouter()


class HealthCheckResponse(BaseModel):
    """Health check status schema."""
    status: str
    project: str
    version: str
    environment: str
    database: Optional[str] = None
    detail: Optional[str] = None


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns the service health status and non-destructive database connectivity verification.",
)
async def health_check(response: Response) -> HealthCheckResponse:
    """Check service and database availability non-destructively."""
    current_engine = getattr(app_main, "engine", engine)
    is_healthy, detail = check_database_connection(current_engine)
    database_status = "healthy" if is_healthy else "unavailable"
    overall_status = "healthy" if is_healthy else "unhealthy"

    if not is_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheckResponse(
        status=overall_status,
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENV,
        database=database_status,
        detail=detail,
    )
