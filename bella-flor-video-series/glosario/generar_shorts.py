#!/usr/bin/env python3
"""Genera Shorts 9:16 de la serie "¿Cómo le dices tú?" a partir de episodios.json.

Uso:
    python3 generar_shorts.py                 # todos los episodios
    python3 generar_shorts.py G01 G04         # solo esos
    python3 generar_shorts.py --demo G01      # ignora "validar" (borrador interno)

Entradas:
    fotos/<foto>     foto vertical de la flor (si falta, usa una ilustración simple)
    musica/*.mp3     opcional; usa la primera que encuentre (con licencia)
Salidas:
    salida/<id>-<slug>.mp4   video listo para subir
    salida/<id>-<slug>.txt   título, descripción y hashtags

Requiere: Pillow y ffmpeg.
"""
import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE = Path(__file__).resolve().parent
W, H = 1080, 1920
FPS = 30
FADE = 0.35
DUR_HOOK, DUR_NOMBRE, DUR_CIERRE = 2.6, 2.1, 2.8

CREMA = (247, 242, 232)
VERDE = (31, 61, 43)
TEXTO_SUAVE = (110, 104, 92)

FONT_DIRS = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/truetype/liberation"]
FONTS = {
    "titulo": "DejaVuSerif-Bold.ttf",
    "nombre": "DejaVuSerif-Bold.ttf",
    "italic": "LiberationSerif-Italic.ttf",
    "label": "DejaVuSans.ttf",
}


