from fastapi import FastAPI

from routes.health import router as health_router

app = FastAPI(
    title="Store Intelligence API",
    version="0.1.0",
    description="FastAPI service for store intelligence endpoints.",
)

app.include_router(health_router)


@app.get("/", response_model=dict)
async def root() -> dict:
    return {"status": "ok", "message": "Store Intelligence API"}
