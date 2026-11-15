#!/usr/bin/env python3
"""Cliente de ComfyUI (GB10, :8189) para la serie de Shorts. Corre EN la GB10.

  comfy_gb10.py t2i  --prompt "..." --seed 1 --out imagenes/t6.png
  comfy_gb10.py edit --img imagenes/t6.png --prompt "..." --seed 1 --out imagenes/t7.png
  comfy_gb10.py i2v  --img imagenes/t6.png --prompt "..." --seed 1 --out clips/t6.mp4

Modelos (todos Apache 2.0): Qwen-Image 2512 (t2i), Qwen-Image-Edit 2511 (edit),
Wan 2.2 I2V 14B alto+bajo ruido (i2v). Cada salida deja un .json al lado con la receta.
"""
import argparse, json, os, shutil, subprocess, sys, time, urllib.request, uuid

API = os.environ.get("COMFY", "http://127.0.0.1:8189")
COMFY_DIR = os.path.expanduser("~/Documents/bf-comfy/ComfyUI")
NEG_IMG = "text, watermark, logo, letters, blurry, low quality, plastic look, deformed leaves, extra pots, people, hands"
NEG_VID = ("色调艳丽，过曝，静态，细节模糊不清，字幕，风格，作品，画作，画面，静止，整体发灰，最差质量，低质量，"
           "JPEG压缩残留，丑陋的，残缺的，多余的手指，画得不好的手部，画得不好的脸部，畸形的，毁容的，形态畸形的肢体，"
           "手指融合，静止不动的画面，杂乱的背景，三条腿，背景人很多，倒着走, text, watermark, people, morphing, flicker")


def _post(path, data):
    req = urllib.request.Request(API + path, json.dumps(data).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def _get(path):
    return json.load(urllib.request.urlopen(API + path))


def correr(wf, espera=7200):
    pid = _post("/prompt", {"prompt": wf, "client_id": uuid.uuid4().hex})["prompt_id"]
    t0 = time.time()
    while time.time() - t0 < espera:
        h = _get(f"/history/{pid}")
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                sys.exit("ComfyUI error: " + json.dumps(st.get("messages", [])[-1:])[:1500])
            if st.get("completed"):
                return h[pid]["outputs"], time.time() - t0
        time.sleep(3)
    sys.exit("timeout")


def _salidas(outputs):
    out_dir = _get("/system_stats")["system"].get("argv", [])
    base = out_dir[out_dir.index("--output-directory") + 1] if "--output-directory" in out_dir else COMFY_DIR + "/output"
    fs = []
    for o in outputs.values():
        for im in o.get("images", []):
            fs.append(os.path.join(os.path.expanduser(base), im.get("subfolder", ""), im["filename"]))
    return sorted(fs)


def _subir(img):
    dst = os.path.join(COMFY_DIR, "input", "g_" + uuid.uuid4().hex[:8] + os.path.splitext(img)[1])
    shutil.copy(img, dst)
    return os.path.basename(dst)


def _receta(out, **kw):
    json.dump(kw, open(os.path.splitext(out)[0] + ".json", "w"), ensure_ascii=False, indent=1)


def t2i(a):
    wf = {
        "u": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2512_fp8_e4m3fn.safetensors", "weight_dtype": "default"}},
        "c": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "v": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "m": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["u", 0], "shift": a.shift}},
        "p": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["c", 0], "text": a.prompt}},
        "n": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["c", 0], "text": a.neg or NEG_IMG}},
        "l": {"class_type": "EmptySD3LatentImage", "inputs": {"width": a.w, "height": a.h, "batch_size": 1}},
        "k": {"class_type": "KSampler", "inputs": {"model": ["m", 0], "seed": a.seed, "steps": a.steps, "cfg": a.cfg,
              "sampler_name": "euler", "scheduler": "simple", "positive": ["p", 0], "negative": ["n", 0],
              "latent_image": ["l", 0], "denoise": 1.0}},
        "d": {"class_type": "VAEDecode", "inputs": {"samples": ["k", 0], "vae": ["v", 0]}},
        "s": {"class_type": "SaveImage", "inputs": {"images": ["d", 0], "filename_prefix": "t2i"}},
    }
    outs, s = correr(wf)
    shutil.move(_salidas(outs)[0], a.out)
    _receta(a.out, modo="t2i", modelo="qwen_image_2512_fp8_e4m3fn", prompt=a.prompt, neg=a.neg or NEG_IMG, seed=a.seed,
            steps=a.steps, cfg=a.cfg, shift=a.shift, w=a.w, h=a.h, sampler="euler/simple", segundos=round(s))
    print(f"{a.out}  {s:.0f}s")


def edit(a):
    wf = {
        "u": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_edit_2511_fp8mixed.safetensors", "weight_dtype": "default"}},
        "c": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_2.5_vl_7b_fp8_scaled.safetensors", "type": "qwen_image", "device": "default"}},
        "v": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_vae.safetensors"}},
        "m": {"class_type": "ModelSamplingAuraFlow", "inputs": {"model": ["u", 0], "shift": a.shift}},
        "i": {"class_type": "LoadImage", "inputs": {"image": _subir(a.img)}},
        "p": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["c", 0], "prompt": a.prompt, "vae": ["v", 0], "image1": ["i", 0]}},
        "n": {"class_type": "TextEncodeQwenImageEditPlus", "inputs": {"clip": ["c", 0], "prompt": a.neg or NEG_IMG, "vae": ["v", 0], "image1": ["i", 0]}},
        "l": {"class_type": "EmptySD3LatentImage", "inputs": {"width": a.w, "height": a.h, "batch_size": 1}},
        "k": {"class_type": "KSampler", "inputs": {"model": ["m", 0], "seed": a.seed, "steps": a.steps, "cfg": a.cfg,
              "sampler_name": "euler", "scheduler": "simple", "positive": ["p", 0], "negative": ["n", 0],
              "latent_image": ["l", 0], "denoise": 1.0}},
        "d": {"class_type": "VAEDecode", "inputs": {"samples": ["k", 0], "vae": ["v", 0]}},
        "s": {"class_type": "SaveImage", "inputs": {"images": ["d", 0], "filename_prefix": "edit"}},
    }
    outs, s = correr(wf)
    shutil.move(_salidas(outs)[0], a.out)
    _receta(a.out, modo="edit", modelo="qwen_image_edit_2511_fp8mixed", base=a.img, prompt=a.prompt, seed=a.seed,
            steps=a.steps, cfg=a.cfg, shift=a.shift, w=a.w, h=a.h, segundos=round(s))
    print(f"{a.out}  {s:.0f}s")


