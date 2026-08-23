#!/usr/bin/env bash
# 00-inventory.sh -- Inventario de solo lectura de la GB10.
#
# NO modifica nada. Averigua que runtime hay, que modelo se esta usando hoy,
# y que archivos del sistema lo mencionan, para saber que hay que repuntar.
#
# Uso:  ./00-inventory.sh [--scan-home]
#       --scan-home  ademas rastrea $HOME buscando configs que nombren el
#                    modelo viejo (mas lento, pero es lo que responde
#                    "actualizar TODO lo que tenemos con ese modelo").

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# shellcheck source=models.conf
source ./models.conf

SCAN_HOME=0
[[ "${1:-}" == "--scan-home" ]] && SCAN_HOME=1

REPORT="inventory-report.txt"
exec > >(tee "$REPORT") 2>&1

hr() { printf '%s\n' "-------------------------------------------------------------"; }

hr; echo "INVENTARIO GB10  --  $(date -u '+%Y-%m-%d %H:%M:%SZ')"; hr

# --- Hardware -------------------------------------------------------------
echo; echo "== HARDWARE =="
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,compute_cap,memory.total,driver_version \
               --format=csv,noheader 2>/dev/null \
        || echo "  nvidia-smi presente pero la query fallo"

    CAP="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d ' ')"
    case "$CAP" in
        12.1|12.*) echo "  -> Blackwell detectado (sm_${CAP//./}). NVFP4 soportado: usar $NEW_MODEL" ;;
        "")        echo "  -> No se pudo leer compute capability." ;;
        *)         echo "  -> AVISO: compute_cap=$CAP no es Blackwell. NVFP4 puede no funcionar;" \
                        "considerar $NEW_MODEL_GGUF" ;;
    esac
else
    echo "  nvidia-smi NO encontrado. Esto no parece la GB10."
    echo "  Los scripts 01/02 asumen que corres esto EN el DGX Spark."
fi

echo; echo "  Memoria del sistema (el GB10 es unificada, ~128GB):"
free -h 2>/dev/null | sed 's/^/    /' || echo "    free(1) no disponible"

echo; echo "  Espacio en disco para pesos:"
df -h "${HOME}" 2>/dev/null | sed 's/^/    /' || true

# --- Runtimes -------------------------------------------------------------
echo; echo "== RUNTIMES DE INFERENCIA =="
FOUND_RUNTIME=0
for rt in ollama vllm llama-server llama-cli lms; do
    if command -v "$rt" >/dev/null 2>&1; then
        FOUND_RUNTIME=1
        printf '  %-14s %s\n' "$rt" "$(command -v "$rt")"
        case "$rt" in
            ollama) ollama --version 2>/dev/null | sed 's/^/                 /' || true ;;
            vllm)   vllm --version   2>/dev/null | sed 's/^/                 /' || true ;;
        esac
    fi
done
[[ $FOUND_RUNTIME -eq 0 ]] && echo "  Ninguno encontrado en PATH."

# --- Modelos instalados ---------------------------------------------------
echo; echo "== MODELOS YA INSTALADOS =="
if command -v ollama >/dev/null 2>&1; then
    if ollama list 2>/dev/null; then :; else
        echo "  'ollama list' fallo. El daemon puede estar caido:  systemctl status ollama"
    fi
else
    echo "  ollama no instalado; no puedo enumerar modelos."
fi

# --- Que se esta usando AHORA --------------------------------------------
echo; echo "== MODELO EN USO AHORA =="
if command -v ollama >/dev/null 2>&1 && ollama ps 2>/dev/null | grep -qv '^NAME'; then
    ollama ps 2>/dev/null | sed 's/^/  /'
    echo
    echo "  ^ Si algo aparece cargado arriba, ESE es tu OLD_MODEL."
    echo "    Ponlo en models.conf -> OLD_MODEL=\"...\""
else
    echo "  Nada cargado en memoria ahora mismo."
    echo "  Mira la lista de arriba y elige a mano el OLD_MODEL."
fi

# --- El alias ya existe? --------------------------------------------------
echo; echo "== ESTADO DEL ALIAS '$ALIAS' =="
if command -v ollama >/dev/null 2>&1 && ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qE "^${ALIAS}(:latest)?$"; then
    echo "  El alias YA existe. 02-switch-model.sh lo repuntara (con backup)."
else
    echo "  El alias no existe todavia. 02-switch-model.sh lo creara."
    echo "  Tras crearlo, apunta tus apps a '$ALIAS' y no vuelvas a tocarlas."
fi

# --- Configs que nombran el modelo viejo ---------------------------------
echo; echo "== CONFIGS QUE MENCIONAN UN MODELO =="
if [[ -z "$OLD_MODEL" ]]; then
    echo "  OLD_MODEL vacio en models.conf -- rellenalo y re-corre para el rastreo dirigido."
    PATTERN='ollama|qwen|llama[0-9.:-]|mistral|deepseek|gemma|phi-|MODEL_NAME|OLLAMA_MODEL'
    echo "  Usando patron generico mientras tanto."
else
    PATTERN="$(printf '%s' "$OLD_MODEL" | sed 's/[.[\*^$()+?{|]/\\&/g')"
    echo "  Buscando referencias a: $OLD_MODEL"
fi

SEARCH_PATHS=( /etc/systemd/system /etc/ollama )
[[ $SCAN_HOME -eq 1 ]] && SEARCH_PATHS+=( "$HOME" )

echo
for p in "${SEARCH_PATHS[@]}"; do
    [[ -d "$p" ]] || continue
    echo "  --- $p ---"
    HITS="$(grep -rIl --exclude-dir={.git,node_modules,.venv,venv,__pycache__,.cache,blobs,models} \
             -E "$PATTERN" "$p" 2>/dev/null | head -40 || true)"
    if [[ -n "$HITS" ]]; then
        printf '%s\n' "$HITS" | sed 's/^/    /'
    else
        echo "    (sin coincidencias)"
    fi
done

[[ $SCAN_HOME -eq 0 ]] && { echo; echo "  Nota: re-corre con --scan-home para rastrear \$HOME tambien."; }

hr
echo "Reporte guardado en: $(pwd)/$REPORT"
echo
echo "SIGUIENTE PASO:"
echo "  1. Edita models.conf y pon OLD_MODEL con lo que viste arriba."
echo "  2. Corre ./01-pull-qwen38.sh   (descarga, no toca nada existente)"
hr
