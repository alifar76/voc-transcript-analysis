"""
Meridian Bank -- Voice of Customer (VOC) Intelligence dashboard.

A demo of an AI-driven VOC pipeline: synthetic, ASR-quality-degraded call
transcripts -> Vertex AI (Gemini) structured extraction -> BigQuery -> this
dashboard. See the "Methodology" tab for the full picture.
"""

import os
import random
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from data_access import load_data  # noqa: E402
from theme import (  # noqa: E402
    CATEGORICAL,
    DIVERGING_MID,
    DIVERGING_NEG,
    DIVERGING_POS,
    LOB_COLOR,
    LOB_ORDER,
    SEQUENTIAL_BLUE,
    URGENCY_COLOR,
    URGENCY_ICON,
    URGENCY_ORDER,
    apply_layout,
)

st.set_page_config(page_title="Meridian Bank | VOC Intelligence", page_icon="\U0001F4DE", layout="wide")

BANK_NAME = "Meridian Bank"


# ---------------------------------------------------------------------------
# Data loading + filters
# ---------------------------------------------------------------------------

df_all, data_source = load_data()

if df_all.empty:
    st.error(
        "No VOC data available. Run `data_gen/generate_transcripts.py` and either "
        "`pipeline/vertex_enrich.py` (live Vertex AI) or `pipeline/simulate_enrich.py` "
        "(offline placeholder) to produce `data/enriched_calls.parquet`, or point "
        "GCP_PROJECT_ID at a BigQuery table populated by the pipeline."
    )
    st.stop()

st.title(f"\U0001F4DE {BANK_NAME} -- Voice of Customer Intelligence")
st.caption(
    f"Data source: {data_source} · {len(df_all):,} calls · "
    f"{df_all['call_datetime'].min().date()} to {df_all['call_datetime'].max().date()}"
)