def i2v(a):
    alto, bajo = "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors"
    wf = {
        "c": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "v": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        "uh": {"class_type": "UNETLoader", "inputs": {"unet_name": alto, "weight_dtype": "default"}},
        "ul": {"class_type": "UNETLoader", "inputs": {"unet_name": bajo, "weight_dtype": "default"}},
        "mh": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["uh", 0], "shift": a.shift}},
        "ml": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["ul", 0], "shift": a.shift}},
        "p": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["c", 0], "text": a.prompt}},
        "n": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["c", 0], "text": a.neg or NEG_VID}},
        "i": {"class_type": "LoadImage", "inputs": {"image": _subir(a.img)}},
        "w": {"class_type": "WanImageToVideo", "inputs": {"positive": ["p", 0], "negative": ["n", 0], "vae": ["v", 0],
              "width": a.w, "height": a.h, "length": a.frames, "batch_size": 1, "start_image": ["i", 0]}},
        "kh": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["mh", 0], "add_noise": "enable", "noise_seed": a.seed,
               "steps": a.steps, "cfg": a.cfg, "sampler_name": "euler", "scheduler": "simple", "positive": ["w", 0],
               "negative": ["w", 1], "latent_image": ["w", 2], "start_at_step": 0, "end_at_step": a.steps // 2,
               "return_with_leftover_noise": "enable"}},
        "kl": {"class_type": "KSamplerAdvanced", "inputs": {"model": ["ml", 0], "add_noise": "disable", "noise_seed": a.seed,
               "steps": a.steps, "cfg": a.cfg, "sampler_name": "euler", "scheduler": "simple", "positive": ["w", 0],
               "negative": ["w", 1], "latent_image": ["kh", 0], "start_at_step": a.steps // 2, "end_at_step": 10000,
               "return_with_leftover_noise": "disable"}},
        "d": {"class_type": "VAEDecode", "inputs": {"samples": ["kl", 0], "vae": ["v", 0]}},
        "s": {"class_type": "SaveImage", "inputs": {"images": ["d", 0], "filename_prefix": "i2v_" + uuid.uuid4().hex[:6] + "/f"}},
    }
    if a.rapido:  # LoRA lightx2v de 4 pasos: ~10x menos computo (la GB10 se calienta)
        for k, r in (("h", "high"), ("l", "low")):
            wf["l" + k] = {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["u" + k, 0], "strength_model": 1.0,
                           "lora_name": f"wan2.2_i2v_lightx2v_4steps_lora_v1_{r}_noise.safetensors"}}
            wf["m" + k]["inputs"]["model"] = ["l" + k, 0]
        a.steps, a.cfg, a.shift = 4, 1.0, 5.0
        for k in ("kh", "kl"):
            wf[k]["inputs"].update(steps=4, cfg=1.0)
        wf["kh"]["inputs"]["end_at_step"] = 2
        wf["kl"]["inputs"]["start_at_step"] = 2
        wf["mh"]["inputs"]["shift"] = wf["ml"]["inputs"]["shift"] = 5.0
    outs, s = correr(wf)
    fs = _salidas(outs)
    d = os.path.dirname(fs[0])
    lst = os.path.join(d, "l.txt")
    open(lst, "w").write("".join(f"file '{f}'\nduration {1/16}\n" for f in fs))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-r", "16",
                    "-c:v", "libx264", "-crf", "12", "-preset", "slow", "-pix_fmt", "yuv420p", a.out], check=True)
    shutil.rmtree(d)
    _receta(a.out, modo="i2v", modelo="wan2.2_i2v_14B_fp8_scaled alto+bajo", base=a.img, prompt=a.prompt, seed=a.seed,
            steps=a.steps, cfg=a.cfg, shift=a.shift, w=a.w, h=a.h, frames=a.frames, fps=16, segundos=round(s))
    print(f"{a.out}  {s:.0f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="modo", required=True)
    for nombre, fn, df in (("t2i", t2i, dict(w=928, h=1664, steps=50, cfg=4.0, shift=3.1)),
                           ("edit", edit, dict(w=928, h=1664, steps=40, cfg=4.0, shift=3.1)),
                           ("i2v", i2v, dict(w=720, h=1280, steps=20, cfg=3.5, shift=8.0))):
        p = sub.add_parser(nombre)
        p.add_argument("--prompt", required=True); p.add_argument("--neg", default="")
        p.add_argument("--seed", type=int, default=1); p.add_argument("--out", required=True)
        p.add_argument("--img"); p.add_argument("--frames", type=int, default=81)
        p.add_argument("--rapido", action="store_true")
        for k, v in df.items():
            p.add_argument("--" + k, type=type(v), default=v)
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)
