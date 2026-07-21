#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVER_HOST="0.0.0.0"
SERVER_PORT="18062"

export SPATIAL_SKILL_GROWTH_BASE_URL="http://127.0.0.1:8862/v1"
export SPATIAL_SKILL_GROWTH_API_RUN_ID="api_server_62"

cd "${PROJECT_ROOT}"
exec python -m uvicorn server.anomaly_detection_server:app \
    --host "${SERVER_HOST}" \
    --port "${SERVER_PORT}" \
    --workers 1
