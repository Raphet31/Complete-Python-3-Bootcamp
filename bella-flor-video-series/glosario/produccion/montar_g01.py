#!/usr/bin/env python3
"""Montaje del Short G01 «Adivina la flor en 3 pistas · Pascua». Corre en la GB10 (CPU, sin GPU).

  python3 montar_g01.py            -> G01/G01-pascua-final.mp4 + portadas
  python3 montar_g01.py --hoja     -> ademas saca logs/hoja_final.png (un cuadro por toma)

Entradas: G01/clips/t{1,2,3,6,7,8}.mp4, G01/imagenes/portada.png, assets/fuentes, assets/banderas.
Todo el sonido se sintetiza aqui con numpy (original, sin samples de terceros).
Zona segura: nada de texto en los 350 px de abajo ni en los 170 px de la derecha.
"""
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal
from scipy.io import wavfile

B = os.path.dirname(os.path.abspath(__file__))
G = f"{B}/G01"; A = f"{B}/assets"
W, H, FPS = 1080, 1920, 30
CX = 488                      # centro del texto: zona segura = x 60..910 (ancho util 850)
ORO, CREMA, VINO = (226, 190, 110), (250, 240, 222), (120, 14, 26)
PF, PFI, MS = f"{A}/fuentes/PlayfairDisplay.ttf", f"{A}/fuentes/PlayfairDisplay-Italic.ttf", f"{A}/fuentes/Montserrat.ttf"

PISTAS = [("PISTA 1", ["Esto amarillo es", "la flor de verdad."], "Lo demás son hojas."),
          ("PISTA 2", ["Los aztecas la usaban", "para hacer tinte rojo."], None),
          ("PISTA 3", ["Solo la ves", "en diciembre."], None)]
NOMBRES = [("us", "ESTADOS UNIDOS", "Poinsettia"), ("mx", "MÉXICO", "Nochebuena"), ("pr", "PUERTO RICO", "Pascua")]

# ------------------------------------------------------------------ utilidades
def fuente(ruta, tam, peso=None):
    f = ImageFont.truetype(ruta, tam)
    if peso:
        try: f.set_variation_by_axes([peso])
        except Exception: pass
    return f

def suave(t): t = min(max(t, 0.0), 1.0); return 1 - (1 - t) ** 3
def rebote(t):
    t = min(max(t, 0.0), 1.0); c = 1.70158 * 1.4
    return 1 + (c + 1) * (t - 1) ** 3 + c * (t - 1) ** 2

def texto(lineas, f, color=(255, 255, 255), espacio=0, interlinea=1.12, sombra=18, trazo=0):
    """Sprite RGBA con texto centrado y sombra suave. lineas: lista de str."""
    d = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    def ancho(s): return sum(d.textlength(c, font=f) + espacio for c in s) - espacio if espacio else d.textlength(s, font=f)
    asc, desc = f.getmetrics(); alto = int((asc + desc) * interlinea)
    w = int(max(ancho(s) for s in lineas)) + 2 * sombra + 40; h = alto * len(lineas) + 2 * sombra + 40
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dd = ImageDraw.Draw(capa)
    for i, s in enumerate(lineas):
        x = (w - ancho(s)) / 2; y = sombra + 20 + i * alto
        if espacio:
            for c in s:
                dd.text((x, y), c, font=f, fill=color); x += d.textlength(c, font=f) + espacio
        else:
            dd.text((x, y), s, font=f, fill=color, stroke_width=trazo, stroke_fill=color)
    if sombra:
        a = capa.getchannel("A").filter(ImageFilter.GaussianBlur(sombra * 0.55)).point(lambda v: min(255, int(v * 0.85)))
        s2 = Image.new("RGBA", (w, h), (0, 0, 0, 0)); s2.putalpha(a)
        fondo = Image.new("RGBA", (w, h), (0, 0, 0, 0)); fondo.alpha_composite(s2, (0, 6)); fondo.alpha_composite(capa)
        capa = fondo
    return capa

def tx(lineas, ruta, tam, peso, maxw=830, **kw):
    """texto() que baja el tamano hasta caber en la zona segura."""
    while True:
        sp = texto(lineas, fuente(ruta, tam, peso), **kw)
        if sp.width - 2 * kw.get("sombra", 18) - 40 <= maxw or tam < 30: return sp
        tam = int(tam * 0.95)

