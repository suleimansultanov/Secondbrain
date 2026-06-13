"""Claude answer client (Anthropic). Injectable for tests."""

from __future__ import annotations

from app.core.config import get_settings

MAX_TOKENS = 1024


class ClaudeAnswerClient:
    def __init__(self, client=None, model: str | None = None) -> None:
        self._client = client
        self._model = model or get_settings().answer_model

    def _messages(self):
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=get_settings().anthropic_api_key).messages
        return self._client

    async def generate(self, system: str, question: str, context: str) -> str:
        user_content = f"Context passages:\n{context}\n\nQuestion: {question}"
        resp = await self._messages().create(
            model=self._model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        # Concatenate text blocks of the response.
        return "".join(
            block.text for block in resp.content if getattr(block, "type", None) == "text"
        )
