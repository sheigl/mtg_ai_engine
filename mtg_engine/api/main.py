from fastapi import FastAPI
from mtg_engine.api.routers import game as game_router
from mtg_engine.api.routers import export as export_router

app = FastAPI(title="MTG Rules Engine", version="1.0.0")
app.include_router(game_router.router)
app.include_router(export_router.router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
