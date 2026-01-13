#!/usr/bin/env bash
set -euo pipefail

# CI integration test runner
# 1. Start docker compose
# 2. Wait for gateway health
# 3. Run orchestrator-contained abuse tests
# 4. Run live validation harness
# 5. Tear down (always)

GATEWAY_URL=${GATEWAY_URL:-http://localhost:9001}
ORCHESTRATOR_CONTAINER=${ORCHESTRATOR_CONTAINER:-ct-orchestrator}
CT_API_KEY=${CT_API_KEY:-${CT_TEST_KEY:-}}

if [ -z "$CT_API_KEY" ]; then
  echo "ERROR: CT_API_KEY or CT_TEST_KEY must be set in environment"
  exit 1
fi

export CT_API_KEY="$CT_API_KEY"

echo "Starting docker compose..."
docker compose -f docker-compose.yml up -d --build

# Wait for gateway health
echo "Waiting for gateway health at $GATEWAY_URL/health ..."
for i in {1..60}; do
  if curl -sSf "$GATEWAY_URL/health" >/dev/null 2>&1; then
    echo "Gateway healthy"
    break
  fi
  sleep 1
  echo -n "."
done

# Run abuse tests inside orchestrator container (contains required deps)
echo "Running in-container abuse tests (test_abuse_cases.py)..."
docker exec "$ORCHESTRATOR_CONTAINER" python /app/ct-dev/test_abuse_cases.py

# Install httpx in runner and run live deployment validation
echo "Running live validation harness (validate_live_deployment.py)..."
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install httpx
python ct-dev/validate_live_deployment.py --gateway-url "$GATEWAY_URL" --api-key "$CT_API_KEY"

# Tear down
echo "Tearing down docker compose..."
docker compose -f docker-compose.yml down --volumes --remove-orphans

echo "CI integration tests completed successfully."