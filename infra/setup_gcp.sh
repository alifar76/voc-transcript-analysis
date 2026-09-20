#!/usr/bin/env bash
# One-time GCP setup for the VOC dashboard demo, project: voc-dane.
#
# Run this in Cloud Shell (https://console.cloud.google.com -> Cloud Shell)
# with `voc-dane` as the active project. It is safe to re-run: most `create`
# commands will just print an "already exists" error you can ignore if you
# run this a second time.
#
# What it sets up:
#   1. Required APIs (Cloud Run, Vertex AI, BigQuery, Artifact Registry, Cloud Build)
#   2. An override of the "Domain Restricted Sharing" org policy for this
#      project only, if one exists, so the deployed dashboard can actually be
#      made public (harmless no-op if there's no such policy)
#   3. A runtime service account for the Cloud Run app (Vertex AI + BigQuery read access)
#   4. A deployer service account for GitHub Actions (Cloud Run + Cloud Build access)
#   5. Build permissions for the default Compute Engine SA (Cloud Build's own
#      identity for `gcloud run deploy --source` builds)
#   6. Workload Identity Federation so GitHub Actions can authenticate as that
#      deployer service account WITHOUT a long-lived JSON key ever leaving GCP
#   7. The BigQuery dataset the enrichment pipeline writes into
#
# At the end it prints the values you paste into the GitHub repo's
# Settings -> Secrets and variables -> Actions -> Variables tab.

set -euo pipefail

PROJECT_ID="voc-dane"
REGION="us-central1"          # Cloud Run deploy region
VERTEX_LOCATION="us"          # Vertex AI (Gemini) multi-region: "us" or "eu", NOT a region like us-central1
BQ_LOCATION="US"
GITHUB_REPO="alifar76/voc-transcript-analysis"   # owner/repo -- must match exactly

DEPLOYER_SA_NAME="github-deployer"
RUNTIME_SA_NAME="voc-app-runtime"
POOL_ID="github-pool"
PROVIDER_ID="github-provider"
BQ_DATASET="voc_analytics"

echo "==> Setting active project to ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}"

echo "==> Enabling required APIs (this can take a minute)"
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  bigquery.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  iamcredentials.googleapis.com \
  iam.googleapis.com \
  sts.googleapis.com \
  storage.googleapis.com \
  orgpolicy.googleapis.com

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
echo "==> Project number: ${PROJECT_NUMBER}"

# If this project sits under a Google Cloud Organization, it likely inherits
# a "Domain Restricted Sharing" policy that blocks granting allUsers access
# to anything -- which would otherwise silently break `--allow-unauthenticated`
# on the Cloud Run deploy (the deploy succeeds, but the service stays 403 to
# the public). Override it for this project only, so the demo dashboard can
# actually be reached without anyone signing in. This is a no-op if the
# project has no organization (the command just fails harmlessly).
echo "==> Allowing public (unauthenticated) access for this project, if an org policy would otherwise block it"
cat > /tmp/voc-dane-orgpolicy.yaml <<EOF
name: projects/${PROJECT_ID}/policies/iam.allowedPolicyMemberDomains
spec:
  rules:
  - allowAll: true
EOF
gcloud org-policies set-policy /tmp/voc-dane-orgpolicy.yaml 2>/dev/null || \
  echo "    (no organization policy to override here -- that's fine, skipping)"
rm -f /tmp/voc-dane-orgpolicy.yaml

# IAM can take a few seconds to propagate a newly created service account, so
# a role-binding command run immediately after `create` can fail with a false
# "does not exist". Wait until the SA is actually visible before using it.
wait_for_service_account() {
  local email="$1"
  local tries=0
  until gcloud iam service-accounts describe "${email}" >/dev/null 2>&1; do
    tries=$((tries + 1))
    if [ "${tries}" -ge 20 ]; then
      echo "Timed out waiting for service account ${email} to become visible." >&2
      exit 1
    fi
    echo "    ...waiting for ${email} to propagate (${tries}/20)"
    sleep 3
  done
}

# ---------------------------------------------------------------------------
# 1. Runtime service account -- identity the deployed Cloud Run app runs as.
#    Needs to call Vertex AI (Live AI Demo tab), read BigQuery (dashboards),
#    and write BigQuery (the login/access-log table).
# ---------------------------------------------------------------------------
echo "==> Creating runtime service account: ${RUNTIME_SA_NAME}"
gcloud iam service-accounts create "${RUNTIME_SA_NAME}" \
  --display-name="VOC dashboard Cloud Run runtime identity" || true

RUNTIME_SA_EMAIL="${RUNTIME_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
wait_for_service_account "${RUNTIME_SA_EMAIL}"

for role in roles/aiplatform.user roles/bigquery.dataEditor roles/bigquery.jobUser; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${RUNTIME_SA_EMAIL}" \
    --role="${role}" \
    --condition=None \
    --quiet
