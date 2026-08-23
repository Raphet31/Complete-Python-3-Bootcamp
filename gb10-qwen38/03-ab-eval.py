#!/usr/bin/env python3
"""A/B entre el modelo viejo y Qwen3.8-27B sobre TUS tareas reales.

El punto de este script: 14 puntos en una tabla publica no son 14 puntos en tu
carga de trabajo. Esto mide latencia, throughput y salida de los dos modelos
sobre los mismos prompts, para decidir con datos propios.

Solo stdlib -- no hace falta pip install nada en la GB10.

Uso:
    ./03-ab-eval.py --prompts mis-tareas.txt
    ./03-ab-eval.py --prompts mis-tareas.txt --runs 3
    ./03-ab-eval.py --a qwen3.8:27b-nvfp4 --b llama3.1:70b --prompts t.txt

Formato del archivo de prompts: prompts separados por una linea '---'.
Si no hay ningun '---', cada linea no vacia se toma como un prompt.
"""

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "models.conf")
OUT = os.path.join(HERE, "ab-results.json")


def read_conf():
    """Lee models.conf sin depender de bash."""
    conf = {}
    if not os.path.exists(CONF):
        return conf
    pat = re.compile(r'^\s*([A-Z_]+)\s*=\s*"?([^"#\n]*)"?')
    with open(CONF, encoding="utf-8") as fh:
        for line in fh:
            if line.lstrip().startswith("#"):
                continue
            m = pat.match(line)
            if m:
                conf[m.group(1)] = m.group(2).strip()
    return conf


def load_prompts(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    if re.search(r"^---\s*$", raw, re.M):
        parts = re.split(r"^---\s*$", raw, flags=re.M)
    else:
        parts = raw.splitlines()
    prompts = [p.strip() for p in parts if p.strip()]
    if not prompts:
        sys.exit(f"ERROR: no encontre ningun prompt en {path}")
    return prompts


def generate(host, model, prompt, timeout):
    """Una llamada a /api/generate. Devuelve (metricas, error)."""
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}"
    except Exception as exc:  # noqa: BLE001 -- queremos seguir con el resto
        return None, f"{type(exc).__name__}: {exc}"

    wall = time.monotonic() - started
    eval_count = data.get("eval_count") or 0
    eval_ns = data.get("eval_duration") or 0
    tps = (eval_count / (eval_ns / 1e9)) if eval_ns else 0.0

    return {
        "wall_s": round(wall, 3),
        "total_s": round((data.get("total_duration") or 0) / 1e9, 3),
        "load_s": round((data.get("load_duration") or 0) / 1e9, 3),
        "prompt_tokens": data.get("prompt_eval_count") or 0,
        "output_tokens": eval_count,
        "tokens_per_s": round(tps, 2),
        "response": data.get("response", ""),
    }, None


def summarize(runs):
    """Agrega las metricas de varias corridas del mismo (modelo, prompt)."""
    ok = [r for r in runs if r]
    if not ok:
        return {"ok": 0, "failed": len(runs)}
    return {
        "ok": len(ok),
        "failed": len(runs) - len(ok),
        "wall_s_median": round(statistics.median(r["wall_s"] for r in ok), 3),
        "tokens_per_s_median": round(
            statistics.median(r["tokens_per_s"] for r in ok), 2
        ),
        "output_tokens_median": int(
            statistics.median(r["output_tokens"] for r in ok)
        ),
    }


def main():
    conf = read_conf()
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompts", required=True, help="archivo con tus prompts reales")
    ap.add_argument("--a", default=conf.get("NEW_MODEL", ""), help="modelo A (nuevo)")
    ap.add_argument("--b", default=conf.get("OLD_MODEL", ""), help="modelo B (viejo)")
    ap.add_argument("--runs", type=int, default=1, help="repeticiones por prompt")
    ap.add_argument("--timeout", type=int, default=600, help="timeout por llamada (s)")
    ap.add_argument("--host", default=conf.get("OLLAMA_HOST") or "http://localhost:11434")
    args = ap.parse_args()

    if not args.a:
        sys.exit("ERROR: falta el modelo A. Pasa --a o rellena NEW_MODEL en models.conf")
    if not args.b:
        sys.exit(
            "ERROR: falta el modelo B (el viejo). Pasa --b o rellena OLD_MODEL\n"
            "en models.conf. Corre ./00-inventory.sh para descubrir cual es."
        )

    prompts = load_prompts(args.prompts)
    models = [args.a, args.b]

    print(f"A (nuevo): {args.a}")
    print(f"B (viejo): {args.b}")
    print(f"Prompts:   {len(prompts)}   Repeticiones: {args.runs}")
    print(f"Host:      {args.host}")
    print("-" * 61)

    results = {m: [] for m in models}
    errors = []

    for i, prompt in enumerate(prompts, 1):
        preview = prompt.replace("\n", " ")[:48]
        print(f"\n[{i}/{len(prompts)}] {preview}...")
        for model in models:
            runs = []
            for r in range(args.runs):
                metrics, err = generate(args.host, model, prompt, args.timeout)
                if err:
                    errors.append({"model": model, "prompt_index": i, "error": err})
                    print(f"    {model:<28} FALLO: {err[:60]}")
                    runs.append(None)
                    continue
                runs.append(metrics)
                tag = f" (run {r + 1})" if args.runs > 1 else ""
                print(
                    f"    {model:<28} {metrics['wall_s']:>7.2f}s "
                    f"{metrics['tokens_per_s']:>7.1f} tok/s "
                    f"{metrics['output_tokens']:>5} tok{tag}"
                )
            results[model].append(
                {
                    "prompt_index": i,
                    "prompt": prompt,
                    "summary": summarize(runs),
                    # Guardamos la salida de la 1a corrida: la calidad la juzgas
                    # tu leyendo esto, no una metrica automatica.
                    "sample_output": next(
                        (r["response"] for r in runs if r), None
                    ),
                }
            )

    # --- Resumen ----------------------------------------------------------
    print("\n" + "=" * 61)
    print("RESUMEN (medianas sobre todos los prompts)")
    print("=" * 61)
    for model in models:
        tps = [
            e["summary"]["tokens_per_s_median"]
            for e in results[model]
            if e["summary"].get("ok")
        ]
        wall = [
            e["summary"]["wall_s_median"]
            for e in results[model]
            if e["summary"].get("ok")
        ]
        if not tps:
            print(f"  {model:<30} sin corridas exitosas")
            continue
        print(
            f"  {model:<30} {statistics.median(tps):>7.1f} tok/s   "
            f"{statistics.median(wall):>7.2f}s por tarea"
        )

    if errors:
        print(f"\n  {len(errors)} llamada(s) fallaron -- detalle en el JSON.")

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": args.host,
        "model_a_new": args.a,
        "model_b_old": args.b,
        "runs_per_prompt": args.runs,
        "results": results,
        "errors": errors,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print(f"\nResultados: {OUT}")
    print(
        "\nLa velocidad la mide este script. La CALIDAD la juzgas tu:\n"
        "lee los 'sample_output' del JSON y compara las respuestas lado a lado.\n"
        "Si el nuevo no gana claramente en TUS tareas, no cambies."
    )


if __name__ == "__main__":
    main()
