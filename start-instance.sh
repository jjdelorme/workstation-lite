#!/usr/bin/env bash
set -euo pipefail

INSTANCE_NAME="${1:-vs-codium29-instance}"
REGION="${REGION:-us-east4}"
PROJECT="${PROJECT:-jasondel-cloudrun10}"

echo "Connecting to Cloud Run instance '${INSTANCE_NAME}' in ${REGION} (project: ${PROJECT})..."
if ! gcloud alpha run instances ssh "${INSTANCE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT}"; then
  echo "SSH failed (instance may be stopped). Starting '${INSTANCE_NAME}'..."
  gcloud alpha run instances start "${INSTANCE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT}"

  echo "Connecting via SSH..."
  gcloud alpha run instances ssh "${INSTANCE_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT}"
fi
