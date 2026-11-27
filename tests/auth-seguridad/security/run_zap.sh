#!/usr/bin/env bash
# =============================================
# Escaneo pasivo de OWASP ZAP contra el ambiente QA local
# ---------------------------------------------
# zap-baseline.py recorre el sitio con el spider y analiza las respuestas de forma
# pasiva: no envia ataques. Solo contra el ambiente QA local, nunca contra terceros.
# Uso, desde una terminal de WSL en la raiz del repo, con el ambiente QA arriba:
#   bash tests/auth-seguridad/security/run_zap.sh http://127.0.0.1:5173 zap-frontend
#   bash tests/auth-seguridad/security/run_zap.sh http://127.0.0.1:8000/docs zap-api
# Deja en reports/zap/ el reporte HTML, JSON y Markdown, y la salida de consola.
set -euo pipefail

# =============================================
# Variables
# ---------------------------------------------
ZAP_IMAGE="ghcr.io/zaproxy/zaproxy:stable"
TARGET_URL="${1:?Missing target URL, for example http://127.0.0.1:5173}"
RUN_LABEL="${2:?Missing run label, for example zap-frontend}"
REPO_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
REPORTS_DIR="$REPO_DIR/reports/zap"

# =============================================
# Validacion del objetivo
# ---------------------------------------------
# Solo se permite escanear el ambiente QA local
case "$TARGET_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *)
    echo "Refusing to scan $TARGET_URL: only the local QA environment is allowed" >&2
    exit 1
    ;;
esac

# =============================================
# Ejecucion
# ---------------------------------------------
# --network host: el contenedor ve los puertos que el compose publica en 127.0.0.1
# -I: las advertencias no hacen fallar el comando; se analizan en el reporte
mkdir -p "$REPORTS_DIR"
chmod a+w "$REPORTS_DIR"
docker run --rm \
  --network host \
  -v "$REPORTS_DIR:/zap/wrk:rw" \
  "$ZAP_IMAGE" zap-baseline.py \
  -t "$TARGET_URL" \
  -r "$RUN_LABEL.html" \
  -J "$RUN_LABEL.json" \
  -w "$RUN_LABEL.md" \
  -I \
  2>&1 | tee "$REPORTS_DIR/$RUN_LABEL.txt"
echo "Reports saved in reports/zap/$RUN_LABEL.*"
