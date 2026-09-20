"""Offline test of the enrichment pipeline's parsing/retry logic, with the
Vertex AI model mocked out (no live GCP credentials required)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))

from vertex_enrich import enrich_one, FALLBACK_RECORD  # noqa: E402


def _fake_response(payload):
    resp = MagicMock()
    resp.text = json.dumps(payload)
    return resp


def test_enrich_one_happy_path():
    model = MagicMock()
    payload = {
        "cleaned_transcript": "Agent: Thank you for calling. Customer: My card was declined.",
        "summary": "Customer reports repeated debit card declines.",
        "sentiment": "negative",
        "sentiment_score": -0.6,
        "is_complaint": True,
        "complaint_category": "Debit card issue",
        "is_business_opportunity": False,
        "opportunity_type": "none",
        "urgency_level": "medium",
        "key_topics": ["debit card", "decline"],
    }
    model.generate_content.return_value = _fake_response(payload)

    record = enrich_one(model, "Retail & Consumer Banking", "raw noisy transcript text")

    assert record["is_complaint"] is True
    assert record["complaint_category"] == "Debit card issue"
    assert record["extraction_error"] is False


def test_enrich_one_falls_back_after_retries(monkeypatch):
    model = MagicMock()
    model.generate_content.side_effect = RuntimeError("simulated API error")
    monkeypatch.setattr("vertex_enrich.time.sleep", lambda *_: None)

    record = enrich_one(model, "Fraud & Disputes", "raw noisy transcript text")

    assert record["extraction_error"] is True
    assert record["complaint_category"] == FALLBACK_RECORD["complaint_category"]
    assert model.generate_content.call_count == 4
