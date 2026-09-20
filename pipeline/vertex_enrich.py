#!/usr/bin/env python3
"""
Batch-enriches synthetic VOC call transcripts using Vertex AI (Gemini):
sentiment, complaint detection/category, business-opportunity detection,
urgency, key topics, a cleaned transcript, and a one-line summary.

Requires:
  - `gcloud auth application-default login` (or running in an environment
    with a service account that has the Vertex AI User role), and
  - the target GCP project to have the Vertex AI API enabled.

Uses the Google Gen AI SDK (`google-genai`) in Vertex mode, not the older
`vertexai.generative_models` module (deprecated, and no longer serving
current Gemini models on classic regional endpoints). Location is a
multi-region value (`us` or `eu`), not a regional one like `us-central1`.

Usage:
    python vertex_enrich.py \
        --input ../data/synthetic_transcripts.csv \
        --output ../data/enriched_calls.parquet \
        --project voc-dane --location us \
        --load-bigquery --bq-dataset voc_analytics --bq-table enriched_calls
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from google import genai
from google.genai import types

from prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_user_prompt

DEFAULT_MODEL = "gemini-3.8-flash"
DEFAULT_LOCATION = "us"
MAX_RETRIES = 4

FALLBACK_RECORD = {
    "cleaned_transcript": "",
    "summary": "Could not be analyzed automatically.",
    "sentiment": "neutral",
    "sentiment_score": 0.0,
    "is_complaint": False,
    "complaint_category": "none",
    "is_business_opportunity": False,
    "opportunity_type": "none",
    "urgency_level": "low",
    "key_topics": [],
    "extraction_error": True,
}


def enrich_one(client, model_name, lob, raw_transcript):
    prompt = build_user_prompt(lob, raw_transcript)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        response_mime_type="application/json",
        response_schema=RESPONSE_SCHEMA,
        temperature=0.2,
    )
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt, config=config)
            record = json.loads(response.text)
            record["extraction_error"] = False
            return record
        except Exception as exc:  # noqa: BLE001 - broad on purpose, we retry/fallback
            last_err = exc
            time.sleep(min(2 ** attempt, 20))
    print(f"[warn] giving up after {MAX_RETRIES} attempts: {last_err}", file=sys.stderr)
    return dict(FALLBACK_RECORD)


def run(input_path, output_path, project, location, model_name, limit, workers):
    client = genai.Client(vertexai=True, project=project, location=location)

    df = pd.read_csv(input_path)
    if limit:
        df = df.head(limit)

    results = [None] * len(df)

    def task(i, row):
        return i, enrich_one(client, model_name, row["lob"], row["raw_transcript"])

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(task, i, row) for i, row in df.iterrows()]
        done = 0
        for future in as_completed(futures):
            i, record = future.result()
            results[i] = record
            done += 1
            if done % 50 == 0 or done == len(df):
                print(f"[info] enriched {done}/{len(df)}", file=sys.stderr)

    enriched_df = pd.DataFrame(results)
    out_df = pd.concat([df.reset_index(drop=True), enriched_df], axis=1)

    if output_path.endswith(".parquet"):
        out_df.to_parquet(output_path, index=False)
    else:
        out_df.to_csv(output_path, index=False)

    print(f"[info] wrote {len(out_df)} enriched rows to {output_path}", file=sys.stderr)
    return out_df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--location", default=DEFAULT_LOCATION, help="Vertex AI multi-region: 'us' or 'eu'")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--limit", type=int, default=None, help="Only process the first N rows (for quick tests)")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--load-bigquery", action="store_true")
    parser.add_argument("--bq-dataset", default="voc_analytics")
    parser.add_argument("--bq-table", default="enriched_calls")
    parser.add_argument("--bq-location", default="US")
    args = parser.parse_args()

    out_df = run(args.input, args.output, args.project, args.location, args.model, args.limit, args.workers)

    if args.load_bigquery:
        from bigquery_io import load_dataframe

        table_id, rows = load_dataframe(out_df, args.project, args.bq_dataset, args.bq_table, args.bq_location)
        print(f"[info] loaded {rows} rows into {table_id}", file=sys.stderr)


if __name__ == "__main__":
    main()
