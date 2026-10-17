"""Thin provider abstraction. The LLM only plans, adapts discovery and writes evidence-grounded summaries.

Every call has a deterministic fallback, so the product works (and is testable) with LLM_PROVIDER=none.
"""

import json
import logging

from app.config import get_settings

log = logging.getLogger("llm")


class LLM:
    def __init__(self):
        s = get_settings()
        self.provider = s.llm_provider if s.llm_enabled else "none"
        self.model = s.llm_model
        self._client = None
        if self.provider == "anthropic":
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=s.llm_api_key, max_retries=2, timeout=90.0)
        elif self.provider == "openai":
            import openai

            self._client = openai.AsyncOpenAI(api_key=s.llm_api_key, max_retries=2, timeout=90.0)
            if self.model.startswith("claude"):
                self.model = "gpt-4o-mini"

    @property
    def enabled(self) -> bool:
        return self._client is not None

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}" if self.enabled else "deterministic"

    async def json(self, system: str, user: str, schema: dict, max_tokens: int = 8000) -> dict | None:
        """Schema-constrained JSON, or None on any failure (caller falls back deterministically)."""
        if not self.enabled:
            return None
        try:
            if self.provider == "anthropic":
                resp = await self._client.beta.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                    output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                )
                if resp.stop_reason in ("refusal", "max_tokens"):
                    log.warning("LLM stopped with %s", resp.stop_reason)
                    return None
                text = next((b.text for b in resp.content if b.type == "text"), None)
                return json.loads(text) if text else None
            resp = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                response_format={"type": "json_schema", "json_schema": {"name": "out", "schema": schema, "strict": True}},
            )
            return json.loads(resp.choices[0].message.content or "null")
        except Exception as e:  # network, auth, schema — never break the run because of the LLM
            log.warning("LLM call failed: %s", e)
            return None


_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm
