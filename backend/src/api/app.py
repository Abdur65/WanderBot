from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import router
from decouple import config as decouple_config


def create_app() -> FastAPI:
    app = FastAPI(
        title="WanderBot API",
        description="LangGraph-powered AI travel itinerary planner",
        version="0.4.0",
    )

    allowed_origins = decouple_config(
        "ALLOWED_ORIGINS",
        default="http://localhost:5173"
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.4.0"}

    return app


app = create_app()