done

# ---------------------------------------------------------------------------
# 2. Deployer service account -- identity GitHub Actions impersonates via WIF
#    to build (Cloud Build) and deploy (Cloud Run) the dashboard.
# ---------------------------------------------------------------------------
echo "==> Creating deployer service account: ${DEPLOYER_SA_NAME}"
gcloud iam service-accounts create "${DEPLOYER_SA_NAME}" \
  --display-name="GitHub Actions deployer for VOC dashboard" || true

DEPLOYER_SA_EMAIL="${DEPLOYER_SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
wait_for_service_account "${DEPLOYER_SA_EMAIL}"

for role in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.admin roles/storage.admin roles/iam.serviceAccountUser; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEPLOYER_SA_EMAIL}" \
    --role="${role}" \
    --condition=None \
    --quiet
done
# roles/iam.serviceAccountUser at the project level lets the deployer act as
# any service account in the project -- both the runtime SA it deploys Cloud
# Run to run as, and the default Compute Engine service account that Cloud
# Build uses under the hood to actually build the container image.

# ---------------------------------------------------------------------------
# 3. Default Compute Engine service account -- this is the identity Cloud
#    Build itself runs the actual build job as for `gcloud run deploy
#    --source` (separate from the deployer SA, which just kicks the deploy
#    off). Newer GCP projects no longer auto-grant this SA the old broad
#    "Editor" role, so it needs these explicitly or the build can't read its
#    own uploaded source, push the built image, or write build logs.
# ---------------------------------------------------------------------------
COMPUTE_SA_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "==> Granting build permissions to default Compute Engine SA: ${COMPUTE_SA_EMAIL}"
for role in roles/storage.objectViewer roles/artifactregistry.writer roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${COMPUTE_SA_EMAIL}" \
    --role="${role}" \
    --condition=None \
    --quiet
done

# ---------------------------------------------------------------------------
# 4. Workload Identity Federation: let GitHub Actions authenticate as the
#    deployer SA using short-lived tokens -- no JSON key ever created.
# ---------------------------------------------------------------------------
echo "==> Creating Workload Identity Pool: ${POOL_ID}"
gcloud iam workload-identity-pools create "${POOL_ID}" \
  --location="global" \
  --display-name="GitHub Actions pool" || true

echo "==> Creating Workload Identity Provider: ${PROVIDER_ID}"
gcloud iam workload-identity-pools providers create-oidc "${PROVIDER_ID}" \
  --location="global" \
  --workload-identity-pool="${POOL_ID}" \
  --display-name="GitHub provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='${GITHUB_REPO}'" || true

gcloud iam service-accounts add-iam-policy-binding "${DEPLOYER_SA_EMAIL}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${GITHUB_REPO}" \
  --quiet

# ---------------------------------------------------------------------------
# 5. BigQuery dataset the enrichment pipeline writes into.
# ---------------------------------------------------------------------------
echo "==> Creating BigQuery dataset: ${BQ_DATASET}"
bq --location="${BQ_LOCATION}" mk --dataset "${PROJECT_ID}:${BQ_DATASET}" || true

# ---------------------------------------------------------------------------
# Done. These go into GitHub: Settings -> Secrets and variables -> Actions ->
# Variables tab (they are identifiers, not secrets, but Variables is the
# right place for them since the workflow reads them via the `vars` context).
# ---------------------------------------------------------------------------
cat <<EOF

============================================================
One-time GCP setup complete. Add these as GitHub repo
Variables (Settings > Secrets and variables > Actions > Variables):

GCP_PROJECT_ID=${PROJECT_ID}
GCP_REGION=${REGION}
GCP_DEPLOYER_SA_EMAIL=${DEPLOYER_SA_EMAIL}
GCP_RUNTIME_SA_EMAIL=${RUNTIME_SA_EMAIL}
GCP_WORKLOAD_IDENTITY_PROVIDER=projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}
============================================================

Next steps:
  1. Add the 5 values above as GitHub repo Variables.
  2. Populate BigQuery with real AI-enriched data (from Cloud Shell, or any
     machine with 'gcloud auth application-default login' run against this
     project):
       python3 -m venv .venv && source .venv/bin/activate
       pip install -r requirements.txt
       python data_gen/generate_transcripts.py --output data/synthetic_transcripts.csv
       python pipeline/vertex_enrich.py \\
         --input data/synthetic_transcripts.csv \\
         --output data/enriched_calls.parquet \\
         --project ${PROJECT_ID} --location ${VERTEX_LOCATION} \\
         --load-bigquery --bq-dataset ${BQ_DATASET} --bq-table enriched_calls
  3. Merge/push to the 'main' branch -- GitHub Actions will build and deploy
     the dashboard to Cloud Run automatically.
EOF
