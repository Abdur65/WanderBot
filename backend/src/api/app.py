from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="WanderBot API",
        description="LangGraph-powered AI travel itinerary planner",
        version="0.4.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # restrict to frontend origin in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
