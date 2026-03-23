"""HTTP wrapper for the MTG engine REST API."""
import logging

import httpx

from .models import GameConfig

logger = logging.getLogger(__name__)


class EngineError(Exception):
    """Raised when the engine returns a non-2xx response."""


class EngineClient:
    """Thin synchronous HTTP client for the MTG engine API."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._base}{path}"
        resp = self._client.request(method, url, **kwargs)
        if resp.status_code >= 400:
            body = resp.text
            logger.error("Engine API %s %s → %d: %s", method, url, resp.status_code, body)
            raise EngineError(f"Engine returned {resp.status_code}: {body}")
        return resp.json()

    def create_game(self, config: GameConfig, debug: bool = False) -> str:
        """POST /game — returns the game_id string."""
        body = {
            "player1_name": config.players[0].name,
            "player2_name": config.players[1].name,
            "deck1": config.deck1,
            "deck2": config.deck2,
            "verbose": config.verbose,
            "debug": debug,
            "format": config.format,
        }
        if config.format == "commander":
            if config.commander1:
                body["commander1"] = config.commander1
            if config.commander2:
                body["commander2"] = config.commander2
        data = self._request("POST", "/game", json=body)
        gs = data["data"]
        return gs["game_id"]

    def get_legal_actions(self, game_id: str) -> dict:
        """GET /game/{game_id}/legal-actions — returns the data payload."""
        data = self._request("GET", f"/game/{game_id}/legal-actions")
        return data["data"]

    def get_game_state(self, game_id: str) -> dict:
        """GET /game/{game_id} — returns the full game state dict."""
        data = self._request("GET", f"/game/{game_id}")
        return data["data"]

    def submit_action(self, game_id: str, action_type: str, payload: dict) -> dict:
        """POST the appropriate action endpoint and return the response data."""
        endpoint_map = {
            "pass": "/pass",
            "play_land": "/play-land",
            "cast": "/cast",
            "activate": "/activate",
            "declare_attackers": "/declare-attackers",
            "declare_blockers": "/declare-blockers",
            "order_blockers": "/order-blockers",
            "assign_combat_damage": "/assign-combat-damage",
            "put_trigger": "/put-trigger",
        }
        path_suffix = endpoint_map.get(action_type)
        if path_suffix is None:
            raise EngineError(f"Unknown action_type: {action_type!r}")
        data = self._request("POST", f"/game/{game_id}{path_suffix}", json=payload)
        return data.get("data", {})

    def set_verbose(self, game_id: str, enabled: bool) -> None:
        """POST /game/{game_id}/verbose to toggle play-by-play logging."""
        self._request("POST", f"/game/{game_id}/verbose", json={"enabled": enabled})

    def close(self) -> None:
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
