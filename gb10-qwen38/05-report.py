#!/usr/bin/env python3
"""Convierte ab-results.json en una comparativa lado a lado, legible.

La velocidad la decide una tabla de numeros. La calidad la decides tu leyendo
las dos respuestas a la misma tarea, una al lado de la otra. Eso es lo que
genera esto: un HTML autocontenido, sin dependencias, que abres en el navegador.

Uso:
    ./05-report.py                      # lee ab-results.json, escribe ab-report.html
    ./05-report.py --json otro.json --out otro.html
    ./05-report.py --markdown           # ademas escribe ab-report.md
"""

import argparse
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--muted:#666;--line:#e3e3e3;--card:#fafafa;
      --a:#0b6b3a;--b:#7a4a00;--code:#f4f4f4}
@media(prefers-color-scheme:dark){:root{--bg:#151515;--fg:#eaeaea;--muted:#9a9a9a;
      --line:#333;--card:#1e1e1e;--a:#6ee7a5;--b:#e8b464;--code:#242424}}
*{box-sizing:border-box}
body{margin:0;padding:2rem 1.25rem;background:var(--bg);color:var(--fg);
     font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     max-width:1200px;margin-inline:auto}
h1{font-size:1.5rem;margin:0 0 .25rem}
h2{font-size:1.05rem;margin:2.5rem 0 .75rem;padding-bottom:.4rem;
   border-bottom:1px solid var(--line)}
.sub{color:var(--muted);margin:0 0 2rem;font-size:.9rem}
table{border-collapse:collapse;width:100%;font-size:.9rem}
th,td{padding:.5rem .7rem;text-align:left;border-bottom:1px solid var(--line)}
th{font-weight:600;color:var(--muted);font-size:.8rem;text-transform:uppercase;
   letter-spacing:.03em}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.win{font-weight:650}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
@media(max-width:820px){.grid{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
      padding:.9rem 1rem;min-width:0}
.card h3{margin:0 0 .5rem;font-size:.82rem;text-transform:uppercase;
         letter-spacing:.04em}
.card.a h3{color:var(--a)} .card.b h3{color:var(--b)}
.task{background:var(--code);border-radius:6px;padding:.75rem .9rem;
      margin:0 0 1rem;white-space:pre-wrap;word-wrap:break-word;font-size:.88rem}
.out{white-space:pre-wrap;word-wrap:break-word;overflow-x:auto;margin:0;
     font:13px/1.55 ui-monospace,SFMono-Regular,Menlo,monospace}
.meta{color:var(--muted);font-size:.78rem;margin-top:.7rem;
      padding-top:.5rem;border-top:1px solid var(--line)}
.none{color:var(--muted);font-style:italic}
.note{background:var(--card);border-left:3px solid var(--muted);
      padding:.8rem 1rem;border-radius:0 6px 6px 0;font-size:.88rem;margin:1.5rem 0}
"""


def esc(x):
    return html.escape(str(x if x is not None else ""))


def fmt(v, suffix="", dash="—"):
    return f"{v}{suffix}" if isinstance(v, (int, float)) else dash


def med(entries, key):
    vals = [e["summary"][key] for e in entries
            if e["summary"].get("ok") and isinstance(e["summary"].get(key), (int, float))]
    if not vals:
        return None
    vals.sort()
    n = len(vals)
    return round(vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2, 2)


def build_html(d):
    a, b = d["model_a_new"], d["model_b_old"]
    ra, rb = d["results"].get(a, []), d["results"].get(b, [])
    mem = d.get("resident_mb", {}) or {}

    rows = []
    metrics = [("wall_p50", "Latencia p50", "s", "lower"),
               ("wall_p95", "Latencia p95", "s", "lower"),
               ("tps_p50", "Throughput p50", " tok/s", "higher"),
               ("ttft_p50", "Prefill p50", "s", "lower")]
    for key, label, suf, better in metrics:
        va, vb = med(ra, key), med(rb, key)
        cls_a = cls_b = ""
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            a_wins = va < vb if better == "lower" else va > vb
            cls_a, cls_b = ("win", "") if a_wins else ("", "win")
        rows.append(f"<tr><td>{esc(label)}</td>"
                    f"<td class='num {cls_a}'>{fmt(va, suf)}</td>"
                    f"<td class='num {cls_b}'>{fmt(vb, suf)}</td></tr>")

    ma, mb = mem.get(a), mem.get(b)
    rows.append("<tr><td>Memoria residente</td>"
                f"<td class='num'>{f'{ma / 1024:.1f} GB' if ma else '—'}</td>"
                f"<td class='num'>{f'{mb / 1024:.1f} GB' if mb else '—'}</td></tr>")

    blocks = []
    by_b = {e["prompt_index"]: e for e in rb}
    for ea in ra:
        eb = by_b.get(ea["prompt_index"], {})
        cards = []
        for cls, label, entry in (("a", f"A · {a}", ea), ("b", f"B · {b}", eb)):
            out = entry.get("sample_output")
            s = entry.get("summary", {})
            body = (f"<pre class='out'>{esc(out)}</pre>" if out
                    else "<p class='none'>sin respuesta (todas las corridas fallaron)</p>")
            meta = (f"p50 {fmt(s.get('wall_p50'), 's')} · "
                    f"{fmt(s.get('tps_p50'), ' tok/s')} · "
                    f"{fmt(s.get('output_tokens_p50'), ' tokens')}"
                    if s.get("ok") else "sin datos")
            cards.append(f"<div class='card {cls}'><h3>{esc(label)}</h3>{body}"
                         f"<div class='meta'>{esc(meta)}</div></div>")
        blocks.append(
            f"<h2>Tarea {ea['prompt_index']}</h2>"
            f"<div class='task'>{esc(ea['prompt'])}</div>"
            f"<div class='grid'>{''.join(cards)}</div>")

    nerr = len(d.get("errors", []))
    err_note = (f"<div class='note'><strong>{nerr} llamada(s) fallaron.</strong> "
                "Revisa <code>errors</code> en el JSON antes de fiarte de los números."
                "</div>") if nerr else ""

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>A/B — {esc(a)} vs {esc(b)}</title><style>{CSS}</style></head><body>
<h1>Comparativa A/B</h1>
<p class="sub">{esc(d.get('generated_at', ''))} · {len(ra)} tarea(s) ·
{esc(d.get('runs_per_prompt'))} medida(s) por tarea ·
warm-up {esc(d.get('warmup', 0))} · concurrencia {esc(d.get('concurrency', 1))}</p>
{err_note}
<h2>Rendimiento</h2>
<table><thead><tr><th>Métrica</th>
<th style="text-align:right">A · {esc(a)}</th>
<th style="text-align:right">B · {esc(b)}</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<div class="note">La tabla decide la <strong>velocidad</strong>. La
<strong>calidad</strong> la decides tú abajo: misma tarea, las dos respuestas
lado a lado. Si el nuevo no gana claramente en tus tareas, no cambies.</div>
{''.join(blocks)}
</body></html>"""


def build_markdown(d):
    a, b = d["model_a_new"], d["model_b_old"]
    ra, rb = d["results"].get(a, []), d["results"].get(b, [])
    by_b = {e["prompt_index"]: e for e in rb}
    L = [f"# Comparativa A/B", "",
         f"- **A (nuevo):** `{a}`", f"- **B (viejo):** `{b}`",
         f"- Generado: {d.get('generated_at','')}", "",
         "| Métrica | A | B |", "|---|---:|---:|"]
    for key, label, suf in [("wall_p50", "Latencia p50", "s"),
                            ("wall_p95", "Latencia p95", "s"),
                            ("tps_p50", "Throughput p50", " tok/s")]:
        L.append(f"| {label} | {fmt(med(ra, key), suf)} | {fmt(med(rb, key), suf)} |")
    L.append("")
    for ea in ra:
        eb = by_b.get(ea["prompt_index"], {})
        L += [f"## Tarea {ea['prompt_index']}", "", "```", ea["prompt"], "```", "",
              f"**A · {a}**", "", "```", str(ea.get("sample_output") or "(sin respuesta)"), "```", "",
              f"**B · {b}**", "", "```", str(eb.get("sample_output") or "(sin respuesta)"), "```", ""]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", default=os.path.join(HERE, "ab-results.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "ab-report.html"))
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.json):
        sys.exit(f"ERROR: no encuentro {args.json}\nCorre primero ./03-ab-eval.py")
    with open(args.json, encoding="utf-8") as fh:
        d = json.load(fh)

    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(build_html(d))
    print(f"HTML:     {args.out}")

    if args.markdown:
        md = os.path.splitext(args.out)[0] + ".md"
        with open(md, "w", encoding="utf-8") as fh:
            fh.write(build_markdown(d))
        print(f"Markdown: {md}")

    print("\nAbrelo en el navegador y compara las respuestas lado a lado.")


if __name__ == "__main__":
    main()
