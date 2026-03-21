"""AI player that calls an OpenAI-compatible LLM to choose actions."""
import json
import logging
import time

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

    def __init__(self, config: PlayerConfig) -> None:
        self._config = config
        self._client = openai.OpenAI(
            base_url=config.base_url,
            api_key="ollama",  # placeholder; most local servers ignore this
        )

    def decide(self, prompt: str) -> tuple[int, str]:
        """
        Send the prompt to the LLM and return (chosen_index, reasoning).

        Retries once on failure. Returns (0, fallback_message) if both attempts fail.
        """
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