def poner(cuadro, sp, cx, cy, alfa=1.0, escala=1.0):
    if alfa <= 0.004: return
    if abs(escala - 1) > 0.002:
        sp = sp.resize((max(1, int(sp.width * escala)), max(1, int(sp.height * escala))), Image.LANCZOS)
    if alfa < 0.996:
        sp = sp.copy(); sp.putalpha(sp.getchannel("A").point(lambda v: int(v * alfa)))
    cuadro.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))

def degradado(y0, y1, a0, a1):
    al = np.zeros((H, W), np.float32); ys = np.arange(H, dtype=np.float32)
    t = np.clip((ys - y0) / max(1, y1 - y0), 0, 1); al[:] = (a0 + (a1 - a0) * t)[:, None]
    al[ys < min(y0, y1)] = a0 if y0 < y1 else a1; al[ys > max(y0, y1)] = a1 if y0 < y1 else a0
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.putalpha(Image.fromarray((al * 255).astype(np.uint8))); return im

def vineta(fuerza=0.42):
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((x - W / 2) / (W * 0.78)) ** 2 + ((y - H / 2) / (H * 0.70)) ** 2)
    al = np.clip((r - 0.55) / 0.6, 0, 1) ** 1.6 * fuerza
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); im.putalpha(Image.fromarray((al * 255).astype(np.uint8))); return im

def cargar(nombre, lento=1.0):
    """Clip -> lista de cuadros RGB 1080x1920 a 30 fps, interpolando movimiento (24 -> 30 y camara lenta)."""
    prep = f"{G}/prep/{nombre}_{lento}.mp4"; os.makedirs(f"{G}/prep", exist_ok=True)
    if not os.path.exists(prep):
        vf = (f"setpts={lento}*PTS,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,"
              f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", f"{G}/clips/{nombre}.mp4", "-an", "-vf", vf,
                        "-c:v", "libx264", "-crf", "10", "-preset", "medium", "-pix_fmt", "yuv420p", prep], check=True)
    crudo = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", prep, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                           capture_output=True, check=True).stdout
    n = len(crudo) // (W * H * 3)
    return np.frombuffer(crudo, np.uint8)[: n * W * H * 3].reshape(n, H, W, 3)

def zoom(img, z):
    if z <= 1.001: return img
    w, h = int(W / z), int(H / z); x, y = (W - w) // 2, (H - h) // 2
    return img.resize((W, H), Image.BICUBIC, box=(x, y, x + w, y + h))

