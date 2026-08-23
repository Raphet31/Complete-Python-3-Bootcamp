# Migración a Qwen3.8-27B en la GB10 (DGX Spark)

Paquete de scripts para evaluar y —si sale bien— adoptar **Qwen3.8-27B** en la
GB10, **sin borrar el modelo actual**.

Los scripts corren **en la GB10**, no aquí. Este repo solo los versiona.

---

## Antes de empezar: dos cosas que conviene saber

**1. Los 14 puntos son de otro modelo.**
Los benchmarks que circulan de "Qwen 3.8" son del **Qwen3.8-Max**: 2.4 billones
de parámetros (MoE, ~95B activos), contexto de 1M. Ese modelo **no cabe en la
GB10** — el techo del DGX Spark son 128GB unificados, unos ~200B parámetros con
cuantización agresiva. El Max está ~12× por encima.

El que sí corre aquí es el **27B denso**, que es un modelo distinto y no es el
que sacó esos números.

**2. Los números son de primera parte.**
A agosto de 2026, los scores publicados salen de la tabla de la propia Alibaba;
Artificial Analysis y los leaderboards de la comunidad todavía no lo habían
medido de forma independiente. Y en lo publicado, el Max **pierde** en varios
ejes: SWE-bench Pro 67.7 (12 puntos por debajo de Fable 5), HLE 43.6 (último
entre los cuatro flagships), #6 de 224 en BenchAlign.

Nada de esto quiere decir que el 27B sea malo — encaja muy bien en el Spark, y
NVFP4 es formato nativo de Blackwell (~1.5× más rápido que BF16). Solo quiere
decir que **la decisión hay que tomarla midiendo, no leyendo una tabla**.

Por eso el orden de los scripts pone el A/B *antes* del cambio.

---

## La idea central: un alias, no N configs

El problema de "actualizar todo lo que tenemos con ese modelo" es que las
referencias están repartidas por la máquina y siempre se escapa alguna.

La solución aquí es indirección: se crea un alias de Ollama llamado
`work-default`, las apps nombran **solo el alias**, y cambiar de modelo pasa a
ser una línea. Volver atrás, también.

```
apps  ->  work-default  ->  qwen3.8:27b-nvfp4   (o el modelo viejo)
```

Se hace con `ollama cp`, que copia el manifiesto y comparte los blobs: es
instantáneo y no duplica los 17GB en disco.

**El modelo viejo nunca se borra.** Ningún script invoca `ollama rm`.

---

## Uso

```bash
# 0. Inventario. Solo lectura, no toca nada.
./00-inventory.sh --scan-home

#    Anota el modelo que estés usando hoy y ponlo en models.conf:
#      OLD_MODEL="loquesea:tag"

# 1. Descarga. No destructivo: los dos modelos conviven.
./01-pull-qwen38.sh
./01-pull-qwen38.sh --gguf    # si el tag NVFP4 falla
./01-pull-qwen38.sh --yes     # no preguntar (runs no interactivos)

# 2. MIDE ANTES DE CAMBIAR.
cp tareas-ejemplo.txt mis-tareas.txt
$EDITOR mis-tareas.txt         # pon tus tareas reales
./03-ab-eval.py --prompts mis-tareas.txt --runs 3

# 3. Solo si el nuevo gana en TUS tareas:
./02-switch-model.sh --dry-run
./02-switch-model.sh

# Volver atrás en cualquier momento:
./02-switch-model.sh --rollback
./02-switch-model.sh --status
```

Después del paso 3, apunta tus aplicaciones al alias:

```bash
OLLAMA_MODEL=work-default
```

---

## Archivos

| Archivo | Qué hace | ¿Modifica algo? |
|---|---|---|
| `models.conf` | Fuente única de verdad. Es el único que editas a mano. | — |
| `00-inventory.sh` | Detecta hardware, runtime, modelos y configs que nombran el viejo. | No |
| `01-pull-qwen38.sh` | Descarga el 27B + prueba de humo. | Solo añade |
| `03-ab-eval.py` | A/B sobre tus prompts: latencia, tok/s, salidas. Solo stdlib. | No |
| `02-switch-model.sh` | Repunta el alias, con backup y auto-rollback si falla. | Sí (reversible) |

---

## Detalles que muerden

- **Visión en silencio.** El 27B es multimodal, pero en GGUF las imágenes
  fallan *sin dar error*: el modelo responde ignorando la imagen. Hay que
  cargar el proyector `mmproj` (~0.9GB). Ver `NEW_MODEL_MMPROJ` en
  `models.conf`.
- **NVFP4 necesita Blackwell.** El GB10 lo es (sm_121). En otro hardware hay
  que usar GGUF (`--gguf`).
- **Espacio.** ~16GB NVFP4, ~17.1GB GGUF Q4_K_M. `01` avisa si hay menos de
  40GB libres.
- **`ollama cp` no duplica pesos**, comparte blobs. Tener el alias no cuesta
  disco.
- **Los archivos de salida están en `.gitignore`** — son estado de tu máquina.

---

## Fuentes

- [Alibaba Qwen Releases Qwen3.8-Max — MarkTechPost](https://www.marktechpost.com/2026/08/03/alibaba-qwen-releases-qwen3-8-max/)
- [Qwen 3.8 Benchmarks: What's Actually Verified So Far — Yotta Labs](https://www.yottalabs.ai/post/qwen-3-8-benchmarks-what-is-verified-2026)
- [Qwen3.8 — How to Run Locally (Unsloth)](https://unsloth.ai/docs/models/qwen3.8)
- [Qwen3.8-27B: Specs, Benchmarks & Local Hardware — Kingy](https://kingy.ai/blog/qwen3-8-27b-specs-benchmarks-local-hardware/)
- [NVIDIA DGX Spark product page](https://www.nvidia.com/en-us/products/workstations/dgx-spark/)
- [vLLM on the DGX Spark](https://vllm.ai/blog/2026-06-01-vllm-dgx-spark)
