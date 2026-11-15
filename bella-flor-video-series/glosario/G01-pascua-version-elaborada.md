# G01 — Pascua · versión elaborada (“La vuelta al mundo de una flor”)

**Formato nuevo de la serie:** la misma flor, siempre en el centro del cuadro, mientras el mundo cambia a su alrededor. Cada nombre es un país distinto; el corte es *match cut* (la flor no se mueve, cambia todo lo demás). Termina en Puerto Rico.
**Duración:** 28–32 s · 9:16 · video generado con IA (Higgsfield u otro generador de imagen a video) · texto elegante encima · música + efectos de sonido · sin voz (la voz se puede añadir después).

## Gancho (0:00–0:03) — tres versiones para probar

| Versión | Imagen | Texto |
|---------|--------|-------|
| **A (recomendada)** | Macro extremo del centro amarillo; la cámara se aleja rápido y revela la planta entera flotando sobre un mapamundi antiguo | ESTA FLOR CAMBIA DE NOMBRE EN CADA PAÍS |
| B | Una mano deja la pascua en una mesa; al tocar la mesa, el cuarto entero cambia de país de golpe | 1 FLOR · 6 NOMBRES |
| C | La pascua con seis etiquetas de equipaje colgando, como una maleta que ha viajado | LA FLOR CON MÁS PASAPORTES |

Se publican A y B en días distintos y se queda el formato que retenga más a los 3 segundos.

## Paso 0 — Flor “héroe” (se genera una sola vez)

Se genera una imagen de la pascua y se usa como **imagen de referencia** en todas las tomas, para que sea la misma planta en cada país.

```
Photorealistic potted red poinsettia, lush and full, deep red bracts with small
yellow center flowers, terracotta pot wrapped in natural linen, centered in frame,
soft diffused light, shallow depth of field, premium editorial photography,
vertical 9:16, no text, no watermark
```

## Tomas (cada una: imagen inicial → video de 5 s; se usan 3–4 s)

Regla para todas: **la pascua en el centro exacto, mismo tamaño, misma altura de cámara.** Movimiento: `slow cinematic push-in, flower stays perfectly centered and still, background elements move subtly`.

| # | Tiempo | Escena (prompt de imagen, con la flor héroe de referencia) | Texto en pantalla | Sonido |
|---|--------|------------------------------------------------------------|-------------------|--------|
| 1 | 0:00–0:03 | `Extreme macro of the tiny yellow center flowers of a red poinsettia` → movimiento: `fast pull-back revealing the whole plant floating above an antique world map, warm light` | ESTA FLOR CAMBIA DE NOMBRE EN CADA PAÍS | Golpe grave + *whoosh* |
| 2 | 0:03–0:07 | `The poinsettia on a 19th century botanist's desk, pressed plants, brass magnifying glass, ink sketches, candlelight` | *Euphorbia pulcherrima* · nombre científico | Pluma sobre papel |
| 3 | 0:07–0:11 | `The poinsettia on a snowy New England porch at dusk, wreath on the door, warm window light, falling snow` | **Poinsettia** · Estados Unidos | Campanitas suaves |
| 4 | 0:11–0:15 | `The poinsettia in a Mexican colonial plaza at night, papel picado overhead, piñata, warm string lights, church in the background` | **Flor de Nochebuena** · México | Guitarra |
| 5 | 0:15–0:19 | `The poinsettia on a wrought-iron balcony in a Spanish old town, Christmas lights across a narrow street, evening` | **Flor de Pascua** · España | Castañuela suave |
| 6 | 0:19–0:23 | `The poinsettia in a sunny Buenos Aires summer patio, mate gourd on the table, jacaranda in bloom, bright daylight` | **Estrella federal** · Argentina | Bandoneón corto |
| 7 | 0:23–0:28 | `The poinsettia on the balcony of a colorful Old San Juan colonial house, blue cobblestones, Christmas lights, golden hour, palm in the distance` → movimiento: `slow push-in, lights twinkle, warm breeze moves a ribbon` | **Pascua** · Puerto Rico 🇵🇷 | Cuatro puertorriqueño + coquí |
| 8 | 0:28–0:31 | La toma 7 se queda; baja la luz a noche | ¿Y TÚ, CÓMO LE DICES? · Comenta tu país | Nota final |

**Texto:** serif grande, blanco con sombra suave, tercio inferior (dentro de la zona segura: nada en los 350 px de abajo ni en los 170 px de la derecha). El nombre entra con un *fade* de 0.3 s justo en el corte.

## Portada (thumbnail)

- **Imagen:** la flor héroe partida en dos mitades verticales: mitad izquierda con el fondo de México de noche, mitad derecha con el Viejo San Juan al atardecer. La flor entera en el centro, cruzando la línea.
- **Texto:** `1 FLOR` arriba, `6 NOMBRES` abajo, serif blanca grande. Nada más.
- **Prompt:**

```
Split-screen vertical poster: one potted red poinsettia perfectly centered, left half
background is a Mexican colonial plaza at night with papel picado, right half is a
colorful Old San Juan street at golden hour, the plant spans both halves seamlessly,
cinematic, premium editorial look, 9:16, no text, no watermark
```

- Se exporta también en 16:9 para YouTube y 4:5 para el feed de Instagram.

## Cómo se produce

1. Generar la flor héroe (Paso 0) y escoger la mejor de 4.
2. Generar las 7 imágenes de escena usando la héroe como referencia. Descartar las que cambien la flor de tamaño o posición.
3. Pasar cada imagen a video de 5 s con el prompt de movimiento.
4. Guardar los clips como `clips/G01/01.mp4` … `07.mp4` y la portada como `clips/G01/portada.png`.
5. Montaje: cortes en el golpe de la música, texto encima, sonido. Lo arma Claude con los clips, o se edita en CapCut con esta tabla.

**Créditos estimados:** 1 héroe + 7 escenas + 1 portada (con repeticiones, ~25 imágenes) y 7 videos de 5 s (con repeticiones, ~12).

## El mismo molde para las próximas flores

| Flor | Recorrido | Cierre en PR |
|------|-----------|--------------|
| Cala | Sudáfrica (origen) → EE.UU. *calla lily* → México *alcatraz* (mercado, estilo mural) → Colombia *cartucho* | Boda en una hacienda |
| Gipsófila | Estepa de Europa del Este (origen) → EE.UU. *baby’s breath* → España *paniculata* → México *nube* | Ramo de novia en el taller |
| Alstroemeria | Andes (origen) → EE.UU. *Peruvian lily* → Chile *lirio del campo* → LatAm *astromelia* | Mesa de una casa boricua |