filt_col1, filt_col2, filt_col3 = st.columns([2, 2, 1])
with filt_col1:
    min_d, max_d = df_all["call_datetime"].min().date(), df_all["call_datetime"].max().date()
    date_range = st.date_input("Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d)
with filt_col2:
    selected_lobs = st.multiselect("Line of business", options=LOB_ORDER, default=LOB_ORDER)
with filt_col3:
    st.metric("Calls in view", f"{len(df_all):,}")

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_d, end_d = date_range
else:
    start_d, end_d = min_d, max_d

mask = (
    (df_all["call_datetime"].dt.date >= start_d)
    & (df_all["call_datetime"].dt.date <= end_d)
    & (df_all["lob"].isin(selected_lobs))
)
df = df_all.loc[mask].copy()

if df.empty:
    st.warning("No calls match the current filters.")
    st.stop()


def weekly_agg(frame):
    g = frame.set_index("call_datetime").resample("W-MON")
    out = g.agg(
        call_count=("call_id", "count"),
        complaint_rate=("is_complaint", "mean"),
        opportunity_rate=("is_business_opportunity", "mean"),
        avg_sentiment=("sentiment_score", "mean"),
    ).reset_index()
    out = out.rename(columns={"call_datetime": "period"})
    return out


def monthly_agg(frame):
    g = frame.set_index("call_datetime").resample("MS")
    out = g.agg(
        call_count=("call_id", "count"),
        complaint_rate=("is_complaint", "mean"),
        opportunity_rate=("is_business_opportunity", "mean"),
        avg_sentiment=("sentiment_score", "mean"),
    ).reset_index()
    out = out.rename(columns={"call_datetime": "period"})
    return out


def kpi_delta(frame, col, agg="mean", window_days=7):
    end = frame["call_datetime"].max()
    recent = frame[frame["call_datetime"] > end - pd.Timedelta(days=window_days)]
    prior = frame[
        (frame["call_datetime"] <= end - pd.Timedelta(days=window_days))
        & (frame["call_datetime"] > end - pd.Timedelta(days=2 * window_days))
    ]
    if recent.empty or prior.empty:
        return None, None
    r = recent[col].mean() if agg == "mean" else getattr(recent[col], agg)()
    p = prior[col].mean() if agg == "mean" else getattr(prior[col], agg)()
    if p == 0:
        return r, None
    return r, (r - p) / abs(p) * 100


tab_overview, tab_complaints, tab_opps, tab_trends, tab_live, tab_method = st.tabs(
    ["Overview", "Complaints & Risk", "Business Opportunities", "Trends (WoW / MoM)", "Live AI Demo", "Methodology"]
)

# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------
with tab_overview:
    c1, c2, c3, c4 = st.columns(4)
    complaint_rate = df["is_complaint"].mean()
    _, complaint_delta = kpi_delta(df, "is_complaint")
    opp_rate = df["is_business_opportunity"].mean()
    _, opp_delta = kpi_delta(df, "is_business_opportunity")
    avg_sent = df["sentiment_score"].mean()
    _, sent_delta = kpi_delta(df, "sentiment_score")
    high_risk = df["urgency_level"].isin(["high", "critical"]).sum()

    c1.metric("Total calls", f"{len(df):,}")
    c2.metric(
        "Complaint rate",
        f"{complaint_rate:.1%}",
        delta=f"{complaint_delta:+.0f}% vs prior 7d" if complaint_delta is not None else None,
        delta_color="inverse",
    )
    c3.metric(
        "Opportunity rate",
        f"{opp_rate:.1%}",
        delta=f"{opp_delta:+.0f}% vs prior 7d" if opp_delta is not None else None,
    )
    c4.metric("High/critical urgency calls", f"{high_risk:,}")

    st.markdown("#### Weekly call volume by line of business")
    weekly_by_lob = (
        df.set_index("call_datetime").groupby("lob").resample("W-MON")["call_id"].count().reset_index(name="calls")
    )
    fig = px.bar(
        weekly_by_lob,
        x="call_datetime",
        y="calls",
        color="lob",
        category_orders={"lob": LOB_ORDER},
        color_discrete_map=LOB_COLOR,
    )
    apply_layout(fig, y_title="Calls", x_title=None)
    fig.update_layout(barmode="stack")
    st.plotly_chart(fig, width="stretch")

    oc1, oc2 = st.columns(2)
    with oc1:
        st.markdown("#### Calls by line of business")
        by_lob = df["lob"].value_counts().reindex(LOB_ORDER).fillna(0).reset_index()
        by_lob.columns = ["lob", "calls"]
        fig = px.bar(
            by_lob.sort_values("calls"),
            x="calls",
            y="lob",
            orientation="h",
            color="lob",
            color_discrete_map=LOB_COLOR,
        )
        apply_layout(fig, x_title="Calls", y_title=None, show_legend=False)
        st.plotly_chart(fig, width="stretch")

    with oc2:
        st.markdown("#### Weekly sentiment trend")
        wk = weekly_agg(df)
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=wk["period"],
                y=wk["avg_sentiment"],
                mode="lines+markers",
                line=dict(color=SEQUENTIAL_BLUE[4], width=2),
                marker=dict(size=7),
                name="Avg sentiment",
            )
        )
        fig.add_hline(y=0, line_dash="dot", line_color="#c3c2b7")
        apply_layout(fig, y_title="Sentiment score (-1 to 1)", x_title=None, show_legend=False)
        st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Complaints & Risk
