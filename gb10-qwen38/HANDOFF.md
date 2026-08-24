# HANDOFF — Migración Qwen3.8-27B en la GB10

**Para:** una sesión de Claude Code corriendo **en la GB10** (`gx10-f972`).
**De:** una sesión de Claude Code **en la web**, sin ruta a la tailnet.
**Fecha:** 24 de agosto de 2026 · **Usuario:** Raphet Delgado (`raphet31`)

---

## 0. Por qué existe este documento

La sesión anterior corría en un contenedor efímero de Anthropic: x86_64, sin
GPU, 15 GB de RAM, fuera de la tailnet. Comprobado, no supuesto:

- `ollama.com`, `registry.ollama.ai`, `huggingface.co`, `modelscope.cn` → **403 del proxy**
- `100.86.81.32:22` y `:3389` → **sin ruta**; `gx10-f972` no resuelve
- `tailscale` no instalado, `tailscale.com` bloqueado, `ssh` ni instalado
- La GB10 es **aarch64**; aquel contenedor era **x86_64**

Por eso todo el código está escrito y probado **contra stubs**, nunca contra la
máquina real. Tú sí estás en la máquina. **Tu primer trabajo es validar lo que
yo no pude.**

---

## 1. El objetivo

Reemplazar el modelo Qwen local por **Qwen3.8-27B**, sin borrar el anterior y
con rollback trivial.

Evidencia pública (verificada en fuentes independientes, agosto 2026):

| | Qwen3.6-27B | Qwen3.8-27B |
|---|---:|---:|
| **AA Intelligence Index** (independiente) | 38 | **52** |
| Terminal-Bench 2.1 | 63.4 | 73.0 |
| DeepSWE 1.1 | 13.3 | 42.2 |
| OSWorld-Verified | 63.9 | 84.3 |
| SWE-bench Pro | 53.5 | 61.7 |

Misma arquitectura, mismo tamaño (~17 GB Q4_K_M), mismo contexto (256K). Todo
el salto viene del post-entrenamiento. **La recomendación es que conviene.**

---

## 2. Dónde está el código

```
git clone --depth 1 --single-branch -b claude/upgrade-qend-3-8-py4bte https://github.com/Raphet31/Complete-Python-3-Bootcamp.git ~/qwen38-migration
```

Ya debería estar clonado en `~/qwen38-migration`. El toolkit vive en
`~/qwen38-migration/gb10-qwen38/`. PR **#1** contra `master`.

**Nota rara pero cierta:** el toolkit vive en un fork del curso de Python de
Udemy porque esa era la única sesión disponible. **Probablemente debería
mudarse a `BELLA_FLOR_OS`.** Decisión abierta (§7).

---

## 3. Qué hay hecho

13 archivos, 10 commits. Todos los scripts resuelven rutas relativas a sí
mismos, así que corren desde cualquier directorio.

| Archivo | Qué hace | ¿Escribe? |
|---|---|---|
| `run-all.sh` | Orquesta las 11 fases, con estado y reanudación | orquesta |
| `models.conf` | Fuente única de verdad. Único que se edita a mano | — |
| `_conf.py` | Lectura compartida de `models.conf`, expande variables de shell | no |
| `00-inventory.sh` | Hardware, runtime, modelos, configs que nombran el viejo | no |
| `01-pull-qwen38.sh` | Descarga + prueba de humo. `--gguf`, `--yes`, `--with-vision` | solo añade |
| `02-switch-model.sh` | Alias: `--init`, `--status`, `--dry-run`, `--rollback` | sí, reversible |
| `03-ab-eval.py` | p50/p95, throughput, memoria, concurrencia, barrido de esfuerzo | no |
| `04-repoint-configs.py` | Reescribe configs al alias. Simulacro por defecto | sí, reversible |
| `05-report.py` | HTML lado a lado, una columna por variante | no |
| `06-verdict.py` | Recomendación. Salida 0 cambiar / 1 no / 2 decides tú | no |
| `07-bfos-gate.py` | **Verifica R7/R8/R4 de BF-OS. Aborta si se violan** | no |

### La idea central: un alias

En vez de perseguir referencias al modelo por toda la máquina, se crea un alias
de Ollama (`work-default`) y las apps lo nombran a él. Cambiar de modelo pasa a
ser un `ollama cp`. **Ver §5.3 — esta idea puede estar mal para BF-OS.**

