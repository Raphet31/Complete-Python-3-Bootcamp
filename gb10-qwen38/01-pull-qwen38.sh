#!/usr/bin/env bash
# 01-pull-qwen38.sh -- Descarga Qwen3.8-27B en la GB10.
#
# NO DESTRUCTIVO: solo descarga. No borra, no repunta, no toca el modelo
# viejo. Despues de esto tienes los dos modelos conviviendo.
#
# Uso:  ./01-pull-qwen38.sh [--gguf] [--with-vision]
#       --gguf         usa el build GGUF en vez de NVFP4 (si NVFP4 falla)
#       --with-vision  descarga tambien el proyector mmproj
#       --yes          no preguntar nada (para runs no interactivos)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# shellcheck source=models.conf
source ./models.conf

USE_GGUF=0
WITH_VISION=0
ASSUME_YES=0
for arg in "$@"; do
    case "$arg" in
        --gguf)        USE_GGUF=1 ;;
        --with-vision) WITH_VISION=1 ;;
        --yes|-y)      ASSUME_YES=1 ;;
        *) echo "Argumento desconocido: $arg" >&2; exit 2 ;;
    esac
done

TARGET="$NEW_MODEL"
[[ $USE_GGUF -eq 1 ]] && TARGET="$NEW_MODEL_GGUF"

echo "==> Modelo a descargar: $TARGET"

# --- Prechequeos ----------------------------------------------------------
command -v ollama >/dev/null 2>&1 || {
    echo "ERROR: ollama no esta en PATH." >&2
    echo "Instalalo con:  curl -fsSL https://ollama.com/install.sh | sh" >&2
    exit 1
}

if ! curl -fsS --max-time 5 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1; then
    echo "ERROR: el daemon de ollama no responde en $OLLAMA_HOST" >&2
    echo "Arrancalo con:  sudo systemctl start ollama" >&2
    exit 1
fi

# Espacio libre: NVFP4 27B ~16GB, GGUF Q4_K_M ~17.1GB. Pedimos 40GB de holgura
# para descarga + descompresion + KV cache.
AVAIL_GB="$(df -BG --output=avail "${HOME}" 2>/dev/null | tail -1 | tr -dc '0-9' || echo 0)"
if [[ -n "$AVAIL_GB" && "$AVAIL_GB" -lt 40 ]]; then
    echo "AVISO: solo ${AVAIL_GB}GB libres. Se recomiendan >=40GB" \
         "(~17GB de pesos + descompresion + KV cache)." >&2
    if [[ $ASSUME_YES -eq 1 ]]; then
        echo "  --yes activo: continuando de todos modos." >&2
    elif [[ ! -t 0 ]]; then
        echo "ABORTADO: sin terminal interactiva para confirmar." >&2
        echo "  Libera espacio, o re-corre con --yes para forzar." >&2
        exit 1
    else
        read -rp "Continuar igual? [y/N] " ok
        if [[ "$ok" != "y" && "$ok" != "Y" ]]; then
            echo "ABORTADO por el usuario. No se descargo nada." >&2
            exit 1
        fi
    fi
fi

# --- Ya lo tenemos? -------------------------------------------------------
if ollama list 2>/dev/null | awk '{print $1}' | grep -qx "$TARGET"; then
    echo "==> $TARGET ya esta descargado. Nada que hacer."
else
    echo "==> Descargando (esto tarda: ~16-18GB)..."
    if ! ollama pull "$TARGET"; then
        echo >&2
        echo "ERROR: fallo el pull de $TARGET" >&2
        if [[ $USE_GGUF -eq 0 ]]; then
            echo "Si el tag NVFP4 no existe en tu version de ollama, reintenta con:" >&2
            echo "    ./01-pull-qwen38.sh --gguf" >&2
        fi
        exit 1
    fi
fi

# --- Proyector de vision --------------------------------------------------
if [[ $WITH_VISION -eq 1 ]]; then
    if [[ -z "$NEW_MODEL_MMPROJ" ]]; then
        echo "==> AVISO: pediste --with-vision pero NEW_MODEL_MMPROJ esta vacio"
        echo "    en models.conf. Sin el proyector, las imagenes fallan EN SILENCIO:"
        echo "    el modelo responde, pero ignorando la imagen. Rellenalo antes."
    else
        echo "==> Descargando proyector: $NEW_MODEL_MMPROJ"
        ollama pull "$NEW_MODEL_MMPROJ"
    fi
fi

# --- Humo ------------------------------------------------------------------
echo; echo "==> Prueba de humo..."
SMOKE="$(curl -fsS --max-time 180 "${OLLAMA_HOST}/api/generate" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${TARGET}\",\"prompt\":\"Responde unicamente con la palabra: OK\",\"stream\":false}" \
    2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("response","").strip())' 2>/dev/null || echo "")"

if [[ -n "$SMOKE" ]]; then
    echo "    Respuesta: $SMOKE"
    echo "    El modelo carga y responde."
else
    echo "    AVISO: la prueba de humo no devolvio texto. Revisa a mano:" >&2
    echo "      ollama run $TARGET" >&2
fi

# Persistimos que variante quedo activa, para que 02 use la correcta.
if [[ "$TARGET" != "$NEW_MODEL" ]]; then
    sed -i "s|^NEW_MODEL=.*|NEW_MODEL=\"$TARGET\"|" models.conf
    echo; echo "==> models.conf actualizado: NEW_MODEL=$TARGET"
fi

echo
echo "-------------------------------------------------------------"
echo "LISTO. Los dos modelos conviven ahora; no se borro nada."
echo
echo "SIGUIENTE PASO -- y hazlo en este orden:"
echo "  1. ./03-ab-eval.py --prompts mis-tareas.txt   <-- MIDE PRIMERO"
echo "  2. ./02-switch-model.sh                        <-- cambia solo si gana"
echo "-------------------------------------------------------------"
