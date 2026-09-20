#!/usr/bin/env python3
"""
Produces a local, no-API-calls-required stand-in for what vertex_enrich.py
would output, so the Streamlit dashboard has real data to render before
anyone has run the live Vertex AI pipeline (and so local dev/CI never
depends on GCP credentials).

This is a *placeholder*: labels are derived directly from the scenario
metadata baked into the synthetic data generator, with a small amount of
injected label noise so it doesn't look suspiciously perfect. It intentionally
uses the same output schema as vertex_enrich.py so the Streamlit app doesn't
care which one produced the data. Run vertex_enrich.py against a real GCP
project + Vertex AI to get genuine Gemini-generated labels.

Usage:
    python simulate_enrich.py --input ../data/synthetic_transcripts.csv \
        --output ../data/enriched_calls.parquet
"""

import argparse
import random

import pandas as pd

URGENCY_BY_CATEGORY = {
    "Unauthorized transaction": "critical",
    "Account takeover concern": "critical",
    "Phishing / scam victim": "critical",
    "Dispute resolution delay": "high",
    "Wire transfer issue": "high",
    "Business loan delay": "high",
    "Refinance delay": "medium",
    "Closing cost surprise": "medium",
}

SUMMARY_TEMPLATES = {
    "complaint": "Customer contacted {lob} to report an issue with {topic}.",
    "opportunity": "Customer expressed interest in {topic} during a {lob} call.",
    "neutral": "Routine {lob} service request regarding {topic}.",
}


def derive_row(row, rng):
    scenario_type = row["scenario_type"]
    category = row["scenario_key"]
    lob = row["lob"]

    is_complaint = scenario_type == "complaint"
    is_opportunity = scenario_type == "opportunity"

    # small amount of injected label noise so the "AI accuracy" panel isn't a
    # suspicious 100% -- real LLM extraction has a realistic error rate too.
    if rng.random() < 0.05:
        is_complaint, is_opportunity = not is_complaint, is_opportunity if is_complaint else is_opportunity

    if scenario_type == "complaint":
        sentiment_score = round(rng.uniform(-0.95, -0.25), 2)
    elif scenario_type == "opportunity":
        sentiment_score = round(rng.uniform(0.15, 0.75), 2)
    else:
        sentiment_score = round(rng.uniform(-0.15, 0.25), 2)

    sentiment = "negative" if sentiment_score < -0.15 else ("positive" if sentiment_score > 0.15 else "neutral")

    urgency = URGENCY_BY_CATEGORY.get(category, None)
    if urgency is None:
        if is_complaint:
            urgency = rng.choices(["medium", "high", "low"], weights=[0.55, 0.25, 0.2])[0]
        else:
            urgency = rng.choices(["low", "medium"], weights=[0.85, 0.15])[0]

    summary = SUMMARY_TEMPLATES[scenario_type].format(lob=lob, topic=(category or "a general inquiry").lower())

    topics = [t.lower() for t in category.split("/")] if category else []
    topics = [t.strip() for t in topics] + [lob.split(" ")[0].lower()]

    return {
        "cleaned_transcript": row["clean_transcript_ref"],
        "summary": summary,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "is_complaint": bool(is_complaint),
        "complaint_category": category if is_complaint else "none",
        "is_business_opportunity": bool(is_opportunity),
        "opportunity_type": category if is_opportunity else "none",
        "urgency_level": urgency,
        "key_topics": topics[:5],
        "extraction_error": False,
    }


def run(input_path, output_path, seed=13):
    rng = random.Random(seed)
    df = pd.read_csv(input_path)
    enriched = pd.DataFrame([derive_row(row, rng) for _, row in df.iterrows()])
    out_df = pd.concat([df.reset_index(drop=True), enriched], axis=1)

    if output_path.endswith(".parquet"):
        out_df.to_parquet(output_path, index=False)
    else:
        out_df.to_csv(output_path, index=False)
    return out_df


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=13)
    args = parser.parse_args()
    out_df = run(args.input, args.output, args.seed)
    print(f"Wrote {len(out_df)} simulated-enrichment rows to {args.output}")


if __name__ == "__main__":
    main()