# ---------------------------------------------------------------------------
with tab_complaints:
    complaints = df[df["is_complaint"]]
    st.markdown(f"**{len(complaints):,} complaint calls** ({len(complaints) / len(df):.1%} of filtered volume)")

    cc1, cc2 = st.columns([3, 2])
    with cc1:
        st.markdown("#### Top complaint categories")
        top_cat = complaints["complaint_category"].value_counts().head(10).sort_values()
        fig = px.bar(top_cat, x=top_cat.values, y=top_cat.index, orientation="h")
        fig.update_traces(marker_color=SEQUENTIAL_BLUE[4])
        apply_layout(fig, x_title="Complaints", y_title=None, show_legend=False)
        st.plotly_chart(fig, width="stretch")

    with cc2:
        st.markdown("#### Complaint urgency mix")
        urg = complaints["urgency_level"].value_counts().reindex(URGENCY_ORDER).fillna(0)
        fig = px.bar(
            urg,
            x=urg.index,
            y=urg.values,
            color=urg.index,
            color_discrete_map=URGENCY_COLOR,
            category_orders={"x": URGENCY_ORDER},
        )
        apply_layout(fig, x_title=None, y_title="Complaints", show_legend=False)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Highest-urgency calls needing follow-up")
    risk = complaints[complaints["urgency_level"].isin(["high", "critical"])].sort_values(
        "call_datetime", ascending=False
    )
    for _, row in risk.head(15).iterrows():
        icon = URGENCY_ICON.get(row["urgency_level"], "")
        with st.expander(
            f"{icon} {row['urgency_level'].upper()} · {row['lob']} · {row['complaint_category']} · "
            f"{row['call_datetime']:%Y-%m-%d %H:%M}"
        ):
            st.write(f"**Summary:** {row['summary']}")
            st.write(f"**Call ID:** {row['call_id']} · **Agent:** {row['agent_id']}")
            st.text_area("Cleaned transcript", row["cleaned_transcript"], height=140, key=f"clean_{row['call_id']}")
            st.text_area("Raw ASR transcript", row["raw_transcript"], height=140, key=f"raw_{row['call_id']}")

# ---------------------------------------------------------------------------
# Business Opportunities
# ---------------------------------------------------------------------------
with tab_opps:
    opps = df[df["is_business_opportunity"]]
    st.markdown(f"**{len(opps):,} business-opportunity signals** ({len(opps) / len(df):.1%} of filtered volume)")

    oc1, oc2 = st.columns([3, 2])
    with oc1:
        st.markdown("#### Opportunity types")
        top_opp = opps["opportunity_type"].value_counts().sort_values()
        fig = px.bar(top_opp, x=top_opp.values, y=top_opp.index, orientation="h")
        fig.update_traces(marker_color=SEQUENTIAL_BLUE[4])
        apply_layout(fig, x_title="Calls", y_title=None, show_legend=False)
        st.plotly_chart(fig, width="stretch")

    with oc2:
        st.markdown("#### Weekly opportunity volume")
        wk_opp = (
            opps.set_index("call_datetime").resample("W-MON")["call_id"].count().reset_index(name="calls")
        )
        fig = px.area(wk_opp, x="call_datetime", y="calls")
        fig.update_traces(line_color=SEQUENTIAL_BLUE[4], fillcolor=SEQUENTIAL_BLUE[1])
        apply_layout(fig, x_title=None, y_title="Calls", show_legend=False)
        st.plotly_chart(fig, width="stretch")

    st.markdown("#### Opportunity calls")
    show_cols = ["call_datetime", "lob", "opportunity_type", "summary", "agent_id"]
    st.dataframe(
        opps[show_cols].sort_values("call_datetime", ascending=False).head(200),
        width="stretch",
        hide_index=True,
    )

