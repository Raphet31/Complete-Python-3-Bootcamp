#!/usr/bin/env python3
"""A/B entre el modelo viejo y Qwen3.8-27B sobre TUS tareas reales.

El punto: 14 puntos en una tabla publica no son 14 puntos en tu carga de
trabajo. Esto mide sobre tus prompts, en tu hardware.

Que mide, y por que:
  - warm-up descartado    la 1a llamada carga el modelo (decenas de segundos)
                          y castigaria injustamente al modelo mas grande
  - p50 y p95             la mediana esconde la cola, y la cola es lo que se
                          siente en uso real
  - memoria residente     en 128GB unificados del GB10, cuanto margen queda
                          es la pregunta que decide cuantas sesiones caben
  - concurrencia opcional  17GB en 128GB dan para varias sesiones a la vez

Solo stdlib -- no hace falta pip install nada en la GB10.

Uso:
    ./03-ab-eval.py --prompts mis-tareas.txt
    ./03-ab-eval.py --prompts mis-tareas.txt --runs 5 --warmup 1
    ./03-ab-eval.py --prompts mis-tareas.txt --concurrency 4
    ./03-ab-eval.py --a qwen3.8:27b-nvfp4 --b llama3.1:70b --prompts t.txt

Formato del archivo de prompts: prompts separados por una linea '---'.
Si no hay ningun '---', cada linea no vacia se toma como un prompt.
"""

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONF = os.path.join(HERE, "models.conf")
OUT = os.path.join(HERE, "ab-results.json")


def read_conf():
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
    # las lineas de comentario al inicio de un prompt son andamiaje, no tarea
    cleaned = []
    for p in parts:
        body = "\n".join(
            ln for ln in p.splitlines() if not ln.lstrip().startswith("#")
        ).strip()
        if body:
            cleaned.append(body)
    if not cleaned:
        sys.exit(f"ERROR: no encontre ningun prompt en {path}")
    return cleaned


def generate(host, model, prompt, timeout):
    """Una llamada a /api/generate. Devuelve (metricas, error)."""
    body = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{host}/api/generate", data=body,
        headers={"Content-Type": "application/json"},
    )
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.read()[:200].decode('utf-8', 'replace')}"
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"

    wall = time.monotonic() - started
    eval_count = data.get("eval_count") or 0
    eval_ns = data.get("eval_duration") or 0
    prompt_ns = data.get("prompt_eval_duration") or 0
    return {
        "wall_s": round(wall, 3),
        "load_s": round((data.get("load_duration") or 0) / 1e9, 3),
        "ttft_s": round(prompt_ns / 1e9, 3),   # aprox: tiempo de prefill
        "prompt_tokens": data.get("prompt_eval_count") or 0,
        "output_tokens": eval_count,
        "tokens_per_s": round(eval_count / (eval_ns / 1e9), 2) if eval_ns else 0.0,
        "response": data.get("response", ""),
    }, None


def resident_mb(model):
    """Cuanta memoria tiene ollama cargada para este modelo. Best-effort."""
    if not shutil.which("ollama"):
        return None
    try:
        out = subprocess.run(["ollama", "ps"], capture_output=True, text=True,
                             timeout=15).stdout
    except (subprocess.SubprocessError, OSError):
        return None
    for line in out.splitlines()[1:]:
        if not line.strip() or not line.split()[0].startswith(model.split(":")[0]):
            continue
        m = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB)", line)
        if m:
            val = float(m.group(1))
            return round(val * 1024 if m.group(2) == "GB" else val, 1)
    return None


def pct(values, p):
    """Percentil por interpolacion lineal. statistics.quantiles necesita n>=2."""
    if not values:
        return None
    s = sorted(values)
    if len(s) == 1:
        return round(s[0], 3)
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo), 3)


def summarize(runs):
    ok = [r for r in runs if r]
    if not ok:
        return {"ok": 0, "failed": len(runs)}
    wall = [r["wall_s"] for r in ok]
    tps = [r["tokens_per_s"] for r in ok]
    return {
        "ok": len(ok),
        "failed": len(runs) - len(ok),
        "wall_p50": pct(wall, 50),
        "wall_p95": pct(wall, 95),
        "tps_p50": pct(tps, 50),
        "tps_p95": pct(tps, 95),
        "ttft_p50": pct([r["ttft_s"] for r in ok], 50),
        "output_tokens_p50": pct([r["output_tokens"] for r in ok], 50),
    }


