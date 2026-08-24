# Migración a Qwen3.8-27B en la GB10 (DGX Spark)

Paquete de scripts para evaluar y —si sale bien— adoptar **Qwen3.8-27B** en la
GB10, **sin borrar el modelo actual**.

Los scripts corren **en la GB10**, no aquí. Este repo solo los versiona.

---

## Qué dicen los benchmarks públicos

Verificado en fuentes independientes, agosto 2026. Los dos son **27B densos,
misma arquitectura** (64 capas, Gated DeltaNet híbrido + atención), mismo
tamaño en disco (~17GB Q4_K_M), mismo contexto (256K). Es un reemplazo directo.

**Artificial Analysis Intelligence Index** (tercero independiente, no Alibaba):

| Modelo | Score |
|---|---:|
| Qwen3.6-27B | 38 |
| **Qwen3.8-27B** | **52** |

Son los 14 puntos. Y en benchmarks concretos:

| Benchmark | 3.6-27B | 3.8-27B |
|---|---:|---:|
| Terminal-Bench 2.1 | 63.4 | 73.0 |
| DeepSWE 1.1 | 13.3 | 42.2 |
| OSWorld-Verified | 63.9 | 84.3 |
| SWE-bench Pro | 53.5 | 61.7 |
| SWE-MM | 25.7 | 38.6 |
| JobBench | 21.8 | 33.4 |

La arquitectura no cambió: **todo el salto viene del post-entrenamiento**
(entornos de RL + destilación on-policy). Con 52 queda a 1 punto de DeepSeek V4
Pro y GLM-5.2, que son mucho más grandes.

En corto: el upgrade está bien respaldado por evidencia independiente. No hace
falta discutirlo.

## El problema real: `reasoning_effort`

Aquí está el riesgo, y no es el que parecía.

Qwen3.8-27B trae `reasoning_effort` con **`xhigh` por defecto**, y en ese modo
se pasa de vueltas de forma extrema: en la prueba de Simon Willison quemó
**22.276 tokens de razonamiento en ~21 minutos** para una sola tarea.

Lo que eso significa para ti: **si haces el A/B con los valores por defecto, el
3.8 va a parecer catastróficamente más lento que el 3.6**, y no porque lo sea,
sino porque está razonando en xhigh mientras el 3.6 no. Rechazarías el upgrade
por un artefacto de configuración.

Los niveles son `low`, `medium` y `xhigh`. `medium` recorta la espera como un
tercio **sin pérdida de calidad medible**, y es el default nativo del modelo
(xhigh se inyecta con una frase en el system prompt).

Ojo también: **el 52 de Artificial Analysis está medido en `xhigh`.** Si corres
en `medium` estás en otro punto de operación — más rápido, y probablemente algo
por debajo de ese 52.

Por eso `03-ab-eval.py` acepta `--reasoning-effort` y `--sweep-effort`: mide los
tres niveles para que elijas el punto de operación con datos, no por defecto.

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

## Instalación en la GB10 (primera vez)

Este toolkit vive en una rama del repo `Complete-Python-3-Bootcamp`. En la GB10
**no está clonado**, así que la primera vez hay que traerlo. `git pull` a secas
falla con *"no such file or directory"* precisamente por eso.

Un comando por línea, **sin barras de continuación**: al pegar en una terminal
remota las líneas se juntan, y `\ ` no continúa línea — escapa el espacio. El
resultado es que `git` recibe argumentos basura y falla con
*"unknown option"* o *"Too many arguments"*.

```bash
git clone --depth 1 --single-branch -b claude/upgrade-qend-3-8-py4bte https://github.com/Raphet31/Complete-Python-3-Bootcamp.git ~/qwen38-migration
```

```bash
cd ~/qwen38-migration/gb10-qwen38 && ./07-bfos-gate.py --bfos ~/BELLA_FLOR_OS
```

Son ~50 MB y unos segundos. El toolkit en sí son 124 KB; el resto es el curso
de Python que arrastra el repo.

**Para actualizar** después, ya desde `~/qwen38-migration`:

```bash
git pull
```

Los scripts resuelven sus rutas relativas a sí mismos, así que da igual desde
qué directorio los invoques.

---

## Antes de nada: reglas de BF-OS v6

Este toolkit se escribió sin conocer BF-OS. Al leer el PLAN COLIBRÍ v1.1
aparecieron tres reglas marcadas **SAGRADO** que la migración, tal como estaba,
habría roto. `07-bfos-gate.py` las comprueba y **aborta** antes de tocar nada.

