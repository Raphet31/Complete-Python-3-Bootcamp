#!/usr/bin/env bash
# Guardian de memoria de la GB10: si MemAvailable baja del piso, mata ComfyUI (:8189).
# Existe porque el 14-nov-2026 la GB10 se reinicio al cargar modelos de 57 GB.
PISO_GB=${1:-12}
while sleep 1; do
  disp=$(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)
  if [ "$disp" -lt "$PISO_GB" ]; then
    pkill -9 -f "main.py --listen 127.0.0.1 --port 8189"
    echo "$(date +%T) MATADO: disponible ${disp}G < ${PISO_GB}G"; sync; echo done; exit 1
  fi
  [ $((SECONDS % 30)) -eq 0 ] && echo "$(date +%T) disp ${disp}G"
done
