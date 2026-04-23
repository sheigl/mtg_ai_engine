"""Card image proxy with MongoDB cache.

Serves card images from a local MongoDB cache, fetching from Scryfall CDN
on cache miss. Falls back to 404 if the image cannot be retrieved,
allowing the frontend to render text-only cards.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/card", tags=["card-images"])

_MONGO_URL = os.environ.get("MONGODB_URL", "")
_SCRYFALL_CDN_BASE = "https://cards.scryfall.io"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_image_col = None


def _get_image_collection():
    global _image_col
    if _image_col is not None:
        return _image_col
    try:
        import pymongo
        url = _MONGO_URL
        if not url.strip():
            url = "mongodb://root:whatever@sheigl-ms-7a38.tailc63ae8.ts.net"
        mc = pymongo.MongoClient(url, serverSelectionTimeoutMS=3000)
        db_name = os.environ.get("MONGODB_DATABASE", "mtg_training")
        col = mc[db_name]["card_images"]
        col.find_one({})
        col.create_index("scryfall_id", unique=True)
        _image_col = col
        logger.info("Card image proxy: MongoDB connected")
    except Exception as exc:
        logger.warning("Card image proxy: MongoDB unavailable: %s", exc)
    return _image_col


def _fetch_from_scryfall(scryfall_id: str, size: str, face: str) -> Optional[bytes]:
    """Fetch an image from Scryfall CDN."""
    import httpx
    a = scryfall_id[0] if scryfall_id else ""
    b = scryfall_id[1] if len(scryfall_id) > 1 else ""
    url = f"{_SCRYFALL_CDN_BASE}/{size}/{face}/{a}/{b}/{scryfall_id}.jpg"
    try:
        resp = httpx.get(url, headers={"User-Agent": _USER_AGENT}, follow_redirects=True, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.content
    except Exception:
        logger.debug("Failed to fetch image from Scryfall CDN: %s", url)
    return None


@router.get("/image/{scryfall_id}")
def get_card_image(
    scryfall_id: str,
    size: str = "small",
    face: str = "front",
) -> Response:
    """GET /card/image/{scryfall_id}?size=small&face=front — serve a card image."""
    if not scryfall_id or len(scryfall_id) < 2:
        raise HTTPException(status_code=400, detail="Invalid scryfall_id")

    if size not in ("small", "normal", "large"):
        size = "small"
    if face not in ("front", "back"):
        face = "front"

    cache_key = f"{scryfall_id}_{size}_{face}"

    # 1. Try MongoDB cache
    col = _get_image_collection()
    if col is not None:
        try:
            doc = col.find_one({"cache_key": cache_key})
            if doc and "data" in doc:
                return Response(
                    content=doc["data"],
                    media_type="image/jpeg",
                    headers={
                        "Cache-Control": "public, max-age=86400",
                        "X-Cache": "HIT",
                    },
                )
        except Exception:
            logger.debug("MongoDB image cache lookup failed", exc_info=True)

    # 2. Fetch from Scryfall CDN
    image_data = _fetch_from_scryfall(scryfall_id, size, face)

    if image_data is None:
        raise HTTPException(status_code=404, detail="Image not available")

    # 3. Store in MongoDB cache (background; don't block response)
    if col is not None:
        try:
            col.update_one(
                {"cache_key": cache_key},
                {"$set": {"scryfall_id": scryfall_id, "size": size, "face": face, "data": image_data}},
                upsert=True,
            )
        except Exception:
            logger.debug("Failed to cache image in MongoDB", exc_info=True)

    return Response(
        content=image_data,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",
            "X-Cache": "MISS",
        },
    )