| Regla | Qué exige | Qué hacía mal el toolkit |
|---|---|---|
| **R7** | Ningún modelo se baja sin entrada previa en `MODEL_INVENTORY.md` con rol asignado | `run-all.sh` descargaba directo |
| **R8** | El drift validator cruza **cinco** fuentes al boot | `04-repoint-configs.py` reescribía `registry.yaml`, `agents/*.yaml`, `swarm_gpu_models.yaml` y el picker → boot **ROJO** |
| **R4** | Memoria unificada compartida, `OLLAMA_MAX_LOADED_MODELS=1` | El A/B carga dos modelos; `--concurrency` carga más |

Las cinco fuentes del drift validator quedan ahora **excluidas por defecto** de la
reescritura automática. Actualizarlas es trabajo manual y coherente en las cinco
a la vez — nunca parcial.

```bash
./07-bfos-gate.py --bfos ~/BELLA_FLOR_OS
# 0 puede continuar   1 hay violaciones   2 no se pudo verificar
```

`run-all.sh` la ejecuta sola, **antes de la descarga**, y se detiene si sale 1.

---

## Uso

### Un solo comando

```bash
./run-all.sh --auto
```

Encadena las diez fases, guarda el progreso y se puede reanudar. Se **detiene
deliberadamente antes de cambiar de modelo** para que mires el informe; el
último paso lo das tú, o lo automatizas con `--yes-flip`.

```bash
./run-all.sh                 # todo hasta el informe, sin tocar el modelo
./run-all.sh --auto          # además migra los configs sin preguntar
./run-all.sh --auto --yes-flip   # y cambia de modelo si el veredicto aprueba
./run-all.sh --status        # qué fases van hechas
./run-all.sh --from bench    # reanuda desde una fase
./run-all.sh --auto --skip-bench --yes-flip   # sin medir, migración completa
```

La última variante hace la migración entera sin medir en tu hardware: descarga,
alias, configs y cambio. Es defendible cuando confías en la evidencia pública
—que en este caso es independiente y contundente— y sabes que el rollback es un
comando. Usa el `REASONING_EFFORT` de `models.conf` tal cual, así que
asegúrate de que dice `medium`.

Lo único que conviene hacer a mano: sustituir `mis-tareas.txt` por tus tareas
reales y reejecutar `./run-all.sh --from bench`. El script lo crea a partir del
ejemplo si no existe, pero un bench sobre tareas genéricas mide poco.

### Paso a paso, si prefieres control

La secuencia separa **introducir la indirección** de **cambiar de modelo**, para
que un fallo sea atribuible a uno u otro.

```bash
# --- Fase 1: descubrir -------------------------------------------------
./00-inventory.sh --scan-home

# --- Fase 2: descargar (no destructivo) --------------------------------
./01-pull-qwen38.sh
./01-pull-qwen38.sh --gguf     # si el tag NVFP4 falla
./01-pull-qwen38.sh --yes      # no preguntar

# --- Fase 3: medir ANTES de decidir ------------------------------------
cp tareas-ejemplo.txt mis-tareas.txt && $EDITOR mis-tareas.txt
./03-ab-eval.py --prompts mis-tareas.txt --runs 5 --sweep-effort
#   ^ IMPRESCINDIBLE la primera vez: sin esto el 3.8 corre en xhigh y
#     parece mucho más lento de lo que es.
./05-report.py                 # comparativa lado a lado -> ab-report.html
./06-verdict.py                # recomendación automática

# --- Fase 4: introducir el alias SIN cambiar comportamiento -------------
./02-switch-model.sh --init
./04-repoint-configs.py --path ~/proyectos          # simulacro
./04-repoint-configs.py --path ~/proyectos --apply
#   Reinicia servicios y comprueba que todo sigue igual.

# --- Fase 5: el flip ----------------------------------------------------
./02-switch-model.sh
```

Volver atrás, sin tocar ningún config:

```bash
./02-switch-model.sh --rollback
./04-repoint-configs.py --restore    # y también los configs, si hace falta
```

## Archivos

| Archivo | Qué hace | ¿Modifica algo? |
|---|---|---|
| `models.conf` | Fuente única de verdad. El único que editas a mano. | — |
| `00-inventory.sh` | Detecta hardware, runtime, modelos y configs que nombran el viejo. | No |
| `01-pull-qwen38.sh` | Descarga el 27B + prueba de humo. | Solo añade |
| `03-ab-eval.py` | A/B sobre tus prompts: p50/p95, tok/s, memoria, concurrencia. | No |
| `05-report.py` | Convierte los resultados en HTML lado a lado para juzgar calidad. | No |
| `06-verdict.py` | Lee las medidas y dicta recomendación. Salida: 0 cambiar, 1 no, 2 decides tú. | No |
| `run-all.sh` | Encadena las diez fases con estado y reanudación. | Orquesta |
| `07-bfos-gate.py` | Verifica R7/R8/R4 de BF-OS antes de descargar. Aborta si se violan. | No |
| `_conf.py` | Lectura compartida de `models.conf`, con expansión de variables. | No |
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
