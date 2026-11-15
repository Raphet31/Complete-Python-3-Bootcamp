#!/usr/bin/env bash
# Marcapasos termico para ComfyUI (:8189) en la GB10. v2 (15-nov-2026).
# La GB10 pasa de 60 a 80 C en ~2 s con el modelo de video; el governor de la casa
# (ayuno/termico_unico.py) corta a 80 C con pausas crecientes de hasta 10 min.
# Este script frena ANTES: lee cada 0.25 s, congela ComfyUI a TOPE (def 68 C) o tras RAFAGA
# segundos corridos (def 1.5), y lo suelta a PISO (def 61 C).
# Nunca suelta nada mientras el governor este en CORTE: el manda.
TOPE=${1:-68}; PISO=${2:-61}; RAFAGA=${3:-1.5}
EST=~/Documents/BELLA_FLOR_OS/command_center/state/thermal_watchdog.json
temp(){ cat /sys/class/thermal/thermal_zone*/temp | sort -n | tail -1 | awk '{print int($1/1000)}'; }
ahora(){ date +%s.%N; }
frenado=0; n=0; fr=0; t0=$(ahora); maxt=0
while sleep 0.25; do
  pid=$(pgrep -f "[m]ain.py --listen 127.0.0.1 --port 8189" | head -1); [ -z "$pid" ] && continue
  t=$(temp); [ "$t" -gt "$maxt" ] && maxt=$t
  if [ "$frenado" = 0 ]; then
    largo=$(echo "$(ahora) - $t0 > $RAFAGA" | bc)
    if [ "$t" -ge "$TOPE" ] || [ "$largo" = 1 ]; then kill -STOP "$pid"; frenado=1; fr=$((fr+1)); fi
  elif [ "$t" -le "$PISO" ] && ! grep -q '"paused": true' "$EST" 2>/dev/null; then
    kill -CONT "$pid"; frenado=0; t0=$(ahora)
  fi
  n=$((n+1)); [ $((n % 240)) -eq 0 ] && { echo "$(date +%T) ${t}C max ${maxt}C frenos ${fr}"; maxt=0; }
done
