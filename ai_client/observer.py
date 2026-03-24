"""
Observer AI: analyzes each non-pass action and rates it good/acceptable/suboptimal.
Feature 011-observer-ai-commentary.
"""
import json
import logging
import time
import uuid

import openai

logger = logging.getLogger(__name__)

_OBSERVER_SYSTEM = (
    "You are an expert Magic: The Gathering analyst observing an AI vs AI game. "
    "You will be given the game state, the action chosen by an AI player, and all legal actions "
    "that were available at that moment. "
    "Rate the play as one of: good, acceptable, suboptimal. "
    "If suboptimal, you MUST name a specific better alternative from the legal actions list. "
    "Respond with valid JSON only: "
    "{\"rating\": \"good|acceptable|suboptimal\", \"explanation\": \"<2-3 sentences>\", \"alternative\": \"<action description or null>\"}"
)


class ObserverAI:
    """
    Calls an OpenAI-compatible LLM to rate each non-pass play.
    Runs in the AI client process (not the engine) so the engine stays LLM-free.
    """

    def __init__(self, base_url: str, model: str) -> None:
        self._model = model
        self._client = openai.OpenAI(base_url=base_url, api_key="ollama")

    def analyze(
        self,
        player_name: str,
        turn: int,
        phase: str,
        step: str,
        chosen_action_desc: str,
        legal_actions: list[dict],
        game_state_summary: str,
    ) -> dict:
        """
        Rate the play and return a dict with rating, explanation, alternative.
        On timeout or error, returns a placeholder so the game keeps running.
        """
        legal_list = "\n".join(
            f"  {i}. {a.get('description', a.get('action_type', '?'))}"
            for i, a in enumerate(legal_actions)
        )
        prompt = (
            f"Turn {turn} | {phase} / {step}\n"
            f"Player: {player_name}\n\n"
            f"Game state summary:\n{game_state_summary}\n\n"
            f"Chosen action: {chosen_action_desc}\n\n"
            f"All legal actions available:\n{legal_list}\n\n"
            "Rate this play."
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _OBSERVER_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                timeout=15.0,
            )
            content = response.choices[0].message.content or ""
            return self._parse(content)
        except Exception as exc:
            logger.warning("ObserverAI.analyze failed: %s", exc)
            return {
                "rating": None,
                "explanation": f"Analysis unavailable ({exc})",
                "alternative": None,
            }

    def _parse(self, content: str) -> dict:
        text = content.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            data = json.loads(text)
            rating = data.get("rating", "").lower()
            if rating not in ("good", "acceptable", "suboptimal"):
                rating = "acceptable"
            explanation = data.get("explanation") or "No explanation provided."
            alternative = data.get("alternative")
            # Only keep alternative for suboptimal ratings
            if rating != "suboptimal":
                alternative = None
            return {"rating": rating, "explanation": explanation, "alternative": alternative}
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.debug("ObserverAI could not parse LLM response: %r", content)
            return {"rating": "acceptable", "explanation": content[:200] or "No analysis.", "alternative": None}
