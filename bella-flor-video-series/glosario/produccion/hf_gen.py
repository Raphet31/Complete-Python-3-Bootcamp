#!/usr/bin/env python3
"""Genera imagen o video con el CLI de Higgsfield (corre en la GB10, donde vive la sesion).
  hf_gen.py img <salida.png> "<prompt>" [--ref imagen.png] [--res 2k]
  hf_gen.py vid <salida.mp4> "<prompt>" --ref imagen.png [--modelo kling3_0_turbo|kling4_0]
Deja <salida>.json con la receta (modelo, prompt, id del trabajo, creditos estimados)."""
import argparse, json, os, re, subprocess, sys
HF = os.path.expanduser("~/.local/bin/higgsfield")
ap = argparse.ArgumentParser()
ap.add_argument("modo", choices=["img", "vid"]); ap.add_argument("out"); ap.add_argument("prompt")
ap.add_argument("--ref"); ap.add_argument("--res", default="2k"); ap.add_argument("--modelo")
a = ap.parse_args()
if a.modo == "img":
    m = a.modelo or "nano_banana_2_1"
    args = [m, "--prompt", a.prompt, "--aspect_ratio", "9:16", "--resolution", a.res]
    if a.ref: args += ["--image", a.ref]
else:
    m = a.modelo or "kling3_0_turbo"
    args = [m, "--prompt", a.prompt, "--start-image", a.ref, "--resolution", "1080p", "--aspect_ratio", "9:16", "--duration", "5"]
    if m == "kling4_0": args += ["--mode", "image-to-video"]
run = lambda *c: subprocess.run([HF, *c], capture_output=True, text=True)
costo = run("generate", "cost", *args).stdout.strip().splitlines()[-1:]
r = run("generate", "create", *args, "--json")
ids = re.findall(r"[0-9a-f]{8}-[0-9a-f-]{27}", r.stdout)
if not ids: sys.exit(f"{a.out}: no creo trabajo: {(r.stdout + r.stderr)[:400]}")
w = run("generate", "wait", ids[0], "--json")
m_ = re.search(r'"result_url":\s*"([^"]+)"', w.stdout)
urls = [m_.group(1)] if m_ else []
if not urls: sys.exit(f"{a.out}: sin resultado: {w.stdout[:600]}")
subprocess.run(["curl", "-sL", "-o", a.out, urls[0]], check=True)
json.dump({"modelo": m, "prompt": a.prompt, "ref": a.ref, "trabajo": ids[0], "costo": costo, "args": args[3:]},
          open(os.path.splitext(a.out)[0] + ".json", "w"), ensure_ascii=False, indent=1)
print(a.out, costo, os.path.getsize(a.out))
