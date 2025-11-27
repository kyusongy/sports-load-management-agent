"""
FastAPI application for the sports load management agent.

Provides REST API for file upload, processing, and result retrieval.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from sports_load_agent.api.routes import router
from sports_load_agent.settings import OUTPUTS_DIR


# Configure logging
logger.add(
    "logs/sports_load_agent.log",
    rotation="10 MB",
    retention="7 days",
    level="INFO",
)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="Sports Load Management Agent",
        description=(
            "LangGraph-based agent for analyzing athlete training load data. "
            "Calculates ACWR (Acute:Chronic Workload Ratio), generates visualizations, "
            "and provides AI-powered interpretation reports."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS configuration for frontend compatibility
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount static files for serving outputs
    app.mount("/static", StaticFiles(directory=str(OUTPUTS_DIR)), name="static")

    # Include API routes
    app.include_router(router, prefix="/api", tags=["API"])

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "Sports Load Management Agent",
            "version": "0.1.0",
            "docs": "/docs",
            "endpoints": {
                "upload": "POST /api/upload",
                "process": "POST /api/process/{session_id}",
                "status": "GET /api/status/{session_id}",
                "results": "GET /api/results/{session_id}",
                "download": "GET /api/download/{session_id}/{filename}",
                "token_stats": "GET /api/token-stats",
            },
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}

    logger.info("Sports Load Management Agent initialized")
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    from sports_load_agent.settings import SERVER_HOST, SERVER_PORT

    uvicorn.run(
        "sports_load_agent.app:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
    )

