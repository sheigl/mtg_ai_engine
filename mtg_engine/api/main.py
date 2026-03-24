import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from mtg_engine.api.routers import game as game_router
from mtg_engine.api.routers import export as export_router
from mtg_engine.api.routers import deck_import as deck_import_router
from mtg_engine.api.routers import debug as debug_router
from mtg_engine.api.routers import ai_game as ai_game_router

app = FastAPI(title="MTG Rules Engine", version="1.0.0")
app.include_router(game_router.router)
app.include_router(export_router.router)
app.include_router(deck_import_router.router)
app.include_router(debug_router.router)
app.include_router(ai_game_router.router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

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
