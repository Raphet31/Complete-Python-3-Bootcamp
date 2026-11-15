# G01 — “Adivina la flor en 3 pistas” · Pascua (formato interactivo)

**Mecánica:** el video no dice qué flor es. Da tres pistas visuales, cada una más fácil, con un contador. El que mira juega contra el reloj; al final se revela la flor y sus nombres por país. Cierre: “¿En cuál pista la adivinaste? Comenta 1, 2 o 3.”
**Por qué retiene:** nadie se va sin saber si acertó. Y el comentario es de un solo número, así que comenta mucha gente.
**Duración:** 30–34 s · 9:16 · video generado (GB10 o Higgsfield) + texto + sonido · sin voz.

## Tomas

Regla de imagen: fotorrealista y cálido. Las pistas son oscuras y con misterio; la revelación, a todo color.

**Orden de generación (importante para que sea la misma planta):** primero la toma 6 (planta héroe). La toma 4 **no se genera**: es la misma toma 6 desenfocada en el montaje, y por eso el enfoque de la revelación cuadra perfecto. Las tomas 7 y 8 se hacen editando la imagen de la toma 6 (cambiar el fondo y conservar la planta). La toma 5 es negro con números y tampoco se genera.

| # | Tiempo | Imagen y movimiento | Texto en pantalla | Sonido |
|---|--------|---------------------|-------------------|--------|
| 1 | 0:00–0:03 | Silueta negra de la planta contra una luz roja que late; la cámara entra despacio | ¿ADIVINAS LA FLOR EN 3 PISTAS? | Golpe grave + tic-tac |
| 2 | 0:03–0:09 | **Pista 1 (difícil):** macro extremo de los botoncitos amarillos del centro, tan cerca que no se reconoce; enfoque que respira | PISTA 1 · Esto amarillo es la flor de verdad. Lo demás son hojas. | Tic-tac; barra de tiempo que se vacía |
| 3 | 0:09–0:15 | **Pista 2 (media):** tinte rojo cayendo en agua en cámara lenta, sobre piedra tallada azteca | PISTA 2 · Los aztecas la usaban para hacer tinte rojo. | Tambor suave + tic-tac |
| 4 | 0:15–0:21 | **Pista 3 (fácil):** mesa de Nochebuena desenfocada, luces de Navidad, la planta al fondo fuera de foco, solo una mancha roja | PISTA 3 · Solo la ves en diciembre. | Campanitas + tic-tac más rápido |
| 5 | 0:21–0:23 | Negro. Números grandes 3 · 2 · 1 | 3 · 2 · 1 | Tres golpes |
| 6 | 0:23–0:28 | **Revelación:** la toma 4 enfoca de golpe; pascua roja plena, la cámara gira lento alrededor | ¡LA PASCUA! · *Euphorbia pulcherrima* | Acorde brillante |
| 7 | 0:28–0:31 | La planta queda en el centro; tres etiquetas entran una tras otra | EE.UU. Poinsettia · México Nochebuena · Puerto Rico Pascua (banderas como imágenes PNG, no emoji: ffmpeg no dibuja emoji) | Tres *pops* |
| 8 | 0:31–0:34 | Balcón del Viejo San Juan al atardecer con la pascua | ¿EN CUÁL PISTA LA ADIVINASTE? Comenta 1, 2 o 3 | Cuatro + coquí |

## Prompts (imagen inicial de cada toma → video de 5 s)

1. `Black silhouette of a potted poinsettia plant against a pulsing deep red backlight, dark moody studio, mysterious, vertical 9:16` · movimiento: `slow push-in, red light pulses like a heartbeat`
2. `Extreme macro photograph of the tiny yellow cyathia at the center of a poinsettia, abstract, shallow depth of field, dark background` · `focus breathing in and out, slight drift`
3. `Deep red natural dye swirling into clear water in slow motion, carved Aztec stone relief below, dramatic side light` · `slow motion ink clouds expanding`
4. Sin prompt: es el clip de la toma 6 con desenfoque fuerte en el montaje (`gblur`), con un leve zoom.
6. `Lush red potted poinsettia in sharp focus on a Christmas Eve table, warm string lights in the background, rich color, premium editorial photography, vertical 9:16, no text, no watermark` · `slow orbit around the plant, lights twinkle` (el paso de borroso a nítido se hace en el montaje, animando el desenfoque de 20 a 0 en 0.4 s)
7. Edición de la imagen 6: `replace the background with a clean cream studio backdrop, keep the poinsettia and its pot exactly the same` · `locked-off, leaves move slightly`
8. Edición de la imagen 6: `place this exact poinsettia and pot on the balcony of a colorful Old San Juan colonial house at golden hour, Christmas lights, blue cobblestone street below` · `slow push-in, lights twinkle`

## Portada

YouTube Shorts no siempre deja subir portada propia (a veces solo se escoge un cuadro del video). Por eso el **primer cuadro de la toma 1** se compone igual que la portada: silueta al centro y el texto del gancho legible. Instagram y Facebook sí aceptan la portada aparte.


Silueta negra de la planta con un signo de interrogación dorado encima, fondo rojo. Texto: `¿LA ADIVINAS?` arriba, `3 PISTAS` abajo.

```
Black silhouette of a potted plant with a large matte gold question mark over it,
deep red glowing background, dramatic, premium poster look, 9:16, no text
```

## Interacción fuera del video

- **Comentario fijado:** “1 = eres florista 🌿 · 2 = sabes de historia · 3 = por lo menos sabes que es Navidad 😅”
- **Stories de Instagram/Facebook:** la toma 2 sola con el *sticker* de quiz (4 opciones: Pascua, Anturio, Hibisco, Rosa) un día antes, como adelanto.
- **YouTube:** encuesta en la pestaña de Comunidad con la misma pregunta.
- **Respuesta a comentarios:** a quien diga “1”, se le contesta con la próxima flor como reto.

## Próximas flores con el mismo juego

| Flor | Pista 1 (difícil) | Pista 2 | Pista 3 (fácil) |
|------|-------------------|---------|-----------------|
| Gipsófila | Viene de las estepas de Europa del Este | En inglés su nombre habla del aliento de un bebé | Es lo blanquito que acompaña a las rosas |
| Girasol | No es una flor: son cientos de flores juntas | De joven sigue al sol durante el día | Amarillo, y de sus semillas se saca aceite |
| Cala | Es de Sudáfrica, no de México | Lo blanco es una sola hoja enrollada | En México le dicen alcatraz |
| Anturio | Lo rojo no es un pétalo | Parece de plástico encerado | Tiene forma de corazón |

> Las pistas de datos botánicos las valida Johnny antes de producir.