# ---------------------------------------------------------------------------
# Trends (WoW / MoM)
# ---------------------------------------------------------------------------
with tab_trends:
    st.markdown("#### Week-over-week")
    wk = weekly_agg(df)
    wk["complaint_wow_pct"] = wk["complaint_rate"].pct_change() * 100
    wk["opportunity_wow_pct"] = wk["opportunity_rate"].pct_change() * 100

    if len(wk) >= 2:
        biggest_wow = wk.dropna(subset=["complaint_wow_pct"]).sort_values("complaint_wow_pct", ascending=False).head(1)
        if not biggest_wow.empty and biggest_wow.iloc[0]["complaint_wow_pct"] > 15:
            r = biggest_wow.iloc[0]
            st.warning(
                f"⚠️ Largest complaint-rate spike: week of **{r['period']:%Y-%m-%d}**, "
                f"complaint rate rose **{r['complaint_wow_pct']:+.0f}%** week-over-week."
            )

    show_wk = wk.copy()
    show_wk["period"] = show_wk["period"].dt.strftime("%Y-%m-%d")
    show_wk["complaint_rate"] = (show_wk["complaint_rate"] * 100).round(1)
    show_wk["opportunity_rate"] = (show_wk["opportunity_rate"] * 100).round(1)
    show_wk["avg_sentiment"] = show_wk["avg_sentiment"].round(2)
    show_wk["complaint_wow_pct"] = show_wk["complaint_wow_pct"].round(0)
    show_wk["opportunity_wow_pct"] = show_wk["opportunity_wow_pct"].round(0)
    st.dataframe(
        show_wk.rename(
            columns={
                "period": "Week of",
                "call_count": "Calls",
                "complaint_rate": "Complaint rate %",
                "opportunity_rate": "Opportunity rate %",
                "avg_sentiment": "Avg sentiment",
                "complaint_wow_pct": "Complaint rate WoW %",
                "opportunity_wow_pct": "Opportunity rate WoW %",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Month-over-month")
    mo = monthly_agg(df)
    mo["complaint_mom_pct"] = mo["complaint_rate"].pct_change() * 100
    mo["opportunity_mom_pct"] = mo["opportunity_rate"].pct_change() * 100
    show_mo = mo.copy()
    show_mo["period"] = show_mo["period"].dt.strftime("%Y-%m")
    show_mo["complaint_rate"] = (show_mo["complaint_rate"] * 100).round(1)
    show_mo["opportunity_rate"] = (show_mo["opportunity_rate"] * 100).round(1)
    show_mo["avg_sentiment"] = show_mo["avg_sentiment"].round(2)
    show_mo["complaint_mom_pct"] = show_mo["complaint_mom_pct"].round(0)
    show_mo["opportunity_mom_pct"] = show_mo["opportunity_mom_pct"].round(0)
    st.dataframe(
        show_mo.rename(
            columns={
                "period": "Month",
                "call_count": "Calls",
                "complaint_rate": "Complaint rate %",
                "opportunity_rate": "Opportunity rate %",
                "avg_sentiment": "Avg sentiment",
                "complaint_mom_pct": "Complaint rate MoM %",
                "opportunity_mom_pct": "Opportunity rate MoM %",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown("#### Sentiment: weekly vs prior week (diverging)")
    wk_delta = wk.dropna(subset=["avg_sentiment"]).copy()
    wk_delta["sentiment_change"] = wk_delta["avg_sentiment"].diff()
    fig = go.Figure(
        go.Bar(
            x=wk_delta["period"],
            y=wk_delta["sentiment_change"],
            marker_color=[DIVERGING_POS if v >= 0 else DIVERGING_NEG for v in wk_delta["sentiment_change"].fillna(0)],
        )
    )
    fig.add_hline(y=0, line_color=DIVERGING_MID, line_width=2)
    apply_layout(fig, y_title="Change in avg sentiment vs prior week", x_title=None, show_legend=False)
    st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------------------
# Live AI Demo
# ---------------------------------------------------------------------------
with tab_live:
    st.markdown(
        "Paste a raw, noisy phone-call transcript (or load a real synthetic example below) and run it through "
        "the same Vertex AI (Gemini) extraction used to build this dashboard, live."
    )

    if "demo_transcript" not in st.session_state:
        sample = df_all[df_all["is_complaint"]].sample(1, random_state=random.randint(0, 10_000)).iloc[0]
        st.session_state["demo_transcript"] = sample["raw_transcript"]
        st.session_state["demo_lob"] = sample["lob"]

    if st.button("\U0001F3B2 Load another random example"):
        sample = df_all.sample(1, random_state=random.randint(0, 10_000)).iloc[0]
        st.session_state["demo_transcript"] = sample["raw_transcript"]
        st.session_state["demo_lob"] = sample["lob"]

    lob_choice = st.selectbox(
        "Line of business", LOB_ORDER, index=LOB_ORDER.index(st.session_state.get("demo_lob", LOB_ORDER[0]))
    )
    transcript_text = st.text_area("Raw ASR transcript", st.session_state["demo_transcript"], height=200)

    if st.button("✨ Analyze with Vertex AI (Gemini)", type="primary"):
        project = os.environ.get("GCP_PROJECT_ID")
        location = os.environ.get("GCP_LOCATION", "us-central1")
        model_name = os.environ.get("VERTEX_MODEL_NAME", "gemini-3.8-flash")

        if not project:
            st.error(
                "GCP_PROJECT_ID is not set for this app, so it can't call Vertex AI. "
                "Set it as an environment variable on the Cloud Run service (see infra/setup_gcp.sh)."
            )
        else:
            try:
                import vertexai
                from vertexai.generative_models import GenerationConfig, GenerativeModel

                from prompts import RESPONSE_SCHEMA, SYSTEM_INSTRUCTION, build_user_prompt

                with st.spinner("Calling Vertex AI..."):
                    vertexai.init(project=project, location=location)
                    model = GenerativeModel(model_name, system_instruction=SYSTEM_INSTRUCTION)
                    generation_config = GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                        temperature=0.2,
                    )
                    response = model.generate_content(
                        build_user_prompt(lob_choice, transcript_text), generation_config=generation_config
                    )
                    import json

                    result = json.loads(response.text)

                r1, r2 = st.columns(2)
                with r1:
                    st.markdown("**Cleaned transcript**")
                    st.info(result["cleaned_transcript"])
                    st.markdown("**Summary**")
                    st.write(result["summary"])
                with r2:
                    st.metric("Sentiment", result["sentiment"], delta=f"{result['sentiment_score']:+.2f}")
                    st.write(f"**Complaint:** {'Yes -- ' + result['complaint_category'] if result['is_complaint'] else 'No'}")
                    st.write(
                        f"**Opportunity:** "
                        f"{'Yes -- ' + result['opportunity_type'] if result['is_business_opportunity'] else 'No'}"
                    )
                    icon = URGENCY_ICON.get(result["urgency_level"], "")
                    st.write(f"**Urgency:** {icon} {result['urgency_level'].upper()}")
                    st.write(f"**Key topics:** {', '.join(result['key_topics'])}")
            except Exception as exc:  # noqa: BLE001
                st.error(
                    "Couldn't reach Vertex AI. Check that GCP_PROJECT_ID/GCP_LOCATION are correct, the Vertex AI "
                    f"API is enabled, and this service's identity has the Vertex AI User role.\n\nDetails: {exc}"
                )

# ---------------------------------------------------------------------------
# Methodology
# ---------------------------------------------------------------------------
with tab_method:
    st.markdown(
        f"""
### How this demo works

1. **Synthetic data generation** (`data_gen/`) -- fictional {BANK_NAME} calls across 6 lines of
   business are generated with realistic dialogue structure, then run through an ASR-noise
   simulator (dropped words, misheard homophones, filler words, missing punctuation,
   `[inaudible]`/`[crosstalk]` artifacts) so they read like real low-quality phone transcripts.
2. **AI extraction** (`pipeline/vertex_enrich.py`) -- each noisy transcript is sent to
   **Vertex AI (Gemini)** with a structured JSON schema, asking it to reconstruct a clean
   transcript, summarize the call, and classify sentiment, complaints, business
   opportunities, urgency, and topics.
3. **Warehouse** -- enriched records land in **BigQuery** (`voc_analytics.enriched_calls`),
   the single source of truth for every chart in this app.
4. **This dashboard** -- a Streamlit app on **Cloud Run**, deployed by **GitHub Actions**
   using Workload Identity Federation (no long-lived keys).
        """
    )

    if "scenario_type" in df_all.columns:
        st.markdown("#### AI extraction accuracy vs. known scenario intent")
        st.caption(
            "Each synthetic call was generated from a known scenario (complaint / opportunity / neutral). "
            "This compares that ground truth to what the AI extraction actually classified -- a sanity check "
            "on extraction quality, not something a real production dataset would have."
        )
        comp_acc = (df_all["is_complaint"] == (df_all["scenario_type"] == "complaint")).mean()
        opp_acc = (df_all["is_business_opportunity"] == (df_all["scenario_type"] == "opportunity")).mean()
        m1, m2 = st.columns(2)
        m1.metric("Complaint-detection agreement", f"{comp_acc:.1%}")
        m2.metric("Opportunity-detection agreement", f"{opp_acc:.1%}")

    st.markdown(
        """
#### Notes for this demo
- All customer names, account numbers, and call content are synthetic. No real customer
  or account data is used anywhere in this repository.
- The bank name used throughout ("Meridian Bank") is fictional; the LOB structure mirrors
  standard retail-banking lines of business for illustration.
        """
    )