def main():
    conf = read_conf()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--a", default=conf.get("NEW_MODEL", ""), help="modelo A (nuevo)")
    ap.add_argument("--b", default=conf.get("OLD_MODEL", ""), help="modelo B (viejo)")
    ap.add_argument("--runs", type=int, default=3, help="corridas medidas por prompt")
    ap.add_argument("--warmup", type=int, default=1,
                    help="corridas descartadas antes de medir (carga del modelo)")
    ap.add_argument("--concurrency", type=int, default=1,
                    help="peticiones simultaneas; >1 mide degradacion bajo carga")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--host", default=conf.get("OLLAMA_HOST") or "http://localhost:11434")
    args = ap.parse_args()

    if not args.a:
        sys.exit("ERROR: falta el modelo A. Pasa --a o rellena NEW_MODEL en models.conf")
    if not args.b:
        sys.exit("ERROR: falta el modelo B (viejo). Pasa --b o rellena OLD_MODEL.\n"
                 "Corre ./00-inventory.sh para descubrir cual es.")

    prompts = load_prompts(args.prompts)
    models = [args.a, args.b]

    print(f"A (nuevo):    {args.a}")
    print(f"B (viejo):    {args.b}")
    print(f"Prompts:      {len(prompts)}   medidas: {args.runs}   warm-up: {args.warmup}")
    print(f"Concurrencia: {args.concurrency}")
    print(f"Host:         {args.host}")
    print("-" * 68)

    results = {m: [] for m in models}
    errors = []
    memory = {}

    for model in models:
        # Warm-up: carga el modelo en memoria. Estas corridas NO se miden.
        if args.warmup:
            print(f"\ncalentando {model} ({args.warmup} corrida/s descartada/s)...")
            for _ in range(args.warmup):
                _, err = generate(args.host, model, prompts[0], args.timeout)
                if err:
                    print(f"  aviso durante warm-up: {err[:70]}")
        mb = resident_mb(model)
        memory[model] = mb
        if mb:
            print(f"  residente: {mb / 1024:.1f} GB")

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] {prompt.replace(chr(10), ' ')[:52]}...")
        for model in models:
            if args.concurrency > 1:
                with concurrent.futures.ThreadPoolExecutor(args.concurrency) as ex:
                    futs = [ex.submit(generate, args.host, model, prompt, args.timeout)
                            for _ in range(args.runs)]
                    pairs = [f.result() for f in futs]
            else:
                pairs = [generate(args.host, model, prompt, args.timeout)
                         for _ in range(args.runs)]

            runs = []
            for metrics, err in pairs:
                if err:
                    errors.append({"model": model, "prompt_index": i, "error": err})
                    runs.append(None)
                else:
                    runs.append(metrics)

            s = summarize(runs)
            if s.get("ok"):
                print(f"    {model:<28} p50 {s['wall_p50']:>6.2f}s  "
                      f"p95 {s['wall_p95']:>6.2f}s  {s['tps_p50']:>6.1f} tok/s")
            else:
                print(f"    {model:<28} TODAS fallaron")
            results[model].append({
                "prompt_index": i, "prompt": prompt, "summary": s,
                "sample_output": next((r["response"] for r in runs if r), None),
            })

    # --- Resumen ---------------------------------------------------------
    print("\n" + "=" * 68)
    print("RESUMEN")
    print("=" * 68)
    print(f"  {'modelo':<28} {'p50':>8} {'p95':>8} {'tok/s':>8} {'RAM':>9}")
    for model in models:
        oks = [e["summary"] for e in results[model] if e["summary"].get("ok")]
        if not oks:
            print(f"  {model:<28} {'sin corridas exitosas':>36}")
            continue
        mb = memory.get(model)
        print(f"  {model:<28} "
              f"{statistics.median(s['wall_p50'] for s in oks):>7.2f}s "
              f"{statistics.median(s['wall_p95'] for s in oks):>7.2f}s "
              f"{statistics.median(s['tps_p50'] for s in oks):>7.1f} "
              f"{(f'{mb / 1024:.1f} GB' if mb else 'n/d'):>9}")

    if errors:
        print(f"\n  {len(errors)} llamada(s) fallaron -- detalle en el JSON.")

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": args.host, "model_a_new": args.a, "model_b_old": args.b,
        "runs_per_prompt": args.runs, "warmup": args.warmup,
        "concurrency": args.concurrency, "resident_mb": memory,
        "results": results, "errors": errors,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print(f"\nResultados: {OUT}")
    print("\nLa velocidad la mide esto. La CALIDAD la juzgas tu:")
    print("    ./05-report.py        -> comparativa lado a lado en HTML")


if __name__ == "__main__":
    main()
