"""
Loads the enriched VOC dataset for the dashboard. Tries BigQuery first (the
production path, populated by pipeline/vertex_enrich.py); falls back to the
bundled local parquet snapshot if BigQuery isn't reachable or configured, so
the dashboard never goes blank -- important for live demos.
"""

import ast
import os
from pathlib import Path

import pandas as pd
import streamlit as st

LOCAL_FALLBACK_PATH = Path(__file__).resolve().parent.parent / "data" / "enriched_calls.parquet"

LIST_COLUMNS = ["key_topics"]


def _coerce_list_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in LIST_COLUMNS:
        if col not in df.columns:
            continue

        def _to_list(v):
            if isinstance(v, list):
                return v
            if isinstance(v, str) and v.startswith("["):
                try:
                    return ast.literal_eval(v)
                except (ValueError, SyntaxError):
                    return []
            return []

        df[col] = df[col].apply(_to_list)
    return df


@st.cache_data(ttl=300, show_spinner=False)
def load_data():
    """Returns (dataframe, source_label)."""
    project = os.environ.get("GCP_PROJECT_ID")
    dataset = os.environ.get("BQ_DATASET", "voc_analytics")
    table = os.environ.get("BQ_TABLE", "enriched_calls")

    if project:
        try:
            from google.cloud import bigquery

            client = bigquery.Client(project=project)
            query = f"SELECT * FROM `{project}.{dataset}.{table}`"
            df = client.query(query).to_dataframe()
            if len(df) > 0:
                df["call_datetime"] = pd.to_datetime(df["call_datetime"])
                return _coerce_list_columns(df), f"BigQuery ({project}.{dataset}.{table})"
        except Exception:
            pass  # fall through to local snapshot

    if LOCAL_FALLBACK_PATH.exists():
        df = pd.read_parquet(LOCAL_FALLBACK_PATH)
        df["call_datetime"] = pd.to_datetime(df["call_datetime"])
        return _coerce_list_columns(df), "Bundled local snapshot (simulated enrichment)"

    return pd.DataFrame(), "No data available"
