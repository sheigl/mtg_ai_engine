"""
Observer AI: analyzes each non-pass action and rates it good/acceptable/suboptimal.
Feature 011-observer-ai-commentary.
"""
import json
import logging
import time
import uuid
from typing import Callable

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
        content_callback: Callable[[str], None] | None = None,
        thinking_callback: Callable[[str], None] | None = None,
        stop_check: Callable[[], bool] | None = None,
    ) -> dict:
        """
        Rate the play and return a dict with rating, explanation, alternative.
        If content_callback is provided, streams response tokens to it as they arrive.
        If thinking_callback is provided, streams reasoning/thinking tokens to it.
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
        messages = [
            {"role": "system", "content": _OBSERVER_SYSTEM},
            {"role": "user", "content": prompt},
        ]

        try:
            if content_callback is not None or thinking_callback is not None:
                return self._analyze_streaming(messages, content_callback, thinking_callback, stop_check)
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
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

    def _analyze_streaming(
        self,
        messages: list[dict],
        content_callback: Callable[[str], None] | None,
        thinking_callback: Callable[[str], None] | None,
        stop_check: Callable[[], bool] | None,
    ) -> dict:
        """
        Stream the LLM response. Calls content_callback for response tokens and
        thinking_callback for reasoning/thinking tokens (e.g. extended thinking models).
        stop_check is polled after each chunk — if it returns True, streaming stops early.
        Returns parsed result.
        """
        accumulated = ""
        try:
            with self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.2,
                timeout=60.0,
                stream=True,
            ) as stream:
                for chunk in stream:
                    if stop_check and stop_check():
                        break
                    if not chunk.choices:
                        continue
                    delta = chunk.choices[0].delta
                    # Regular response content
                    content = delta.content
                    if content:
                        accumulated += content
                        if content_callback:
                            content_callback(content)
                    # Extended thinking / reasoning tokens (field name varies by server)
                    thinking = (
                        getattr(delta, 'reasoning_content', None)
                        or getattr(delta, 'reasoning', None)
                        or getattr(delta, 'thinking', None)
                    )
                    if thinking and thinking_callback:
                        thinking_callback(thinking)
        except Exception as exc:
            logger.warning("ObserverAI streaming failed: %s", exc)
            if not accumulated:
                return {
                    "rating": None,
                    "explanation": f"Analysis unavailable ({exc})",
                    "alternative": None,
                }
        return self._parse(accumulated)

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
