# Meridian Bank — Voice of Customer (VOC) Intelligence

A demo of an AI-driven Voice-of-Customer pipeline for a retail bank contact
center: synthetic, ASR-quality-degraded call transcripts → **Vertex AI
(Gemini)** structured extraction → **BigQuery** → a **Streamlit** dashboard
on **Cloud Run**, deployed by **GitHub Actions** via Workload Identity
Federation.

> **Everything in this repo is synthetic.** Bank name ("Meridian Bank"),
> customers, agents, account numbers, and call content are all fictional and
> generated for demo purposes. No real customer or account data is used
> anywhere. The line-of-business structure mirrors standard retail-banking
> categories for illustration only.

## Architecture

```
data_gen/generate_transcripts.py
        │  synthetic calls across 6 LOBs, ASR noise injected
        ▼
data/synthetic_transcripts.csv
        │
        ▼
pipeline/vertex_enrich.py  ───calls───▶  Vertex AI (Gemini)
        │  structured JSON: sentiment, complaint, opportunity,
        │  urgency, topics, cleaned transcript, summary
        ▼
BigQuery: voc_analytics.enriched_calls
        │
        ▼
app/streamlit_app.py  (Cloud Run)
   Overview · Complaints & Risk · Business Opportunities ·
   Trends (WoW/MoM) · Live AI Demo · Methodology
```

CI/CD: pushing to `main` triggers `.github/workflows/deploy.yml`, which
authenticates to GCP via **Workload Identity Federation** (no service-account
keys stored anywhere) and deploys the dashboard to Cloud Run, building the
container from source with Cloud Build.

## Repo layout

| Path | What it is |
|---|---|
| `data_gen/` | Synthetic transcript generator + ASR-noise simulator |
| `pipeline/` | Vertex AI enrichment (`vertex_enrich.py`), BigQuery loader, and an offline rule-based `simulate_enrich.py` used only for local dev/fallback data |
| `app/` | The Streamlit dashboard |
| `infra/setup_gcp.sh` | One-time GCP setup (run once from Cloud Shell) |
| `.github/workflows/deploy.yml` | CI/CD: build + deploy to Cloud Run on push to `main` |
| `data/` | Bundled sample dataset (so the dashboard always has something to show, even before BigQuery is populated) |

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. Generate synthetic transcripts
python data_gen/generate_transcripts.py --output data/synthetic_transcripts.csv

# 2a. Offline placeholder enrichment (no GCP needed, rule-based, fast)
python pipeline/simulate_enrich.py \
  --input data/synthetic_transcripts.csv --output data/enriched_calls.parquet

# 2b. OR real Vertex AI enrichment (needs `gcloud auth application-default login`
#     and a GCP project with the Vertex AI API enabled)
python pipeline/vertex_enrich.py \
  --input data/synthetic_transcripts.csv --output data/enriched_calls.parquet \
  --project voc-dane --location us-central1

# 3. Run the dashboard
streamlit run app/streamlit_app.py
```

With no `GCP_PROJECT_ID` env var set, the dashboard reads the local
`data/enriched_calls.parquet` snapshot. Set `GCP_PROJECT_ID` (and optionally
`BQ_DATASET`/`BQ_TABLE`) to read live from BigQuery instead — it falls back
to the local snapshot automatically if BigQuery isn't reachable.

The **Live AI Demo** tab always calls Vertex AI directly (it's the point of
that tab), so it needs `GCP_PROJECT_ID` set and Vertex AI API access from
wherever the app is running.

## Deploying to GCP (project: `voc-dane`)

### One-time setup (you run this, in Cloud Shell)

Open Cloud Shell on the `voc-dane` project and run:

```bash
git clone https://github.com/alifar76/voc-transcript-analysis.git
cd voc-transcript-analysis
bash infra/setup_gcp.sh
```

This enables the required APIs, creates two service accounts (one for the
Cloud Run app itself, one for GitHub Actions to deploy with), and sets up
Workload Identity Federation so GitHub Actions never needs a downloaded
service-account key. It prints five values at the end — add them as
**GitHub repo Variables**: Settings → Secrets and variables → Actions →
Variables tab.

| Variable | What it is |
|---|---|
| `GCP_PROJECT_ID` | `voc-dane` |
| `GCP_REGION` | Cloud Run region, e.g. `us-central1` |
| `GCP_DEPLOYER_SA_EMAIL` | Service account GitHub Actions impersonates to deploy |
| `GCP_RUNTIME_SA_EMAIL` | Service account the deployed dashboard runs as |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | The WIF provider resource name |

### Populate BigQuery with real AI-enriched data

Run once (also from Cloud Shell, or any machine authenticated to the
project) — this is what actually calls Gemini and is the part worth showing
Dane is real, not canned:

```bash
python pipeline/vertex_enrich.py \
  --input data/synthetic_transcripts.csv \
  --output data/enriched_calls.parquet \
  --project voc-dane --location us-central1 \
  --load-bigquery --bq-dataset voc_analytics --bq-table enriched_calls
```

### Deploy

Push (or merge a PR) to `main`. GitHub Actions builds the container from
source and deploys it to Cloud Run automatically. Re-running the workflow
(Actions tab → "Run workflow") re-deploys on demand.

## Demo script

1. **Overview** — call volume by LOB, complaint/opportunity rates, sentiment
   trend at a glance.
2. **Complaints & Risk** — top complaint categories, urgency mix, drill into
   a real (synthetic) high-urgency call: raw ASR transcript next to what
   Gemini reconstructed and extracted.
3. **Trends (WoW/MoM)** — the dataset has a deliberate ~2-week mobile-app-outage
   complaint spike and a rising high-yield-savings/business-line-of-credit
   opportunity trend baked in, so the "trends actually mean something" story
   tells itself.
4. **Live AI Demo** — paste (or randomly load) a raw noisy transcript and run
   it through Gemini live, on stage. This is the "look, it's not a canned
   screenshot" moment.
5. **Methodology** — the end-to-end architecture, plus an AI-extraction
   accuracy check against the known synthetic scenario.

## Notes on scope

- The bundled `data/enriched_calls.parquet` was produced by
  `pipeline/simulate_enrich.py`, a rule-based stand-in, so the repo and local
  dev never depend on live GCP credentials. Run `pipeline/vertex_enrich.py`
  against a real project to get genuine Gemini-generated labels, cleaned
  transcripts, and summaries into BigQuery.
- `gemini-2.0-flash-001` is the default model; if a newer Gemini model is GA
  in your project/region by the time you deploy, override it via
  `VERTEX_MODEL_NAME`.
