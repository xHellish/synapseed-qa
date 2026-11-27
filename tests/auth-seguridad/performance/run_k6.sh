#!/usr/bin/env bash
# =============================================
# Corre un escenario de k6 contra el ambiente QA local
# ---------------------------------------------
# Uso, desde una terminal de WSL en la raiz del repo:
#   bash tests/auth-seguridad/performance/run_k6.sh auth_read_load.js perf-01
#   bash tests/auth-seguridad/performance/run_k6.sh recommendation_load.js perf-02-delay-0
# Deja en reports/k6/ la salida de consola (<etiqueta>.txt) y el resumen (<etiqueta>.json).
set -euo pipefail

# =============================================
# Variables
# ---------------------------------------------
K6_IMAGE="grafana/k6:1.0.0"
QA_NETWORK="synapseed-qa_default"
SCRIPT_NAME="${1:?Missing k6 script name, for example auth_read_load.js}"
RUN_LABEL="${2:?Missing run label, for example perf-01}"
REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
REPORTS_DIR="$REPO_DIR/reports/k6"

# =============================================
# Ejecucion
# ---------------------------------------------
# El contenedor se une a la red del compose QA para llegar al backend por nombre
mkdir -p "$REPORTS_DIR"
set +e
docker run --rm \
  --network "$QA_NETWORK" \
  -v "$REPO_DIR/tests/auth-seguridad/performance:/scripts:ro" \
  -v "$REPORTS_DIR:/reports" \
  "$K6_IMAGE" run --summary-export "/reports/$RUN_LABEL.json" "/scripts/$SCRIPT_NAME" \
  2>&1 | tee "$REPORTS_DIR/$RUN_LABEL.txt"
K6_EXIT_CODE="${PIPESTATUS[0]}"
set -e

# k6 sale con 99 cuando algun umbral no se cumple; se informa sin ocultarlo
if [ "$K6_EXIT_CODE" -eq 99 ]; then
  echo "Thresholds failed for $RUN_LABEL (k6 exit code 99)"
elif [ "$K6_EXIT_CODE" -ne 0 ]; then
  echo "k6 failed for $RUN_LABEL with exit code $K6_EXIT_CODE" >&2
  exit "$K6_EXIT_CODE"
fi
echo "Reports saved in reports/k6/$RUN_LABEL.txt and reports/k6/$RUN_LABEL.json"
