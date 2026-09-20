"""
Per-call Vertex AI token usage logging, so cost drivers (like unexpectedly
high output/thinking-token usage) show up in BigQuery immediately instead of
only surfacing a day later in the Cloud Billing report.

Best-effort throughout: logging usage must never break the actual AI call
it's describing.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

USAGE_LOG_TABLE = "vertex_usage_log"

USAGE_LOG_SCHEMA = [
    {"name": "log_id", "type": "STRING"},
    {"name": "context", "type": "STRING"},  # e.g. "batch_enrichment" or "live_demo"
    {"name": "call_id", "type": "STRING"},
    {"name": "model_name", "type": "STRING"},
    {"name": "prompt_tokens", "type": "INTEGER"},
    {"name": "output_tokens", "type": "INTEGER"},  # visible output only
    {"name": "thoughts_tokens", "type": "INTEGER"},  # hidden reasoning tokens, billed as output
    {"name": "total_tokens", "type": "INTEGER"},
    {"name": "estimated_cost_usd", "type": "FLOAT"},
    {"name": "event_time", "type": "TIMESTAMP"},
]


def _estimate_cost(prompt_tokens, output_tokens, thoughts_tokens):
    """Approximate only -- Cloud Billing is the source of truth, and pricing
    changes over time. Reads VERTEX_PRICE_INPUT_PER_1M / VERTEX_PRICE_OUTPUT_PER_1M
    (USD per 1M tokens) from the environment; returns None if either is unset
    rather than guessing a number that could be wrong. Thinking tokens are
    billed at the output rate, same as visible output tokens."""
    input_price = os.environ.get("VERTEX_PRICE_INPUT_PER_1M")
    output_price = os.environ.get("VERTEX_PRICE_OUTPUT_PER_1M")
    if not input_price or not output_price:
        return None
    try:
        input_price, output_price = float(input_price), float(output_price)
    except ValueError:
        return None
    billable_output = (output_tokens or 0) + (thoughts_tokens or 0)
    return round((prompt_tokens or 0) * input_price / 1_000_000 + billable_output * output_price / 1_000_000, 6)


def ensure_table(bq_client, project, dataset):
    """Call once per process, not per row -- table creation is idempotent
    but there's no reason to hit the API on every single call."""
    from google.cloud import bigquery

    table_id = f"{project}.{dataset}.{USAGE_LOG_TABLE}"
    schema = [bigquery.SchemaField(f["name"], f["type"]) for f in USAGE_LOG_SCHEMA]
    bq_client.create_table(bigquery.Table(table_id, schema=schema), exists_ok=True)
    return table_id


def log_usage(bq_client, table_id, context, call_id, model_name, usage_metadata):
    if bq_client is None or table_id is None or usage_metadata is None:
        return
    prompt_tokens = usage_metadata.prompt_token_count or 0
    output_tokens = usage_metadata.candidates_token_count or 0
    thoughts_tokens = usage_metadata.thoughts_token_count or 0
    row = {
        "log_id": str(uuid.uuid4()),
        "context": context,
        "call_id": call_id,
        "model_name": model_name,
        "prompt_tokens": prompt_tokens,
        "output_tokens": output_tokens,
        "thoughts_tokens": thoughts_tokens,
        "total_tokens": usage_metadata.total_token_count or 0,
        "estimated_cost_usd": _estimate_cost(prompt_tokens, output_tokens, thoughts_tokens),
        "event_time": datetime.now(timezone.utc).isoformat(),
    }
    try:
        errors = bq_client.insert_rows_json(table_id, [row])
        if errors:
            print(f"[usage_log] insert_rows_json returned errors: {errors}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"[usage_log] failed to log usage: {exc}", file=sys.stderr)
