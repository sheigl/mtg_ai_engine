import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from mtg_engine.api.routers import game as game_router
from mtg_engine.api.routers import export as export_router
from mtg_engine.api.routers import deck_import as deck_import_router
from mtg_engine.api.routers import debug as debug_router
from mtg_engine.api.routers import ai_game as ai_game_router
from mtg_engine.api.routers import human_game as human_game_router
from mtg_engine.api.routers import game_records as game_records_router
from mtg_engine.api.routers import player_defaults as player_defaults_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    from mtg_engine.persistence.mongo_client import is_configured, get_games_collection, set_main_loop, ensure_indexes
    set_main_loop(asyncio.get_running_loop())
    if is_configured():
        try:
            collection = get_games_collection()
            import pymongo
            await collection.create_index([("created_at", pymongo.DESCENDING)], background=True)
            await collection.create_index([("is_complete", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)], background=True)
            await collection.create_index([("has_human_player", pymongo.ASCENDING), ("is_complete", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)], background=True)
            await collection.create_index([("format", pymongo.ASCENDING), ("is_complete", pymongo.ASCENDING), ("created_at", pymongo.DESCENDING)], background=True)
            logger.info("MongoDB: indexes created/verified")
        except Exception:
            logger.warning("MongoDB: failed to create indexes", exc_info=True)
        await ensure_indexes()
    yield


app = FastAPI(title="MTG Rules Engine", version="1.0.0", lifespan=lifespan)
app.include_router(game_router.router)
app.include_router(export_router.router)
app.include_router(deck_import_router.router)
app.include_router(debug_router.router)
app.include_router(ai_game_router.router)
app.include_router(human_game_router.router)
app.include_router(game_records_router.router)
app.include_router(player_defaults_router.router)


@app.get("/health")
async def health() -> dict:
    from mtg_engine.persistence.mongo_client import is_configured, get_client
    mongo_status = "not_configured"
    if is_configured():
        try:
            client = get_client()
            await client.admin.command("ping")
            mongo_status = "connected"
        except Exception:
            mongo_status = "error"
    return {"status": "ok", "mongodb": mongo_status}

# Serve frontend SPA from frontend/dist/ if it exists
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

if _frontend_dist.is_dir():
    # Mount static assets (JS, CSS, fonts) at /ui/assets
    _assets_dir = _frontend_dist / "assets"
    if _assets_dir.is_dir():
        app.mount("/ui/assets", StaticFiles(directory=str(_assets_dir)), name="ui-assets")

    @app.get("/ui/{full_path:path}")
    def serve_spa(full_path: str) -> FileResponse:
        """Serve index.html for all /ui/* routes (SPA catch-all)."""
        return FileResponse(str(_frontend_dist / "index.html"))
