"""AI player that calls an OpenAI-compatible LLM to choose actions."""
import json
import logging
import time
from typing import Callable

import openai

from .models import PlayerConfig

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are an expert Magic: The Gathering player. "
    "Read the game state carefully and choose the best legal action. "
    "Reply with valid JSON only: {\"action_index\": <number>, \"reasoning\": \"<your reasoning>\"}"
)


class AIPlayer:
    """Calls an OpenAI-compatible endpoint to decide game actions."""

    def __init__(
        self,
        config: PlayerConfig,
        debug_callback: Callable[[str, str, str], None] | None = None,
    ) -> None:
        self._config = config
        self._client = openai.OpenAI(
            base_url=config.base_url,
            api_key="ollama",  # placeholder; most local servers ignore this
        )
        # debug_callback(event_type, text, entry_id)
        # event_type: "prompt_start" | "response_chunk" | "response_done"
        self._debug_callback = debug_callback

    def decide(self, prompt: str) -> tuple[int, str]:
        """
        Send the prompt to the LLM and return (chosen_index, reasoning).

        When a debug_callback is registered, uses streaming mode so tokens
        can be forwarded to the engine in real-time.
        Retries once on failure. Returns (0, fallback_message) if both attempts fail.
        """
        if self._debug_callback:
            return self._decide_streaming(prompt)
        return self._decide_normal(prompt)

    def _decide_normal(self, prompt: str) -> tuple[int, str]:
        for attempt in range(1, 3):
            try:
                response = self._client.chat.completions.create(
                    model=self._config.model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                )
                content = response.choices[0].message.content or ""
                return self._parse_response(content)
            except (openai.OpenAIError, Exception) as exc:
                logger.warning(
                    "[WARNING] %s AI endpoint failed (attempt %d/2): %s",
                    self._config.name, attempt, exc,
                )
                print(
                    f"[WARNING] {self._config.name} AI endpoint failed "
                    f"(attempt {attempt}/2): {exc}"
                )
                if attempt < 2:
                    time.sleep(2)

        print(f"[WARNING] Falling back to pass priority for {self._config.name}")
        return 0, "(AI endpoint unreachable)"

    def _decide_streaming(self, prompt: str) -> tuple[int, str]:
        """Streaming variant: forwards tokens via debug_callback as they arrive."""
        cb = self._debug_callback
        assert cb is not None  # guarded by caller

        # Signal that prompt is being sent (entry_id assigned by caller via forwarder)
        cb("prompt_start", prompt, "")

        for attempt in range(1, 3):
            try:
                stream = self._client.chat.completions.create(
                    model=self._config.model,
                    messages=[
                        {"role": "system", "content": _SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    stream=True,
                )
                accumulated = ""
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or "" if chunk.choices else ""
                    if delta:
                        accumulated += delta
                        cb("response_chunk", delta, "")
                cb("response_done", accumulated, "")
                return self._parse_response(accumulated)
            except (openai.OpenAIError, Exception) as exc:
                logger.warning(
                    "[WARNING] %s AI streaming failed (attempt %d/2): %s",
                    self._config.name, attempt, exc,
                )
                print(
                    f"[WARNING] {self._config.name} AI streaming failed "
                    f"(attempt {attempt}/2): {exc}"
                )
                if attempt < 2:
                    time.sleep(2)

        cb("response_done", "", "")
        print(f"[WARNING] Falling back to pass priority for {self._config.name}")
        return 0, "(AI endpoint unreachable)"

    def _parse_response(self, content: str) -> tuple[int, str]:
        """Parse JSON response from LLM. Returns (index, reasoning)."""
        # Strip markdown code fences if present
        text = content.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            data = json.loads(text)
            idx = int(data["action_index"])
            reasoning = data.get("reasoning") or "(no reasoning provided)"
            return idx, reasoning
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            logger.warning("Could not parse LLM response: %r", content)
            return 0, "(no reasoning provided)"
