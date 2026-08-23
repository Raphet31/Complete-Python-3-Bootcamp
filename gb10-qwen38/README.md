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

La secuencia importa. La idea es **separar "introducir la indirección" de
"cambiar de modelo"**, para que nunca haya un paso en que cambien las dos cosas
a la vez. Si algo se rompe, sabes cuál de las dos fue.

```bash
# --- Fase 1: descubrir -------------------------------------------------
./00-inventory.sh --scan-home
#   Anota el modelo que usas hoy y ponlo en models.conf:
#     OLD_MODEL="loquesea:tag"

# --- Fase 2: descargar (no destructivo) --------------------------------
./01-pull-qwen38.sh
./01-pull-qwen38.sh --gguf     # si el tag NVFP4 falla
./01-pull-qwen38.sh --yes      # no preguntar (runs no interactivos)

# --- Fase 3: medir ANTES de decidir ------------------------------------
cp tareas-ejemplo.txt mis-tareas.txt
$EDITOR mis-tareas.txt          # pon tus tareas reales
./03-ab-eval.py --prompts mis-tareas.txt --runs 5
./03-ab-eval.py --prompts mis-tareas.txt --concurrency 4   # bajo carga
./05-report.py                  # comparativa lado a lado -> ab-report.html

# --- Fase 4: introducir el alias SIN cambiar comportamiento -------------
./02-switch-model.sh --init     # alias -> modelo VIEJO
./04-repoint-configs.py --path ~/proyectos --path /etc/systemd/system
#   ^ simulacro: revisa el diff con calma
./04-repoint-configs.py --path ~/proyectos --apply
#   Reinicia servicios y COMPRUEBA que todo sigue igual que antes.
#   Hasta aqui no cambiaste de modelo: solo de nombre.

# --- Fase 5: el flip ----------------------------------------------------
./02-switch-model.sh            # alias -> Qwen3.8-27B. Un comando.
```

Volver atrás, en cualquier momento y sin tocar ningún config:

```bash
./02-switch-model.sh --rollback
./02-switch-model.sh --status
```

Y si quieres deshacer también la migración de configs:

```bash
./04-repoint-configs.py --list-backups
./04-repoint-configs.py --restore
```

## Archivos

| Archivo | Qué hace | ¿Modifica algo? |
|---|---|---|
| `models.conf` | Fuente única de verdad. El único que editas a mano. | — |
| `00-inventory.sh` | Detecta hardware, runtime, modelos y configs que nombran el viejo. | No |
| `01-pull-qwen38.sh` | Descarga el 27B + prueba de humo. | Solo añade |
| `03-ab-eval.py` | A/B sobre tus prompts: p50/p95, tok/s, memoria, concurrencia. | No |
| `05-report.py` | Convierte los resultados en HTML lado a lado para juzgar calidad. | No |
| `02-switch-model.sh` | Crea/repunta el alias, con backup y auto-rollback si falla. | Sí (reversible) |
| `04-repoint-configs.py` | Reescribe tus configs para que nombren el alias. Simulacro por defecto. | Sí (reversible) |

### Sobre el benchmark

Un bench mal hecho es peor que ninguno, porque da falsa confianza. `03-ab-eval.py`
intenta no serlo:

- **Warm-up descartado.** La primera llamada carga el modelo en memoria, y eso
  son decenas de segundos. Incluirla castiga injustamente al modelo más grande.
  Por defecto se descarta una corrida por modelo.
- **p50 y p95, no solo la mediana.** La mediana esconde la cola, y la cola es lo
  que de verdad se nota cuando estás trabajando.
- **Memoria residente.** En 128GB unificados, cuánto ocupa el modelo y cuánto
  margen queda es lo que decide cuántas sesiones te caben en paralelo. Se lee de
  `ollama ps` (best-effort; sale `n/d` si no está disponible).
- **Concurrencia.** `--concurrency N` lanza N peticiones a la vez para ver cuánto
  se degrada bajo carga. 17GB dentro de 128GB dan margen para varias sesiones;
  esto te dice cuántas.
- **La calidad no se automatiza.** El script mide velocidad. `05-report.py` te
  pone las dos respuestas a la misma tarea lado a lado y la juzgas tú. No hay
  métrica automática que sustituya eso para tus tareas concretas.

### Sobre `04-repoint-configs.py`

Es el único script que toca archivos fuera del store de Ollama, así que es el
más cuidadoso:

- **Simulacro por defecto.** Enseña un diff unificado; hay que pasar `--apply`.
- **Respalda todo** antes de escribir, con manifiesto, y `--restore` lo deshace.
- **Reemplazo literal**, no regex: no hay metacaracteres que se escapen.
- **No entra** en `.git`, `node_modules`, `venv`, `blobs`/`manifests` de Ollama,
  ni en archivos binarios (detecta NUL), symlinks, o cosas de más de 2MB.
- **No se toca a sí mismo**: los archivos de este toolkit mencionan nombres de
  modelo a propósito y quedan excluidos aunque apuntes el `--path` al repo.

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
