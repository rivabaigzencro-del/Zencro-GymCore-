from fastapi import FastAPI, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.core.config import settings
from app.core.database import engine, check_database_connection
from app.api.v1.api import api_router


def create_application() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=settings.DESCRIPTION,
        docs_url="/docs" if settings.ENV != "production" else None,
        redoc_url="/redoc" if settings.ENV != "production" else None,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.ENV != "production" else None,
    )

    # Configure CORS middleware
    if settings.BACKEND_CORS_ORIGINS:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.BACKEND_CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Root service status
    @application.get(
        "/",
        status_code=status.HTTP_200_OK,
        tags=["Root"],
        summary="API Root Information",
    )
    async def root():
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.VERSION,
            "docs": "/docs",
            "health": f"{settings.API_V1_STR}/health",
        }

    # Top-level health check (useful for hosting platform probes / load balancers)
    @application.get(
        "/health",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Service Health Check",
    )
    async def top_level_health(response: Response):
        import app.main as app_main
        current_engine = getattr(app_main, "engine", engine)
        is_healthy, detail = check_database_connection(current_engine)
        db_status = "healthy" if is_healthy else "unavailable"
        overall_status = "healthy" if is_healthy else "unhealthy"

        if not is_healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

        payload = {
            "status": overall_status,
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENV,
            "database": db_status,
        }
        if detail:
            payload["detail"] = detail
        return payload

    # Mount API v1 router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    return application


app = create_application()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