# ------------------------------------------------------------------ piezas fijas
def piezas():
    P = {}
    P["grad_arriba"] = degradado(0, 760, 0.72, 0.0); P["grad_abajo"] = degradado(900, 1700, 0.0, 0.78)
    P["vineta"] = vineta()
    P["gancho"] = tx(["¿ADIVINAS", "LA FLOR"], PF, 148, 900, interlinea=1.02, sombra=26)
    P["gancho2"] = tx(["EN 3 PISTAS?"], MS, 62, 800, color=ORO, espacio=9, sombra=14)
    for i, (chip, lin, sub) in enumerate(PISTAS):
        P[f"chip{i}"] = tx([chip], MS, 46, 800, color=ORO, espacio=12, sombra=12)
        P[f"de{i}"] = tx(["DE 3"], MS, 26, 600, color=(255, 255, 255), espacio=8, sombra=8)
        P[f"pista{i}"] = tx(lin, PF, 78, 800, sombra=22)
        if sub: P[f"sub{i}"] = tx([sub], PFI, 62, 600, color=ORO, sombra=18)
    for n in "321": P[f"n{n}"] = texto([n], fuente(PF, 640, 900), ORO, sombra=40)
    P["rev"] = tx(["¡LA PASCUA!"], PF, 150, 900, sombra=28)
    P["rev2"] = tx(["Euphorbia pulcherrima"], PFI, 60, 500, color=CREMA, sombra=16)
    fp, fn = fuente(MS, 28, 700), fuente(PF, 66, 800)
    for k, pais, nom in NOMBRES:
        t = Image.new("RGBA", (760, 170), (0, 0, 0, 0)); d = ImageDraw.Draw(t)
        som = Image.new("RGBA", t.size, (0, 0, 0, 0)); ImageDraw.Draw(som).rounded_rectangle((20, 24, 740, 156), 36, fill=(60, 30, 10, 90))
        t.alpha_composite(som.filter(ImageFilter.GaussianBlur(12)))
        d.rounded_rectangle((20, 14, 740, 146), 36, fill=(255, 255, 255, 246))
        b = Image.open(f"{A}/banderas/{k}.png").convert("RGBA").resize((92, 92), Image.LANCZOS); t.alpha_composite(b, (48, 34))
        x = 168
        for c in pais: d.text((x, 34), c, font=fp, fill=(150, 120, 70)); x += d.textlength(c, font=fp) + 5
        d.text((166, 60), nom, font=fn, fill=VINO); P[f"tarjeta_{k}"] = t
    P["cta"] = tx(["¿EN CUÁL PISTA", "LA ADIVINASTE?"], PF, 88, 900, interlinea=1.06, sombra=24)
    P["cta2"] = tx(["COMENTA"], MS, 40, 800, color=CREMA, espacio=12, sombra=12)
    fb = fuente(PF, 92, 900)
    for n in "123":
        c = Image.new("RGBA", (190, 190), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
        som = Image.new("RGBA", c.size, (0, 0, 0, 0)); ImageDraw.Draw(som).ellipse((22, 30, 168, 176), fill=(0, 0, 0, 150))
        c.alpha_composite(som.filter(ImageFilter.GaussianBlur(10))); d.ellipse((22, 20, 168, 166), fill=ORO + (255,), outline=(255, 245, 215), width=4)
        bb = d.textbbox((0, 0), n, font=fb); d.text((95 - (bb[0] + bb[2]) / 2, 93 - (bb[1] + bb[3]) / 2), n, font=fb, fill=(70, 8, 14))
        P[f"c{n}"] = c
    return P

def barra(cuadro, frac, y=336, ancho=560, alfa=1.0):
    """Barra de tiempo que se vacia (frac 1 -> 0)."""
    capa = Image.new("RGBA", (ancho + 20, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(capa)
    d.rounded_rectangle((10, 10, ancho + 10, 20), 5, fill=(255, 255, 255, 70))
    if frac > 0.01: d.rounded_rectangle((10, 10, 10 + max(10, int(ancho * frac)), 20), 5, fill=ORO + (255,))
    poner(cuadro, capa, CX, y, alfa)

# ------------------------------------------------------------------ tomas
def render(salida_cruda, hoja=None):
    P = piezas()
    c1, c2, c3 = cargar("t1"), cargar("t2", 1.2), cargar("t3", 1.2)
    c6, c8 = cargar("t6"), cargar("t8")
    muestras = {}
    def emitir(im, n):
        salida_cruda.write(im.convert("RGB").tobytes())
        if hoja is not None and n in hoja: muestras[n] = im.convert("RGB").resize((270, 480), Image.LANCZOS)
    n = 0
    # --- 1 · gancho 0:00-0:03 (el cuadro 0 es la portada: todo el texto ya visible)
    for i in range(90):
        t = i / FPS; im = Image.fromarray(c1[min(i, len(c1) - 1)]).convert("RGBA")
        im.alpha_composite(P["grad_arriba"]); im.alpha_composite(P["vineta"])
        golpe = 1.0 + 0.07 * max(0, 1 - abs(t - 0.10) / 0.22) if t > 0.03 else 1.0
        late = 1 + 0.015 * np.sin(t * 2 * np.pi * 1.0)
        poner(im, P["gancho"], CX, 380, 1.0, golpe * late)
        poner(im, P["gancho2"], CX, 1505, 1.0, 1.0 + 0.03 * np.sin(t * 2 * np.pi * 2.0))
        emitir(im, n); n += 1
    # --- 2,3,4 · pistas, 6 s cada una
    for k, clip in enumerate([c2, c3, None]):
        borroso = None
        for i in range(180):
            t = i / FPS
            if clip is not None:
                im = Image.fromarray(clip[min(i, len(clip) - 1)]).convert("RGBA")
            else:  # pista 3 = la revelacion fuera de foco, corriendo hacia atras hasta el cuadro 0
                j = int(round((1 - i / 179) * 60)); base = Image.fromarray(c6[j])
                im = zoom(base.filter(ImageFilter.GaussianBlur(42)), 1.0 + 0.06 * i / 179).convert("RGBA")
            im.alpha_composite(P["grad_arriba"]); im.alpha_composite(P["grad_abajo"]); im.alpha_composite(P["vineta"])
            e = suave(t / 0.35); sal = 1 - suave((t - 5.8) / 0.2)
            poner(im, P[f"chip{k}"], CX, 232 - 20 * (1 - e), e * sal)
            poner(im, P[f"de{k}"], CX, 286, e * sal * 0.85)
            barra(im, 1 - t / 6.0, alfa=e * sal)
            e2 = suave((t - 0.25) / 0.45)
            ty = 1300 if f"sub{k}" in P else 1340
            poner(im, P[f"pista{k}"], CX, ty + 30 * (1 - e2), e2 * sal)
            if f"sub{k}" in P:
                e3 = suave((t - 1.6) / 0.45); poner(im, P[f"sub{k}"], CX, 1478 + 24 * (1 - e3), e3 * sal)
            if i < 4: im = Image.blend(im, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.35 * (1 - i / 4))
            emitir(im, n); n += 1
    # --- 5 · conteo 0:21-0:23
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    halo = np.clip(1 - np.sqrt((x - W / 2) ** 2 + (y - 900) ** 2) / 900, 0, 1) ** 2
    for i in range(60):
        k, r = divmod(i, 20); t = r / 20
        f = (halo * (70 + 40 * (1 - t)))[..., None] * np.array([1.0, 0.08, 0.12], np.float32)
        im = Image.fromarray(f.astype(np.uint8)).convert("RGBA")
        poner(im, P[f"n{'321'[k]}"], W / 2, 880, min(1, t / 0.15) * (1 - max(0, (t - 0.8) / 0.2)), 1.45 - 0.45 * suave(t / 0.3) - 0.05 * t)
        emitir(im, n); n += 1
    # --- 6 · revelacion 0:23-0:28
    for i in range(150):
        t = i / FPS; base = Image.fromarray(c6[min(i, len(c6) - 1)])
        r = 42 * (1 - suave(t / 0.4))
        if r > 0.4: base = base.filter(ImageFilter.GaussianBlur(r))
        im = zoom(base, 1.06 - 0.06 * suave(t / 0.6)).convert("RGBA")
        im.alpha_composite(P["grad_arriba"]); im.alpha_composite(P["vineta"])
        if i < 9: im = Image.blend(im, Image.new("RGBA", (W, H), (255, 244, 220, 255)), 0.75 * (1 - i / 9) ** 1.5)
        e = (t - 0.35) / 0.4
        if e > 0: poner(im, P["rev"], CX, 300, min(1, e * 2.2), 0.7 + 0.3 * rebote(e))
        e2 = suave((t - 0.95) / 0.5); poner(im, P["rev2"], CX, 432 + 16 * (1 - e2), e2)
        emitir(im, n); n += 1
    # --- 7 · nombres 0:28-0:31 (la imagen ya trae el tercio de arriba en crema para las tarjetas)
    fijo7 = Image.open(f"{G}/imagenes/t7.png").convert("RGB").resize((W, 1935), Image.LANCZOS).crop((0, 8, W, 8 + H))
    for i in range(90):
        t = i / FPS; im = zoom(fijo7, 1.0 + 0.035 * t / 3).convert("RGBA")   # foto fija con zoom leve: Kling se acercaba demasiado
        for j, (k, _, _) in enumerate(NOMBRES):
            e = (t - (0.2 + 0.7 * j)) / 0.32
            if e > 0: poner(im, P[f"tarjeta_{k}"], CX, 250 + 166 * j, min(1, e * 2.5), 0.6 + 0.4 * rebote(e))
        if i < 5: im = Image.blend(im, Image.new("RGBA", (W, H), (255, 250, 240, 255)), 0.5 * (1 - i / 5))
        emitir(im, n); n += 1
    # --- 8 · cierre 0:31-0:34
    grad = degradado(0, 900, 0.80, 0.0)
    for i in range(90):
        t = i / FPS; im = Image.fromarray(c8[min(i, len(c8) - 1)]).convert("RGBA")
        im.alpha_composite(grad); im.alpha_composite(P["vineta"])
        e = suave(t / 0.4); poner(im, P["cta"], CX, 238 + 26 * (1 - e), e)
        e2 = suave((t - 0.5) / 0.35); poner(im, P["cta2"], CX, 404, e2)
        for j, nn in enumerate("123"):
            ej = (t - (0.75 + 0.22 * j)) / 0.3
            if ej > 0: poner(im, P[f"c{nn}"], CX + (j - 1) * 200, 512, min(1, ej * 3), (0.5 + 0.5 * rebote(ej)) * (1 + 0.04 * np.sin((t - j * 0.2) * 2 * np.pi * 1.6)))
        if i < 5: im = Image.blend(im, Image.new("RGBA", (W, H), (255, 250, 240, 255)), 0.4 * (1 - i / 5))
        emitir(im, n); n += 1
    return muestras

# ------------------------------------------------------------------ sonido (todo sintetizado)
SR = 44100
def sonido(ruta):
    N = SR * 34; mix = np.zeros((N, 2), np.float64); rng = np.random.default_rng(7)
    def env(n, a=0.005, d=0.3): t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / d)
    def suma(s, t0, g=1.0, pan=0.0):
        i = int(t0 * SR); s = s[: max(0, N - i)]
        mix[i:i + len(s), 0] += s * g * (1 - max(0, pan)); mix[i:i + len(s), 1] += s * g * (1 + min(0, pan))
    def filtro(s, f, tipo="low"): b, a = signal.butter(2, np.asarray(f, float) / (SR / 2), tipo); return signal.lfilter(b, a, s)
    def seno(f, dur): return np.sin(2 * np.pi * f * np.arange(int(dur * SR)) / SR)
    def golpe(f0=95, f1=36, dur=1.4):
        t = np.arange(int(dur * SR)) / SR; f = f1 + (f0 - f1) * np.exp(-t / 0.09)
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.45)
        return s + filtro(rng.standard_normal(len(t)), 900) * np.exp(-t / 0.05) * 0.5
    def tic(alto=True):
        n = int(0.05 * SR); f = 2600 if alto else 1900
        return (filtro(rng.standard_normal(n), [f * 0.8, f * 1.25], "band") * 3 + seno(f, 0.05) * 0.4) * env(n, 0.0005, 0.009)
    def campana(f, dur=1.6):
        t = np.arange(int(dur * SR)) / SR
        return sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t / d) for m, a, d in ((1, 1, .9), (2.76, .5, .5), (5.4, .25, .25), (8.9, .12, .12))) * np.minimum(1, t / 0.002)
    def cuerda(f, dur=1.8, brillo=0.5):
        """Cuerda pulsada (Karplus-Strong), doble cuerda algo desafinada como un cuatro."""
        def una(ff):
            p = int(SR / ff); n = int(dur * SR); buf = filtro(rng.uniform(-1, 1, p), 6000 * brillo + 1500); out = np.empty(n)
            for i in range(n):
                out[i] = buf[i % p]; buf[i % p] = 0.996 * 0.5 * (buf[i % p] + buf[(i + 1) % p])
            return out
        return (una(f) + una(f * 1.004) * 0.8) * 0.5
    def pop():
        t = np.arange(int(0.11 * SR)) / SR; f = 380 + 900 * (t / 0.11) ** 0.6
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.035) * np.minimum(1, t / 0.002)
    def coqui():
        co = seno(1180, 0.11) * np.hanning(int(0.11 * SR))
        t = np.arange(int(0.20 * SR)) / SR; f = 1900 + 850 * (t / 0.20) ** 0.7
        qui = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.hanning(len(t))
        return np.concatenate([co * 0.7, np.zeros(int(0.07 * SR)), qui])
    # gancho
    suma(golpe(), 0.0, 0.95); suma(campana(293.66, 2.5), 0.02, 0.10)
    # tension: pad en Re menor que crece hasta el conteo
    t = np.arange(int(21 * SR)) / SR
    pad = sum(np.sin(2 * np.pi * f * t + ph) * (1 + 0.3 * np.sin(2 * np.pi * r * t)) for f, ph, r in ((73.42, 0, .13), (110, 1, .17), (146.83, 2, .11), (174.61, 3, .19), (220, 4, .23)))
    pad = filtro(pad, 700) * (0.25 + 0.75 * (t / 21) ** 1.5) * np.minimum(1, t / 1.5) * np.minimum(1, (21 - t) / 0.15)
    suma(pad, 0, 0.045, 0.2); suma(np.roll(pad, 400), 0, 0.045, -0.2)
    # tic-tac: cada 0.5 s; en la pista 3 se acelera
    tt, k = 0.5, 0
    while tt < 20.95:
        suma(tic(k % 2 == 0), tt, 0.30 + 0.25 * tt / 21, 0.25 if k % 2 else -0.25); k += 1
        tt += 0.5 if tt < 15 else (1 / 3 if tt < 19 else 0.25)
    for i, t0 in enumerate((3.0, 9.0, 15.0)):
        suma(campana((587.33, 698.46, 880.0)[i], 1.8), t0, 0.16); suma(golpe(70, 40, 0.5), t0, 0.35)
    # pista 2: tambor suave
    for b in np.arange(9.0, 14.9, 0.75):
        suma(golpe(120, 70, 0.4), b, 0.22); suma(golpe(150, 95, 0.25), b + 0.5, 0.10)
    # pista 3: campanitas
    esc = [880, 1174.66, 1396.91, 1760, 1396.91, 1174.66, 1318.51, 1760]
    for i, b in enumerate(np.arange(15.15, 20.8, 1 / 3)):
        suma(campana(esc[i % 8] * 1.5, 0.9), b, 0.045 + 0.02 * (i % 2), 0.4 * np.sin(i))
    # conteo: tres golpes que suben
    for i, f in enumerate((146.83, 174.61, 220.0)):
        t0 = 21 + i * (2 / 3); suma(golpe(110 + 20 * i, 42, 0.6), t0, 0.55); suma(campana(f * 2, 0.6), t0, 0.14)
    # subida de aire antes de revelar
    n = int(0.45 * SR); sub = filtro(rng.standard_normal(n), 5000) * (np.arange(n) / n) ** 3
    suma(sub, 22.55, 0.25)
    # revelacion: acorde de Re mayor rasgueado + campanas
    for i, f in enumerate((146.83, 220.0, 293.66, 369.99, 440.0, 587.33)):
        suma(cuerda(f, 3.2, 0.9), 23.0 + i * 0.018, 0.60, (i - 2.5) * 0.12)
    for f in (587.33, 880.0, 1174.66, 1479.98): suma(campana(f, 3.0), 23.0, 0.13)
    suma(golpe(80, 34, 1.6), 23.0, 0.8)
    plato = filtro(rng.standard_normal(int(2.2 * SR)), 5000, "high") * env(int(2.2 * SR), 0.004, 0.55); suma(plato, 23.0, 0.10)
    # cuatro: arpegio Re - Sol - Re - La - Re
    acordes = {24: (146.83, 220.0, 293.66, 369.99), 26: (196.0, 246.94, 293.66, 392.0), 28: (146.83, 220.0, 293.66, 369.99),
               30: (220.0, 277.18, 329.63, 440.0), 32: (146.83, 220.0, 293.66, 369.99)}
    patron = (0, 2, 1, 3, 2, 3, 1, 2)
    for t0, ac in acordes.items():
        for j in range(8 if t0 < 32 else 4):
            suma(cuerda(ac[patron[j]] * 2, 1.2, 0.7), t0 + j * 0.25, 0.46 if j % 4 == 0 else 0.34, 0.3 * ((j % 3) - 1))
        suma(cuerda(ac[0], 2.0, 0.4), t0, 0.45)
    for i, f in enumerate((293.66, 369.99, 440.0, 587.33, 739.99)): suma(cuerda(f, 2.5, 0.9), 33.0 + i * 0.02, 0.50)
    # pops de las tarjetas y coqui
    for i in range(3): suma(pop(), 28.2 + 0.7 * i, 0.7, (i - 1) * 0.3)
    for i in range(3): suma(pop(), 31.75 + 0.22 * i, 0.45, (i - 1) * 0.3)
    suma(coqui(), 31.35, 0.34, 0.45); suma(coqui(), 32.55, 0.28, -0.4); suma(coqui(), 33.35, 0.18, 0.5)
    # sala (reverb corta) + salida
    ir = rng.standard_normal(int(1.1 * SR)) * np.exp(-np.arange(int(1.1 * SR)) / (0.28 * SR)); ir /= np.sqrt((ir ** 2).sum())
    for c in (0, 1): mix[:, c] += signal.fftconvolve(mix[:, c], np.roll(ir, c * 113), mode="full")[:N] * 0.16
    fin = np.ones(N); m = int(0.7 * SR); fin[-m:] = np.linspace(1, 0, m) ** 1.5; mix *= fin[:, None]
    mix = np.tanh(mix * 1.3) / max(1e-9, np.abs(np.tanh(mix * 1.3)).max()) * 0.92
    wavfile.write(ruta, SR, (mix * 32767).astype(np.int16))

