"""
A lightweight access gate for the demo: a shared access code plus a
self-reported name, not real per-user accounts. Every login (and periodic
activity ping) is logged to BigQuery so usage can be reviewed later. If
APP_ACCESS_CODE isn't set (local dev), the gate is skipped entirely.
"""

import os
import time
import uuid
from datetime import datetime, timezone

import streamlit as st

ACCESS_LOG_TABLE = "access_log"
PING_INTERVAL_SECONDS = 60

ACCESS_LOG_SCHEMA = [
    {"name": "log_id", "type": "STRING"},
    {"name": "session_id", "type": "STRING"},
    {"name": "event_type", "type": "STRING"},
    {"name": "user_name", "type": "STRING"},
    {"name": "user_email", "type": "STRING"},
    {"name": "event_time", "type": "TIMESTAMP"},
]


@st.cache_resource(show_spinner=False)
def _bq_client_and_table():
    """Returns (client, table_id), creating the access_log table if needed.
    Cached per container instance so this only runs once, not every rerun."""
    project = os.environ.get("GCP_PROJECT_ID")
    if not project:
        return None, None

    from google.cloud import bigquery

    dataset = os.environ.get("BQ_DATASET", "voc_analytics")
    client = bigquery.Client(project=project)
    table_id = f"{project}.{dataset}.{ACCESS_LOG_TABLE}"

    schema = [bigquery.SchemaField(f["name"], f["type"]) for f in ACCESS_LOG_SCHEMA]
    table = bigquery.Table(table_id, schema=schema)
    try:
        client.create_table(table, exists_ok=True)
    except Exception:
        return None, None
    return client, table_id


def log_event(event_type, session_id, user_name, user_email):
    """Best-effort usage logging -- never blocks or breaks the app if BigQuery
    is unreachable (e.g. local dev, or a transient outage during a demo)."""
    client, table_id = _bq_client_and_table()
    if client is None:
        return
    row = {
        "log_id": str(uuid.uuid4()),
        "session_id": session_id,
        "event_type": event_type,
        "user_name": user_name,
        "user_email": user_email or "",
        "event_time": datetime.now(timezone.utc).isoformat(),
    }
    try:
        client.insert_rows_json(table_id, [row])
    except Exception:
        pass


def require_login():
    """Gates the app behind a name + shared access code. Returns once the
    visitor is authenticated; renders the login form and stops execution
    otherwise. Also fires a periodic 'activity' ping while the app is in use."""
    access_code = os.environ.get("APP_ACCESS_CODE")
    if not access_code:
        return  # no code configured (local dev) -- skip the gate entirely

    if not st.session_state.get("authenticated"):
        st.title("\U0001F4DE Meridian Bank VOC Intelligence")
        st.caption("This demo is access-limited. Enter your name and the access code you were given.")
        with st.form("login_form"):
            name = st.text_input("Your name")
            email = st.text_input("Email (optional)")
            code = st.text_input("Access code", type="password")
            submitted = st.form_submit_button("Enter")

        if submitted:
            if not name.strip():
                st.error("Please enter your name.")
            elif code != access_code:
                st.error("Incorrect access code.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["user_name"] = name.strip()
                st.session_state["user_email"] = email.strip()
                st.session_state["session_id"] = str(uuid.uuid4())
                st.session_state["last_ping"] = time.time()
                log_event("login", st.session_state["session_id"], name.strip(), email.strip())
                st.rerun()
        st.stop()

    # Already authenticated -- periodic lightweight activity ping.
    now = time.time()
    if now - st.session_state.get("last_ping", 0) > PING_INTERVAL_SECONDS:
        st.session_state["last_ping"] = now
        log_event(
            "activity",
            st.session_state["session_id"],
            st.session_state["user_name"],
            st.session_state["user_email"],
        )


def render_user_badge():
    """Small sidebar badge showing who's logged in, with a logout button."""
    if not st.session_state.get("authenticated"):
        return
    with st.sidebar:
        st.caption(f"Signed in as **{st.session_state['user_name']}**")
        if st.button("Log out"):
            for key in ("authenticated", "user_name", "user_email", "session_id", "last_ping"):
                st.session_state.pop(key, None)
            st.rerun()
