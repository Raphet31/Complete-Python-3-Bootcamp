#!/usr/bin/env bash
# run-all.sh -- La migracion entera, en un solo comando.
#
# Encadena las nueve fases, guarda el progreso, y se puede reanudar si se
# corta. Por defecto se DETIENE antes del cambio final para que mires el
# informe; con --yes-flip lo hace solo si el veredicto lo aprueba.
#
# Uso:
#   ./run-all.sh                 todo hasta el informe; no cambia de modelo
#   ./run-all.sh --auto          no pregunta nada (aplica la migracion de configs)
#   ./run-all.sh --auto --yes-flip   ademas cambia de modelo si el veredicto aprueba
#   ./run-all.sh --from bench    reanuda desde una fase concreta
#   ./run-all.sh --status        que fases van hechas
#   ./run-all.sh --reset         olvida el progreso (no deshace nada)
#
# Fases: preflight inventory pull tasks bench report verdict init repoint flip

set -uo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
source ./models.conf

STATE=".run-all-state"
LOG="run-all.log"
PHASES=(preflight inventory pull tasks bench report verdict init repoint flip)

AUTO=0; YES_FLIP=0; FROM=""; MODE="run"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto)     AUTO=1 ;;
        --yes-flip) YES_FLIP=1 ;;
        --from)     FROM="${2:-}"; shift ;;
        --status)   MODE="status" ;;
        --reset)    MODE="reset" ;;
        -h|--help)  sed -n '2,20p' "$0"; exit 0 ;;
        *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
    esac
    shift
done

done_phase()  { [[ -f "$STATE" ]] && grep -qx "$1" "$STATE"; }
mark_phase()  { printf '%s\n' "$1" >> "$STATE"; }
say()         { printf '\n\033[1m== %s ==\033[0m\n' "$*" | tee -a "$LOG"; }
info()        { printf '   %s\n' "$*" | tee -a "$LOG"; }
fail()        { printf '\n\033[1mFALLO en la fase %s\033[0m\n   %s\n' "$1" "$2" >&2; exit 1; }

if [[ "$MODE" == "status" ]]; then
    echo "Progreso:"
    for p in "${PHASES[@]}"; do
        done_phase "$p" && echo "  [x] $p" || echo "  [ ] $p"
    done
    exit 0
fi
if [[ "$MODE" == "reset" ]]; then
    rm -f "$STATE"; echo "Progreso olvidado. Nada se deshizo."; exit 0
fi

# --from: recorta el estado para reejecutar desde ahi
if [[ -n "$FROM" ]]; then
    if [[ ! " ${PHASES[*]} " == *" $FROM "* ]]; then
        echo "Fase desconocida: $FROM" >&2; echo "Validas: ${PHASES[*]}" >&2; exit 2
    fi
    if [[ -f "$STATE" ]]; then
        awk -v stop="$FROM" '$0==stop{exit} {print}' "$STATE" > "$STATE.tmp" \
            && mv "$STATE.tmp" "$STATE"
    fi
fi

: > "$LOG"
echo "run-all -- $(date -u '+%Y-%m-%d %H:%M:%SZ')" >> "$LOG"
info "Log completo en: $(pwd)/$LOG"

# ---------------------------------------------------------------- preflight
if ! done_phase preflight; then
    say "1/10  Comprobaciones previas"
    command -v ollama >/dev/null 2>&1 \
        || fail preflight "ollama no esta instalado. curl -fsSL https://ollama.com/install.sh | sh"
    curl -fsS --max-time 8 "${OLLAMA_HOST}/api/tags" >/dev/null 2>&1 \
        || fail preflight "el daemon de ollama no responde en $OLLAMA_HOST. sudo systemctl start ollama"
    info "ollama responde en $OLLAMA_HOST"

    ARCH="$(uname -m)"
    info "arquitectura: $ARCH"
    [[ "$ARCH" == "aarch64" ]] || info "  aviso: el DGX Spark es aarch64; esto no lo parece."

    if command -v nvidia-smi >/dev/null 2>&1; then
        info "GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)"
    else
        info "  aviso: sin nvidia-smi. Sin GPU esto va a ir muy lento."
    fi

    AVAIL="$(df -BG --output=avail "$HOME" 2>/dev/null | tail -1 | tr -dc '0-9')"
    info "disco libre: ${AVAIL:-?}GB  (hacen falta ~40GB)"
    mark_phase preflight
fi

# ---------------------------------------------------------------- inventory
if ! done_phase inventory; then
    say "2/10  Inventario"
    ./00-inventory.sh >/dev/null 2>&1 || true
    info "reporte: inventory-report.txt"
    if [[ -z "${OLD_MODEL:-}" ]]; then
        fail inventory "OLD_MODEL vacio en models.conf. Mira inventory-report.txt y rellenalo."
    fi
    if ollama list 2>/dev/null | awk 'NR>1{print $1}' | grep -qx "$OLD_MODEL"; then
        info "modelo viejo presente: $OLD_MODEL"
    else
        fail inventory "el modelo viejo '$OLD_MODEL' no esta instalado. Corrige OLD_MODEL en models.conf."
    fi
    mark_phase inventory
