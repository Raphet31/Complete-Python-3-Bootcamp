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


# Qwen3.8 fue post-entrenado con estas frases; 'medium' es el default nativo
# del modelo y no inyecta nada. Se usan cuando el runtime no acepta el campo
# reasoning_effort de la API (--effort-via-system).
EFFORT_SYSTEM = {
    "low": "Reasoning effort is set to low. Answer directly with minimal deliberation.",
    "medium": "",
    "xhigh": "Reasoning effort is set to xhigh. Please think carefully before answering.",
}


def generate(host, model, prompt, timeout, effort=None, via_system=False):
    """Una llamada a /api/generate. Devuelve (metricas, error)."""
    payload = {"model": model, "prompt": prompt, "stream": False}
    if effort:
        if via_system:
            sys_msg = EFFORT_SYSTEM.get(effort, "")
            if sys_msg:
                payload["system"] = sys_msg
        else:
            payload["reasoning_effort"] = effort
    body = json.dumps(payload).encode()
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
    ap.add_argument("--reasoning-effort", choices=["low", "medium", "xhigh"],
                    default=(conf.get("REASONING_EFFORT") or None),
                    help="nivel de razonamiento para el modelo A. Qwen3.8 viene en "
                         "xhigh por defecto y se pasa de vueltas; medium suele ser "
                         "el punto util")
    ap.add_argument("--sweep-effort", action="store_true",
                    help="mide el modelo A en low, medium y xhigh para ver la curva "
                         "coste/beneficio antes de fijar el nivel")
    ap.add_argument("--effort-via-system", action="store_true",
                    help="aplica el nivel por system prompt en vez del campo de API "
                         "(para runtimes que no soportan reasoning_effort)")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--host", default=conf.get("OLLAMA_HOST") or "http://localhost:11434")
    args = ap.parse_args()

    if not args.a:
        sys.exit("ERROR: falta el modelo A. Pasa --a o rellena NEW_MODEL en models.conf")
    if not args.b:
        sys.exit("ERROR: falta el modelo B (viejo). Pasa --b o rellena OLD_MODEL.\n"
                 "Corre ./00-inventory.sh para descubrir cual es.")

    prompts = load_prompts(args.prompts)

    # Una "variante" es un modelo corrido en un nivel de razonamiento concreto.
    # El modelo viejo va sin nivel: no tiene el parametro.
    if args.sweep_effort:
        variants = [(f"{args.a} @{lv}", args.a, lv)
                    for lv in ("low", "medium", "xhigh")]
        label_a = f"{args.a} @medium"
    else:
        label_a = f"{args.a} @{args.reasoning_effort}" if args.reasoning_effort else args.a
        variants = [(label_a, args.a, args.reasoning_effort)]
    variants.append((args.b, args.b, None))
    labels = [v[0] for v in variants]

    print(f"A (nuevo):    {args.a}")
    print(f"B (viejo):    {args.b}")
    print(f"Prompts:      {len(prompts)}   medidas: {args.runs}   warm-up: {args.warmup}")
    print(f"Concurrencia: {args.concurrency}")
    if args.sweep_effort:
        print("Razonamiento: barrido low / medium / xhigh sobre el modelo A")
    elif args.reasoning_effort:
        print(f"Razonamiento: {args.reasoning_effort}"
              f"{' (via system prompt)' if args.effort_via_system else ''}")
    else:
        print("Razonamiento: por defecto del runtime  <-- OJO: en Qwen3.8 es xhigh,")
        print("              y hara que parezca mucho mas lento de lo que es.")
        print("              Usa --sweep-effort para verlo.")
    print(f"Host:         {args.host}")
    print("-" * 68)

    results = {lb: [] for lb in labels}
    errors = []
    memory = {}

    warmed = set()
    for label, model, effort in variants:
        # Warm-up: carga el modelo en memoria. Estas corridas NO se miden.
        # Un modelo ya cargado no se recalienta entre variantes de effort.
        if args.warmup and model not in warmed:
            print(f"\ncalentando {model} ({args.warmup} corrida/s descartada/s)...")
            for _ in range(args.warmup):
                _, err = generate(args.host, model, prompts[0], args.timeout,
                                  effort, args.effort_via_system)
                if err:
                    print(f"  aviso durante warm-up: {err[:70]}")
            warmed.add(model)
            mb = resident_mb(model)
            if mb:
                print(f"  residente: {mb / 1024:.1f} GB")
        memory[label] = resident_mb(model)

    for i, prompt in enumerate(prompts, 1):
        print(f"\n[{i}/{len(prompts)}] {prompt.replace(chr(10), ' ')[:52]}...")
        for label, model, effort in variants:
            gargs = (args.host, model, prompt, args.timeout, effort,
                     args.effort_via_system)
            if args.concurrency > 1:
                with concurrent.futures.ThreadPoolExecutor(args.concurrency) as ex:
                    futs = [ex.submit(generate, *gargs) for _ in range(args.runs)]
                    pairs = [f.result() for f in futs]
            else:
                pairs = [generate(*gargs) for _ in range(args.runs)]

            runs = []
            for metrics, err in pairs:
                if err:
                    errors.append({"variant": label, "prompt_index": i, "error": err})
                    runs.append(None)
                else:
                    runs.append(metrics)

            st = summarize(runs)
            if st.get("ok"):
                print(f"    {label:<30} p50 {st['wall_p50']:>6.2f}s  "
                      f"p95 {st['wall_p95']:>6.2f}s  {st['tps_p50']:>6.1f} tok/s  "
                      f"{st['output_tokens_p50']:>5.0f} tok")
            else:
                print(f"    {label:<30} TODAS fallaron")
            results[label].append({
                "prompt_index": i, "prompt": prompt, "summary": st,
                "sample_output": next((r["response"] for r in runs if r), None),
            })

    # --- Resumen ---------------------------------------------------------
    print("\n" + "=" * 68)
    print("RESUMEN")
    print("=" * 68)
    print(f"  {'variante':<30} {'p50':>8} {'p95':>8} {'tok/s':>8} {'tokens':>8}")
    for label in labels:
        oks = [e["summary"] for e in results[label] if e["summary"].get("ok")]
        if not oks:
            print(f"  {label:<30} {'sin corridas exitosas':>34}")
            continue
        print(f"  {label:<30} "
              f"{statistics.median(x['wall_p50'] for x in oks):>7.2f}s "
              f"{statistics.median(x['wall_p95'] for x in oks):>7.2f}s "
              f"{statistics.median(x['tps_p50'] for x in oks):>7.1f} "
              f"{statistics.median(x['output_tokens_p50'] for x in oks):>8.0f}")
    if args.sweep_effort:
        print("\n  La columna 'tokens' es la que explica el coste de xhigh:")
        print("  son tokens de razonamiento que pagas en tiempo y no ves.")

    if errors:
        print(f"\n  {len(errors)} llamada(s) fallaron -- detalle en el JSON.")

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": args.host, "model_a_new": label_a, "model_b_old": args.b,
        "variants": [{"label": lb, "model": m, "effort": e} for lb, m, e in variants],
        "runs_per_prompt": args.runs, "warmup": args.warmup,
        "concurrency": args.concurrency,
        "reasoning_effort": args.reasoning_effort,
        "sweep_effort": args.sweep_effort,
        "resident_mb": memory,
        "results": results, "errors": errors,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    print(f"\nResultados: {OUT}")
    print("\nLa velocidad la mide esto. La CALIDAD la juzgas tu:")
    print("    ./05-report.py        -> comparativa lado a lado en HTML")


if __name__ == "__main__":
    main()