# ------------------------------------------------------------------ portadas
def portadas():
    base = Image.open(f"{G}/imagenes/portada.png").convert("RGB")
    t1 = tx(["¿LA ADIVINAS?"], PF, 118, 900, maxw=960, sombra=28); t2 = tx(["3 PISTAS"], MS, 84, 800, color=ORO, espacio=16, sombra=18)
    v = base.resize((W, H), Image.LANCZOS).convert("RGBA"); v.alpha_composite(degradado(0, 620, 0.55, 0)); v.alpha_composite(degradado(1250, 1920, 0, 0.6))
    poner(v, t1, W / 2, 150); poner(v, t2, W / 2, 1560); v.convert("RGB").save(f"{G}/G01-portada-1080x1920.jpg", quality=94)
    c = base.crop((0, 40, 1536, 1960)).resize((1080, 1350), Image.LANCZOS).convert("RGBA")
    c.alpha_composite(degradado(0, 520, 0.55, 0).crop((0, 0, 1080, 1350))); poner(c, t1.resize((int(t1.width * .9), int(t1.height * .9)), Image.LANCZOS), 540, 100); poner(c, t2, 540, 1265)
    c.convert("RGB").save(f"{G}/G01-portada-1080x1350.jpg", quality=94)
    f = base.resize((1280, 2293), Image.LANCZOS).crop((0, 700, 1280, 1420)).filter(ImageFilter.GaussianBlur(40))
    f = Image.eval(f, lambda p: int(p * 0.55)).convert("RGBA"); r = base.crop((120, 330, 1416, 2270)).resize((481, 720), Image.LANCZOS)
    f.paste(r, (760, 0))
    h1 = tx(["¿LA", "ADIVINAS?"], PF, 128, 900, interlinea=1.02, sombra=26); poner(f, h1, 390, 290); poner(f, tx(["3 PISTAS"], MS, 64, 800, color=ORO, espacio=14, sombra=16), 390, 560)
    f.convert("RGB").save(f"{G}/G01-portada-1280x720.jpg", quality=94)