---

## 4. LO QUE BLOQUEA AHORA MISMO

### 4.1 No sabemos qué modelo se está reemplazando ⛔

`models.conf` dice `OLD_MODEL="qwen3.6:27b"`. Ese tag salió de una descripción
verbal del usuario. **La puerta, corrida en la GB10 real, reportó que ese tag
NO aparece en `MODEL_INVENTORY.md`.**

El PLAN COLIBRÍ nombra `qwen3:30b`, `qwen3:14b`, `deepseek-r1:32b`,
`llama3.3:70b`, `glm-4.7-flash`. Ninguno es `qwen3.6:27b`.

**Primer comando a correr:**

```
cd ~/qwen38-migration/gb10-qwen38 && ./07-bfos-gate.py --bfos ~/BELLA_FLOR_OS --report
```

Es solo lectura. Lista (1) lo instalado en Ollama vía API, (2) lo declarado en
`MODEL_INVENTORY.md`, (3) lo que nombran las fuentes reales del drift validator.
Con eso se fija `OLD_MODEL` de verdad.

### 4.2 R7 bloquea la descarga (correctamente)

`qwen3.8:27b-nvfp4` no tiene entrada en `MODEL_INVENTORY.md`. R7 es SAGRADO:
la entrada con rol asignado va **antes** de bajar. Hay que redactarla.

---

## 5. HUECOS Y RIESGOS — leer entero

### 5.1 Ningún tag de modelo fue verificado ⚠️

`qwen3.8:27b-nvfp4` y `qwen3.8:27b` salieron de **búsqueda web**, no de
consultar el registro de Ollama. **Puede que el tag NVFP4 ni exista** en la
versión de Ollama de la GB10. `01-pull-qwen38.sh` cae a GGUF si el pull falla,
pero eso no se ha probado de verdad. **Verificar antes de confiar.**

### 5.2 Nada corrió nunca contra un modelo real

| script | probado contra | hueco |
|---|---|---|
| `07-bfos-gate.py` | fixtures **+ la GB10 real** | ninguno conocido |
| `04-repoint-configs.py` | fixtures realistas | nunca escribió en BF-OS real |
| todos los demás | stubs (CLI y HTTP falsos) | **nunca vieron un modelo real** |

Los stubs validan la lógica, no la realidad. Trata cada script como no probado
hasta que lo corras.

### 5.3 `work-default` es un nombre que inventé yo ⚠️⚠️

**Este es el hueco que menos me gusta.** El alias no está declarado en ninguna
de las cinco fuentes del drift validator. Si las apps empiezan a nombrar
`work-default` mientras los registries nombran tags reales, **el drift validator
puede salir ROJO al boot.**

`04-repoint-configs.py` deliberadamente **no** toca esas cinco fuentes (R8), lo
cual evita romperlas — pero deja la incoherencia: configs diciendo una cosa,
registries otra.

**Puede que el enfoque de alias sea directamente incorrecto para BF-OS**, que ya
tiene gestión de modelos por registry. Evalúa si conviene:

- registrar `work-default` coherentemente en las cinco fuentes, o
- tirar el alias y hacer el swap por el mecanismo propio de BF-OS

**No sigas con `04-repoint-configs.py --apply` hasta resolver esto.**

### 5.4 R4 nunca se verificó

`ollama` no está en el PATH de un shell SSH limpio, así que la puerta no pudo
comprobar qué hay cargado. El A/B carga **dos** modelos; `--concurrency` carga
más. Los 121 GB son unificados y compartidos con Whisper, Kokoro y ComfyUI, y
ya hubo un crash por 53 GB pineados. **Drena Ollama antes de medir.**

### 5.5 Otros

- `NEW_MODEL_MMPROJ` vacío: el 27B es multimodal, pero en GGUF **las imágenes
  fallan en silencio** sin el proyector (~0.9 GB). Rellenar si se usa visión.
- **Cadena de escalación**: `deepseek-r1:32b → glm-4.7-flash → glm-5.2`. No he
  examinado si meter/cambiar un modelo obliga a tocarla.