def font(kind, size):
    custom = BASE / "fuentes" / f"{kind}.ttf"
    if custom.exists():
        return ImageFont.truetype(str(custom), size)
    for d in FONT_DIRS:
        p = Path(d) / FONTS[kind]
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def hex_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def fondo_foto(path):
    img = Image.open(path).convert("RGB")
    s = max(W / img.width, H / img.height)
    img = img.resize((math.ceil(img.width * s), math.ceil(img.height * s)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def fondo_ilustrado(color):
    """Flor estilizada sobre crema cuando no hay foto (solo para borradores)."""
    img = Image.new("RGB", (W, H), CREMA)
    c = hex_rgb(color)
    cx, cy = W // 2, 640
    for capa, (n, largo, ancho, alpha) in enumerate([(8, 330, 130, 150), (8, 250, 105, 210)]):
        petalo = Image.new("RGBA", (ancho, largo), (0, 0, 0, 0))
        ImageDraw.Draw(petalo).ellipse((0, 0, ancho - 1, largo - 1), fill=(*c, alpha))
        for i in range(n):
            ang = 360 / n * i + capa * (180 / n)
            rot = petalo.rotate(-ang, expand=True, resample=Image.BICUBIC)
            r = largo / 2
            px = cx + int(r * math.sin(math.radians(ang))) - rot.width // 2
            py = cy - int(r * math.cos(math.radians(ang))) - rot.height // 2
            img.paste(rot, (px, py), rot)
    d = ImageDraw.Draw(img)
    for i in range(7):
        a = math.radians(360 / 7 * i)
        x, y = cx + 28 * math.cos(a), cy + 28 * math.sin(a)
        d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=(222, 180, 40))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def envolver(draw, texto, f, ancho_max):
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if draw.textlength(prueba, font=f) <= ancho_max:
            actual = prueba
        else:
            lineas.append(actual)
            actual = p
    lineas.append(actual)
    return lineas


def tarjeta(fondo, label, principal, kind="nombre", size=96):
    """Panel crema en la zona segura (fuera de la UI de Shorts/Reels)."""
    img = fondo.copy()
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(panel)
    x0, x1, y0, y1 = 70, W - 170, 1120, 1520
    pd.rounded_rectangle((x0, y0, x1, y1), radius=36, fill=(*CREMA, 238))
    img.paste(panel, (0, 0), panel)
    d = ImageDraw.Draw(img)
    ancho = x1 - x0 - 100

    f_main = font(kind, size)
    lineas = envolver(d, principal, f_main, ancho)
    while len(lineas) > 3 and size > 56:
        size -= 8
        f_main = font(kind, size)
        lineas = envolver(d, principal, f_main, ancho)

    f_lab = font("label", 40)
    alto = (50 if label else 0) + len(lineas) * int(size * 1.18)
    y = y0 + ((y1 - y0) - alto) // 2
    if label:
        d.text((x0 + 50, y), label.upper(), font=f_lab, fill=TEXTO_SUAVE)
        y += 64
    for ln in lineas:
        d.text((x0 + 50, y), ln, font=f_main, fill=VERDE)
        y += int(size * 1.18)
    return img


def construir_tarjetas(ep, fondo):
    n = len(ep["nombres"])
    cards = [(tarjeta(fondo, "", f"Esta flor tiene {n} nombres", "titulo", 100), DUR_HOOK)]
    for item in ep["nombres"]:
        kind = "italic" if item.get("cientifico") else "nombre"
        cards.append((tarjeta(fondo, item["label"], item["nombre"], kind, 104), DUR_NOMBRE))
    cards.append((tarjeta(fondo, "Comenta tu país", "¿Y tú, cómo le dices?", "titulo", 96), DUR_CIERRE))
    return cards


def render(cards, salida, musica):
    with tempfile.TemporaryDirectory() as tmp:
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for i, (img, dur) in enumerate(cards):
            p = Path(tmp) / f"c{i:02d}.png"
            img.save(p)
            cmd += ["-loop", "1", "-t", f"{dur}", "-i", str(p)]
        total = sum(d for _, d in cards) - FADE * (len(cards) - 1)

        filtros = []
        for i, (_, dur) in enumerate(cards):
            frames = int(dur * FPS)
            filtros.append(
                f"[{i}:v]scale={W * 2}:{H * 2},"
                f"zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                f":d={frames}:s={W}x{H}:fps={FPS},setsar=1,format=yuv420p[v{i}]"
            )
        prev, offset = "v0", 0.0
        for i in range(1, len(cards)):
            offset += cards[i - 1][1] - FADE
            out = f"x{i}"
            filtros.append(f"[{prev}][v{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[{out}]")
            prev = out

        a = len(cards)
        if musica:
            cmd += ["-i", str(musica)]
            filtros.append(f"[{a}:a]atrim=0:{total:.3f},afade=t=in:d=0.5,"
                           f"afade=t=out:st={total - 1.2:.3f}:d=1.2,volume=0.8[a]")
        else:
            cmd += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
            filtros.append(f"[{a}:a]anull[a]")

        cmd += ["-filter_complex", ";".join(filtros), "-map", f"[{prev}]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", str(FPS),
                "-c:a", "aac", "-b:a", "160k", "-t", f"{total:.3f}", "-movflags", "+faststart", str(salida)]
        subprocess.run(cmd, check=True)
    return total


def texto_publicacion(ep):
    lineas = [f"{i['label']}: {i['nombre']}" for i in ep["nombres"]]
    return (f"{ep['titulo']}\n\n" + "\n".join(lineas) +
            "\n\n¿Cómo le dicen en tu país? Te leemos en los comentarios 👇\n\n" + ep["hashtags"] + "\n")


def main():
    args = sys.argv[1:]
    demo = "--demo" in args
    ids = {a for a in args if not a.startswith("--")}
    data = json.loads((BASE / "episodios.json").read_text(encoding="utf-8"))
    musica = next(iter(sorted((BASE / "musica").glob("*.mp3"))), None)
    out_dir = BASE / "salida"
    out_dir.mkdir(exist_ok=True)

    for ep in data["episodios"]:
        if ids and ep["id"] not in ids:
            continue
        pend = [i["nombre"] for i in ep["nombres"] if i.get("validar")]
        if pend and not demo:
            print(f"[{ep['id']}] SALTADO: falta validar {pend} (usa --demo para borrador)")
            continue
        foto = BASE / "fotos" / ep["foto"]
        fondo = fondo_foto(foto) if foto.exists() else fondo_ilustrado(ep["color"])
        nombre = f"{ep['id']}-{ep['slug']}"
        dur = render(construir_tarjetas(ep, fondo), out_dir / f"{nombre}.mp4", musica)
        (out_dir / f"{nombre}.txt").write_text(texto_publicacion(ep), encoding="utf-8")
        origen = "foto" if foto.exists() else "ilustración (falta foto)"
        print(f"[{ep['id']}] OK {nombre}.mp4 · {dur:.1f}s · fondo: {origen}")


if __name__ == "__main__":
    main()
