from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.opportunities import router as opportunities_router
from app.clients.opticodds import OpticOddsClient
from app.core.logging_config import configure_logging


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.opticodds_client = OpticOddsClient()
    try:
        yield
    finally:
        await app.state.opticodds_client.close()


app = FastAPI(
    title="OpticOdds Soccer Opportunities API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(opportunities_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