if __name__ == "__main__":
    for k in ("us", "mx", "pr"):
        if not os.path.exists(f"{A}/banderas/{k}.png"):
            subprocess.run(["rsvg-convert", "-w", "256", f"{A}/banderas/{k}.svg", "-o", f"{A}/banderas/{k}.png"], check=True)
    os.makedirs(f"{G}/prep", exist_ok=True); sonido(f"{G}/prep_audio.wav")
    mudo = f"{G}/prep/mudo.mp4"
    enc = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                            "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
                            "-color_trc", "bt709", mudo], stdin=subprocess.PIPE)
    marcas = [0, 150, 330, 560, 636, 665, 694, 760, 800, 835, 900, 960, 1005]
    m = render(enc.stdin, set(marcas) if "--hoja" in sys.argv else None); enc.stdin.close(); enc.wait()
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", mudo, "-i", f"{G}/prep_audio.wav", "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-shortest", f"{G}/G01-pascua-final.mp4"], check=True)
    portadas()
    if m:
        hoja = Image.new("RGB", (270 * 7, 480 * 2), (20, 20, 20))
        for i, k in enumerate(marcas): hoja.paste(m[k], (270 * (i % 7), 480 * (i // 7)))
        os.makedirs(f"{B}/logs", exist_ok=True); hoja.save(f"{B}/logs/hoja_final.png")
    print("listo", f"{G}/G01-pascua-final.mp4")