- **Disco**: PLAN COLIBRÍ estima ~2.5 TB libres, pero es estimado. `df -h`.
- `reasoning_effort` viene en **`xhigh`** de fábrica y se pasa de vueltas (caso
  documentado: 22.000 tokens en una tarea). `models.conf` ya pone `medium`. Si
  mides sin fijarlo, el 3.8 parecerá ~4× más lento de lo que es.

---

## 6. Errores ya cometidos y corregidos — no repetirlos

Todos salieron de probar, no de razonar:

1. **Afirmación falsa sobre los benchmarks.** Dije que los 14 puntos eran del
   Max (2.4T) y de la tabla de Alibaba. Falso: son 27B contra 27B en Artificial
   Analysis, independiente. El usuario tenía razón. Corregido en README y PR.
2. **Python no expandía variables de shell** al leer `models.conf`, así que
   `OLLAMA_HOST="${OLLAMA_HOST:-...}"` llegaba como literal y **fallaban todas
   las peticiones**. Solo apareció corriendo la cadena entera. → `_conf.py`.
3. **El veredicto recomendaba el esfuerzo más barato** dentro del margen, o sea
   el modelo nuevo en su configuración más floja. Ahora elige el más alto.
4. **`04` iba a reescribir las cinco fuentes del drift validator** → boot ROJO.
   Ahora protegidas.
5. **`04` entraba en los 8 worktrees** de `.claude/worktrees/`, dejando diffs
   espurios en ocho ramas. Ahora excluidos.
6. `--dry-run` pedía confirmación antes de darse cuenta de que era simulacro.
7. El chequeo de disco abortaba **en silencio** sin TTY.
8. Un `|| echo` que nunca disparaba (exit status del pipeline venía de `sed`).
9. Instrucciones que empezaban con `git pull` sobre un repo **no clonado**.
10. Comandos con `\` de continuación que al pegarlos en terminal remota se
    aplastan en una línea y rompen `git`. Ahora todo va en una línea.

---

## 7. Decisiones abiertas

1. **¿Cuál es el `OLD_MODEL` real?** — bloqueante, §4.1
2. **¿Sobrevive el enfoque de alias en BF-OS?** — §5.3
3. **¿El toolkit debe mudarse a `BELLA_FLOR_OS`?** — probablemente sí
4. **Rol para la entrada de `MODEL_INVENTORY.md`** (R7)
5. **¿Medir o no?** El usuario aceptó saltarse el bench
   (`run-all.sh --skip-bench`). La evidencia pública es independiente y sólida,
   y el rollback es un comando.

---

## 8. Reglas de BF-OS que este trabajo debe respetar

Del PLAN COLIBRÍ v1.1 (`BF-OS-COLIBRI-PLAN-v1.1`, Drive):

- **R7** SAGRADO — nada se baja sin entrada previa en `MODEL_INVENTORY.md`
- **R8** — el drift validator cruza **cinco** fuentes; incoherencia = boot ROJO
- **R4** SAGRADO — arbitraje de memoria unificada; `OLLAMA_MAX_LOADED_MODELS=1`
- **REGLA MADRE** — todo fallo visible, nunca silencioso
- **`sudo` siempre pausa para Raphet** — el agente lo solicita, no lo ejecuta
- **No `git add -A`** — staging explícito
- Puertos sagrados **7799 / 7777 / 8887 / 7800** — intocables

---

## 9. Primeros pasos sugeridos

```
cd ~/qwen38-migration && git pull
./gb10-qwen38/07-bfos-gate.py --bfos ~/BELLA_FLOR_OS --report
```

Después, en orden:

1. Fijar `OLD_MODEL` real en `models.conf` (§4.1)
2. Verificar que `qwen3.8:27b-nvfp4` existe en el registro de Ollama (§5.1)
3. **Resolver §5.3 antes de tocar configs** — es lo que puede romper el boot
4. Redactar la entrada de `MODEL_INVENTORY.md` con rol (R7)
5. `./gb10-qwen38/07-bfos-gate.py --bfos ~/BELLA_FLOR_OS` hasta que pase
6. Solo entonces: `./gb10-qwen38/run-all.sh`

Rollback en cualquier momento:

```
./gb10-qwen38/02-switch-model.sh --rollback
./gb10-qwen38/04-repoint-configs.py --restore
```
