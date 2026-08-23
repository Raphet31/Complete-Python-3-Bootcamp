#!/usr/bin/env python3
"""Lee ab-results.json y dicta un veredicto: cambiar o no cambiar.

La decision no es "cual es mas rapido". Es: al nivel de razonamiento donde el
modelo nuevo da respuestas al menos tan buenas, ¿cuesta un tiempo aceptable?

Reglas, en orden:
  1. Si el nuevo no completo las tareas, no se cambia. Sin excepcion.
  2. Entre los niveles que caben en el margen de latencia, se elige el MAS
     ALTO, no el mas barato. En un modelo de razonamiento mas esfuerzo tiende
     a dar mejores respuestas, asi que si xhigh y low caben los dos, xhigh es
     mejor trato: misma latencia aceptable, mas calidad.
  3. Si ningun nivel entra en el margen, no hay recomendacion automatica:
     lo decides tu leyendo el informe.

La calidad NO se juzga aqui -- ninguna metrica automatica sustituye leer las
dos respuestas. Esto acota el punto de operacion; la ultima palabra es tuya.

Uso:
    ./06-verdict.py
    ./06-verdict.py --max-slowdown 1.5     # tolera hasta 50% mas lento
    ./06-verdict.py --quiet                # solo el codigo de salida

Codigos de salida:  0 = cambiar   1 = no cambiar   2 = decides tu
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORDER = {"low": 0, "medium": 1, "xhigh": 2}


def med(entries, key):
    vals = [e["summary"][key] for e in entries
            if e["summary"].get("ok") and isinstance(e["summary"].get(key), (int, float))]
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=os.path.join(HERE, "ab-results.json"))
    ap.add_argument("--max-slowdown", type=float, default=1.25,
                    help="cuanto mas lento se tolera el nuevo (1.25 = 25%%)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.json):
        print(f"ERROR: no encuentro {args.json}. Corre ./03-ab-eval.py primero.",
              file=sys.stderr)
        return 2
    with open(args.json, encoding="utf-8") as fh:
        d = json.load(fh)

    old = d["model_b_old"]
    variants = d.get("variants") or []
    new_vs = [v for v in variants if v["label"] != old and v["label"] in d["results"]]
    if old not in d["results"] or not new_vs:
        print("ERROR: el JSON no tiene ambas mitades del A/B.", file=sys.stderr)
        return 2

    old_lat = med(d["results"][old], "wall_p50")
    old_ok = any(e["summary"].get("ok") for e in d["results"][old])

    say = (lambda *a: None) if args.quiet else print
    say("=" * 62)
    say("VEREDICTO")
    say("=" * 62)

    if old_lat is None or not old_ok:
        say(f"\n  El modelo viejo ({old}) no completo ninguna tarea.")
        say("  Sin linea base no hay comparacion posible.")
        return 2

    say(f"\n  Linea base — {old}: {old_lat:.2f}s por tarea (p50)")
    say(f"  Margen tolerado: hasta {args.max_slowdown:.2f}x  "
        f"({old_lat * args.max_slowdown:.2f}s)\n")

    rows, viables = [], []
    for v in new_vs:
        lab = v["label"]
        entries = d["results"][lab]
        done = sum(1 for e in entries if e["summary"].get("ok"))
        lat = med(entries, "wall_p50")
        toks = med(entries, "output_tokens_p50")
        if not done or lat is None:
            rows.append((lab, None, None, None, "no completo"))
            continue
        ratio = lat / old_lat
        ok = done == len(entries) and ratio <= args.max_slowdown
        rows.append((lab, lat, ratio, toks, "dentro" if ok else "fuera de margen"))
        if ok:
            # negativo para que sort() deje el esfuerzo MAS ALTO primero
            viables.append((-ORDER.get(v.get("effort"), -1), lab, lat, ratio))

    for lab, lat, ratio, toks, note in rows:
        if lat is None:
            say(f"  {lab:<32} {'—':>8}  {note}")
        else:
            say(f"  {lab:<32} {lat:>7.2f}s  {ratio:>5.2f}x  "
                f"{toks:>6.0f} tok   {note}")

    if not viables:
        say("\n  NINGUN nivel del modelo nuevo entra en el margen.")
        say("  No hay recomendacion automatica: abre ab-report.html, compara")
        say("  las respuestas, y decide si la calidad justifica el tiempo.")
        say("\n  Si la calidad es claramente mejor, sube el margen:")
        say("      ./06-verdict.py --max-slowdown 2.0")
        return 2

    viables.sort()
    _, lab, lat, ratio = viables[0]
    say(f"\n  RECOMENDACION: cambiar, usando  {lab}")
    say(f"  {lat:.2f}s por tarea ({ratio:.2f}x respecto al viejo)")
    if len(viables) > 1:
        otros = ", ".join(v[1].split("@")[-1] for v in viables[1:])
        say(f"  (tambien caben en el margen: {otros} — mas rapidos, menos"
            f" razonamiento)")
    say("\n  Antes de aceptarlo, abre ab-report.html y comprueba que las")
    say("  respuestas del nuevo son al menos tan buenas. La velocidad la")
    say("  midio el bench; la calidad la juzgas tu.")
    say("\n  Para aplicar el cambio:")
    say("      ./02-switch-model.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
