#!/usr/bin/env bash
# 02-switch-model.sh -- Repunta el alias estable al modelo nuevo.
#
# MECANISMO: en vez de editar N configs repartidas por la maquina, creamos un
# alias de ollama ('work-default') y hacemos que las apps lo nombren a el.
# Cambiar de modelo pasa a ser una linea, y volver atras tambien.
#
# El modelo viejo NUNCA se borra. Este script no invoca 'ollama rm' jamas.
#
# Uso:  ./02-switch-model.sh              repunta alias -> NEW_MODEL
#       ./02-switch-model.sh --init       crea el alias -> OLD_MODEL
#                                         (introduce la indireccion SIN cambiar
#                                          comportamiento; hacer esto ANTES de
#                                          migrar configs con 04)
#       ./02-switch-model.sh --rollback   repunta alias -> OLD_MODEL
#       ./02-switch-model.sh --status     solo muestra a que apunta hoy
#       ./02-switch-model.sh --dry-run    enseña que haria, sin hacerlo

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
# shellcheck source=models.conf
source ./models.conf

STATE_FILE=".alias-state"
MODE="switch"
DRY=0
for arg in "$@"; do
    case "$arg" in
        --init)     MODE="init" ;;
        --rollback) MODE="rollback" ;;
        --status)   MODE="status" ;;
        --dry-run)  DRY=1 ;;
        *) echo "Argumento desconocido: $arg" >&2; exit 2 ;;
    esac
done

command -v ollama >/dev/null 2>&1 || { echo "ERROR: ollama no esta en PATH." >&2; exit 1; }

model_exists() {
    ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$1"
}

current_target() {
    [[ -f "$STATE_FILE" ]] && cat "$STATE_FILE" || echo "(desconocido)"
}

# --- status ---------------------------------------------------------------
if [[ "$MODE" == "status" ]]; then
    echo "Alias:            $ALIAS"
    echo "Apunta a:         $(current_target)"
    echo "Modelo nuevo:     $NEW_MODEL     $(model_exists "$NEW_MODEL" && echo '[instalado]' || echo '[NO instalado]')"
    echo "Modelo viejo:     ${OLD_MODEL:-<sin definir>}  $( [[ -n "$OLD_MODEL" ]] && { model_exists "$OLD_MODEL" && echo '[instalado]' || echo '[NO instalado]'; } )"
    echo
    echo "Alias existente en ollama:"
    ollama list 2>/dev/null | awk -v a="$ALIAS" 'NR==1 || $1 ~ "^"a' | sed 's/^/  /'
    exit 0
fi

# --- Elegir destino -------------------------------------------------------
if [[ "$MODE" == "rollback" || "$MODE" == "init" ]]; then
    [[ -n "$OLD_MODEL" ]] || {
        echo "ERROR: OLD_MODEL esta vacio en models.conf." >&2
        echo "Corre ./00-inventory.sh y rellenalo." >&2
        exit 1
    }
    DEST="$OLD_MODEL"
    if [[ "$MODE" == "init" ]]; then
        echo "==> INIT: $ALIAS -> $DEST (el modelo que ya usas)"
        echo "    Esto NO cambia comportamiento: solo crea la indireccion."
        echo "    Siguiente: ./04-repoint-configs.py --apply, verificar, y"
        echo "    recien entonces ./02-switch-model.sh para el flip."
    else
        echo "==> ROLLBACK: $ALIAS -> $DEST"
    fi
else
    DEST="$NEW_MODEL"
    echo "==> SWITCH: $ALIAS -> $DEST"
fi

model_exists "$DEST" || {
    echo "ERROR: '$DEST' no esta instalado." >&2
    [[ "$MODE" == "switch" ]] && echo "Corre primero ./01-pull-qwen38.sh" >&2
    exit 1
}

# --- Aviso si no se midio nada -------------------------------------------
if [[ $DRY -eq 0 && "$MODE" == "switch" && ! -f "ab-results.json" ]]; then
    echo
    echo "AVISO: no encuentro ab-results.json, o sea que no corriste el A/B."
    echo "Los 14 puntos de la tabla publica son del Qwen3.8-MAX (2.4T params),"
    echo "no de este 27B, y salen de la tabla de la propia Alibaba."
    echo "Cambiar sin medir es cambiar a ciegas."
    echo
    read -rp "Continuar de todos modos? [y/N] " ok
    [[ "$ok" == "y" || "$ok" == "Y" ]] || { echo "Abortado. Corre ./03-ab-eval.py primero."; exit 1; }
fi

# --- Backup del estado actual --------------------------------------------
PREV="$(current_target)"
if [[ $DRY -eq 1 ]]; then
    echo
    echo "[dry-run] Ejecutaria:  ollama cp \"$DEST\" \"$ALIAS\""
    echo "[dry-run] Guardaria en $STATE_FILE:  $DEST"
    echo "[dry-run] Estado anterior preservado: $PREV"
    exit 0
fi

# --- Repuntar -------------------------------------------------------------
# 'ollama cp' copia el manifiesto, no los pesos: comparte blobs, es instantaneo
# y no duplica los 17GB en disco.
ollama cp "$DEST" "$ALIAS"
printf '%s\n' "$DEST" > "$STATE_FILE"

echo "==> Alias repuntado."
echo "    Antes:   $PREV"
echo "    Ahora:   $DEST"

# --- Verificacion ---------------------------------------------------------
echo; echo "==> Verificando que el alias responde..."
RESP="$(curl -fsS --max-time 180 "${OLLAMA_HOST}/api/generate" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"${ALIAS}\",\"prompt\":\"Responde unicamente con la palabra: OK\",\"stream\":false}" \
    2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("response","").strip())' 2>/dev/null || echo "")"

if [[ -n "$RESP" ]]; then
    echo "    Respuesta via '$ALIAS': $RESP"
else
    echo "    AVISO: el alias no respondio. Volviendo atras por seguridad..." >&2
    if [[ "$PREV" != "(desconocido)" ]] && model_exists "$PREV"; then
        ollama cp "$PREV" "$ALIAS"
        printf '%s\n' "$PREV" > "$STATE_FILE"
        echo "    Rollback automatico hecho: $ALIAS -> $PREV" >&2
    else
        echo "    No pude auto-revertir (estado previo desconocido)." >&2
        echo "    Manual:  ./02-switch-model.sh --rollback" >&2
    fi
    exit 1
fi

echo
echo "-------------------------------------------------------------"
echo "HECHO. El modelo viejo sigue instalado e intacto."
echo
echo "Apunta tus apps al alias, no al modelo:"
echo "    OLLAMA_MODEL=$ALIAS"
echo
echo "Para volver atras en cualquier momento:"
echo "    ./02-switch-model.sh --rollback"
echo "-------------------------------------------------------------"
