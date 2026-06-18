"""Client for the external NER / sanitization service (your `app.py` on port 8000).

Our backend never runs the NER model itself — it POSTs text to that service and gets
back detected entities plus highlighted/anonymized text. This module is the boundary:
it owns the HTTP call and the typed shape of the response, so the rest of the codebase
just calls `SanitizerClient.sanitize_to_text(...)` and gets clean de-identified text.

Sanitizer response contract (must match the service):
    {
      "entities": [{entity, text, start, end, confidence}, ...],
      "original_highlighted":   "...*Name*...",
      "anonymized_highlighted": "...*<Person_1>*...",
      "person_map": {"Name": "<Person_1>"}
    }
"""

import httpx
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)

# The service wraps every entity span in asterisks purely for UI highlighting.
# Downstream LLM stages want the text WITHOUT those markers.
HIGHLIGHT_MARKER = "*"


class SanitizerEntity(BaseModel):
    entity: str
    text: str
    start: int
    end: int
    confidence: float


class SanitizationResult(BaseModel):
    """Typed view of the sanitizer's JSON response."""

    entities: list[SanitizerEntity] = Field(default_factory=list)
    original_highlighted: str = ""
    anonymized_highlighted: str = ""
    person_map: dict[str, str] = Field(default_factory=dict)

    @property
    def sanitised_text(self) -> str:
        """Clean de-identified text for downstream stages (markers stripped)."""
        return self.anonymized_highlighted.replace(HIGHLIGHT_MARKER, "")

    @property
    def issues_count(self) -> int:
        return len(self.entities)


class SanitizerUnavailable(Exception):
    """Raised when the sanitizer service can't be reached or returns an error."""


class SanitizerClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 120.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        # URL defaults to config; `transport` lets tests inject a mock without a network.
        self._url = base_url or get_settings().sanitizer_url
        self._timeout = timeout
        self._transport = transport

    async def sanitize(self, text: str) -> SanitizationResult:
        """Call the NER service and return the parsed result.

        Raises SanitizerUnavailable on any transport/HTTP error so callers can decide
        how to degrade (e.g. store raw text and flag for manual review).
        """
        if not text.strip():
            return SanitizationResult()
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, transport=self._transport
            ) as client:
                resp = await client.post(self._url, json={"text": text})
                resp.raise_for_status()
        except httpx.HTTPError as exc:
            log.error("Sanitizer call failed (%s): %s", self._url, exc)
            raise SanitizerUnavailable(str(exc)) from exc
        return SanitizationResult.model_validate(resp.json())

    async def sanitize_to_text(self, text: str) -> tuple[str, int]:
        """Convenience: return (clean_sanitised_text, issues_count).

        This is what the analysis-creation flow uses to populate AnalysisFile.
        Falls back to the original text if the service returns nothing useful.
        """
        result = await self.sanitize(text)
        clean = result.sanitised_text or text
        return clean, result.issues_count
