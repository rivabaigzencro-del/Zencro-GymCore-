from typing import Optional
from fastapi import APIRouter, status, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db

router = APIRouter()


class HealthCheckResponse(BaseModel):
    """Health check status schema."""
    status: str
    project: str
    version: str
    environment: str
    database: Optional[str] = None


@router.get(
    "/health",
    response_model=HealthCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Returns the service health status and non-destructive database connectivity verification.",
)
async def health_check(response: Response, db: Session = Depends(get_db)) -> HealthCheckResponse:
    """Check service and database availability non-destructively."""
    database_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"

    overall_status = "healthy" if database_status == "healthy" else "unhealthy"
    if overall_status != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthCheckResponse(
        status=overall_status,
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENV,
        database=database_status,
    )
