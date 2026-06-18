"""Tests for the sanitizer client.

We use httpx.MockTransport to fake the NER service: it returns a canned response in the
exact shape your `app.py` produces, so we verify OUR parsing/cleaning logic without
downloading the roberta model or running the service.
"""

import httpx
import pytest

from app.services.sanitizer_client import SanitizerClient, SanitizerUnavailable

# A canned response matching the real service's contract.
FAKE_RESPONSE = {
    "entities": [
        {"entity": "PER", "text": "John", "start": 0, "end": 4, "confidence": 0.98},
        {"entity": "ORG", "text": "Acme", "start": 9, "end": 13, "confidence": 0.95},
        {"entity": "PER", "text": "Mary", "start": 18, "end": 22, "confidence": 0.97},
    ],
    "original_highlighted": "*John* met *Acme* and *Mary*",
    "anonymized_highlighted": "*<Person_1>* met *Acme* and *Person_2*",
    "person_map": {"John": "<Person_1>", "Mary": "<Person_2>"},
}


def _client_returning(payload: dict, status: int = 200) -> SanitizerClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=payload)

    return SanitizerClient(
        base_url="http://test/ner", transport=httpx.MockTransport(handler)
    )


async def test_sanitize_parses_response():
    client = _client_returning(FAKE_RESPONSE)
    result = await client.sanitize("John met Acme and Mary")
    assert result.issues_count == 3
    assert result.person_map["John"] == "<Person_1>"
    # Persons anonymized, org kept, highlight markers removed.
    assert result.sanitised_text == "<Person_1> met Acme and Person_2"


async def test_sanitize_to_text_returns_clean_text_and_count():
    client = _client_returning(FAKE_RESPONSE)
    clean, count = await client.sanitize_to_text("John met Acme and Mary")
    assert "*" not in clean
    assert count == 3


async def test_empty_text_short_circuits():
    client = _client_returning(FAKE_RESPONSE)
    clean, count = await client.sanitize_to_text("   ")
    assert clean == "   "  # falls back to original
    assert count == 0


async def test_service_error_raises_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = SanitizerClient(
        base_url="http://test/ner", transport=httpx.MockTransport(handler)
    )
    with pytest.raises(SanitizerUnavailable):
        await client.sanitize("anything")
