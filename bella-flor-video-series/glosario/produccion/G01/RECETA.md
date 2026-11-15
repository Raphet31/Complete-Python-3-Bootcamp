# RECETA · G01 «Adivina la flor en 3 pistas · Pascua»

Producido el 15-nov-2026. **Pendiente de aprobación de Raphet. No publicado.**

## Entregables
- `G01-pascua-final.mp4` — 34.0 s, 1080×1920, 30 fps, H.264 + AAC, audio a −14 LUFS.
- `G01-portada-1080x1920.jpg`, `G01-portada-1080x1350.jpg`, `G01-portada-1280x720.jpg`.

## Cómo se rehace
En la GB10, carpeta `~/Documents/bella-flor-video-series-prod/`:

```bash
python3 montar_g01.py --hoja
```

Tarda ~40 s con los clips ya interpolados en `G01/prep/` (la primera vez ~7 min). Solo usa CPU.

## Imágenes
| Toma | Archivo | Modelo | Notas |
|---|---|---|---|
| 6 (héroe) | `imagenes/t6_s11.png` | Qwen-Image 2512 fp8, local en la GB10 (Apache 2.0) | semilla 11, 50 pasos, cfg 4.0, shift 3.1, 928×1664 |
| 1, 2, 3 | `imagenes/t1.png` … `t3.png` | Nano Banana 2.1 (Higgsfield), 2k, 9:16 | prompt e id del trabajo en el `.json` de cada una |
| 7 | `imagenes/t7.png` | Nano Banana 2.1, edición de `t7_v1.png` (que es edición de la toma 6) | se rehízo para dejar el tercio de arriba en crema |
| 8 | `imagenes/t8.png` | Nano Banana 2.1, edición de la toma 6 | la planta no es idéntica a la de la 6 |
| Portada | `imagenes/portada.png` | Nano Banana 2.1, edición de la toma 1 | |

## Clips (Higgsfield, 1080p, 9:16, 5 s)
| Toma | Modelo | Créditos |
|---|---|---|
| 1, 2, 3 | Kling 4.0 (imagen a video) | 16.25 c/u |
| 6, 8 | Kling 3.0 Turbo | 10 c/u |
| 7 | no se usa clip: foto fija con zoom leve en el montaje (Kling se acercaba demasiado) | 20 gastados en dos intentos |

La toma 4 (pista 3) es la toma 6 desenfocada y corriendo hacia atrás hasta su primer cuadro; la revelación arranca de ese mismo cuadro. La toma 5 (conteo) se dibuja en el montaje.

Gasto total en Higgsfield: **106.75 créditos** (de 892.35 quedaron 785.60).

## Montaje (`montar_g01.py`)
- 24 → 30 fps y cámara lenta ×1.2 en las pistas 1 y 2 con `minterpolate`.
- Zona segura: nada de texto en los 350 px de abajo ni en los 170 px de la derecha; el texto se centra en x = 488.
- Revelación: desenfoque gaussiano 42 → 0 en 0.4 s, destello y zoom 1.06 → 1.00.
- Audio: `loudnorm=I=-14:TP=-1.5:LRA=11`.

## Fuentes, banderas y sonido
| Recurso | Origen | Licencia |
|---|---|---|
| Playfair Display (regular e itálica, variable) | github.com/google/fonts, `ofl/playfairdisplay` | SIL OFL 1.1 (`assets/fuentes/OFL-Playfair.txt`) |
| Montserrat (variable) | github.com/google/fonts, `ofl/montserrat` | SIL OFL 1.1 (`assets/fuentes/OFL-Montserrat.txt`) |
| Banderas EE. UU., México, Puerto Rico | Twemoji 15.1.0 (jdecked/twemoji), SVG | CC-BY 4.0 — **poner atribución en la descripción**: «Banderas: Twemoji, CC-BY 4.0» |
| Todo el sonido (golpe, tic-tac, tambor, campanitas, acorde, cuatro, pops, coquí) | Sintetizado con numpy en `montar_g01.py` | Original, sin samples de terceros |

## Pendiente antes de publicar
- **Johnny valida la pista 2**: «Los aztecas la usaban para hacer tinte rojo».
- Atribución de Twemoji en la descripción.
- El canal B no lleva nombre ni logo de Bella Flor: el video no los tiene.

## Lo que no sirvió (para no repetirlo)
- Video local con Wan 2.2 14B en la GB10: la máquina llegó a 95 °C y se suspendió. Los modelos quedaron bajados en `~/Documents/bf-comfy/ComfyUI/models`. `comfy_gb10.py`, `paso_termico.sh` y `guardian_mem.sh` son de ese intento.