fi

# --------------------------------------------------------------------- pull
if ! done_phase pull; then
    say "3/10  Descargando $NEW_MODEL"
    if ! ./01-pull-qwen38.sh --yes 2>&1 | tee -a "$LOG"; then
        info "NVFP4 fallo; reintentando con GGUF..."
        ./01-pull-qwen38.sh --gguf --yes 2>&1 | tee -a "$LOG" \
            || fail pull "no se pudo descargar ni NVFP4 ni GGUF."
    fi
    source ./models.conf   # 01 puede haber reescrito NEW_MODEL
    mark_phase pull
fi

# -------------------------------------------------------------------- tasks
if ! done_phase tasks; then
    say "4/10  Tareas de evaluacion"
    if [[ ! -f mis-tareas.txt ]]; then
        cp tareas-ejemplo.txt mis-tareas.txt
        info "creado mis-tareas.txt a partir del ejemplo."
        info "  Para que el bench valga de verdad, sustituyelo por TUS tareas"
        info "  reales y reejecuta:  ./run-all.sh --from bench"
    else
        info "usando mis-tareas.txt existente."
    fi
    mark_phase tasks
fi

# -------------------------------------------------------------------- bench
if ! done_phase bench; then
    say "5/10  Benchmark A/B (barrido de razonamiento)"
    info "mide low / medium / xhigh contra $OLD_MODEL. Tarda."
    ./03-ab-eval.py --prompts mis-tareas.txt --runs 5 --warmup 1 --sweep-effort \
        2>&1 | tee -a "$LOG" || fail bench "el benchmark no completo."
    mark_phase bench
fi

# ------------------------------------------------------------------- report
if ! done_phase report; then
    say "6/10  Informe comparativo"
    ./05-report.py 2>&1 | tee -a "$LOG" || fail report "no se pudo generar el informe."
    mark_phase report
fi

# ------------------------------------------------------------------ verdict
VERDICT=2
if ! done_phase verdict; then
    say "7/10  Veredicto"
    ./06-verdict.py 2>&1 | tee -a "$LOG"
    VERDICT=${PIPESTATUS[0]}
    printf '%s\n' "$VERDICT" > .verdict-code
    mark_phase verdict
else
    [[ -f .verdict-code ]] && VERDICT="$(cat .verdict-code)"
fi

# --------------------------------------------------------------------- init
if ! done_phase init; then
    say "8/10  Creando el alias (apuntando al modelo VIEJO)"
    info "esto NO cambia comportamiento: solo introduce la indireccion."
    ./02-switch-model.sh --init 2>&1 | tee -a "$LOG" \
        || fail init "no se pudo crear el alias."
    mark_phase init
fi

# ------------------------------------------------------------------ repoint
if ! done_phase repoint; then
    say "9/10  Migrando configs al alias"
    ./04-repoint-configs.py --path "$HOME" 2>&1 | tee -a "$LOG"
    if [[ $AUTO -eq 1 ]]; then
        info "--auto: aplicando."
        ./04-repoint-configs.py --path "$HOME" --apply 2>&1 | tee -a "$LOG" \
            || fail repoint "no se pudieron migrar los configs."
        info "reinicia los servicios que lean esos configs."
    else
        info "simulacro mostrado arriba. Para aplicarlo:"
        info "    ./04-repoint-configs.py --path \$HOME --apply"
        info "(o reejecuta con --auto)"
    fi
    mark_phase repoint
fi

# --------------------------------------------------------------------- flip
say "10/10  Cambio de modelo"
if [[ "$VERDICT" == "0" && $YES_FLIP -eq 1 ]]; then
    info "veredicto favorable y --yes-flip: cambiando."
    ./02-switch-model.sh 2>&1 | tee -a "$LOG" || fail flip "no se pudo cambiar."
    mark_phase flip
    say "MIGRACION COMPLETA"
    info "rollback en cualquier momento:  ./02-switch-model.sh --rollback"
else
    case "$VERDICT" in
        0) info "El veredicto APRUEBA el cambio." ;;
        1) info "El veredicto NO recomienda cambiar." ;;
        *) info "Sin recomendacion automatica: decidelo tu." ;;
    esac
    echo
    info "PARADA DELIBERADA. Antes del ultimo paso, mira el informe:"
    info "    $(pwd)/ab-report.html"
    echo
    info "Compara las respuestas lado a lado. Si el nuevo es al menos igual"
    info "de bueno, aplica el cambio con:"
    info "    ./02-switch-model.sh"
fi
