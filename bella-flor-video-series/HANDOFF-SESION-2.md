# HANDOFF · Serie de videos Bella Flor · Sesión 2 (MacBook + GB10)

**Para:** la nueva sesión de Claude Code que corre en la MacBook de Raphet, con acceso SSH a la GB10.
**De:** la sesión 1, que corría en la nube sin acceso a máquinas locales y solo pudo dejar guiones, prompts y herramientas.
**Repo:** `raphet31/complete-python-3-bootcamp` · branch `claude/bella-flor-video-series-xuvnq7` · carpeta `bella-flor-video-series/`

---

## 1. Misión de esta sesión

Producir el **primer video real y publicable**: el Short interactivo **“Adivina la flor en 3 pistas · Pascua”**, generando las imágenes y los clips **en la GB10 con modelos locales**. Entregar a Raphet el MP4 final y la portada para aprobación. **No publicar nada en ninguna red.**

Raphet autorizó a meter mano en la MacBook y en la GB10, y a bajar modelos o herramientas si hacen falta. Hay que reportar lo que se instale y cuánto disco ocupa.

## 2. Quién es quién y cómo comunicarse

- **Raphet Delgado:** VP de Innovación y Operaciones de Bella Flor Inc. (floristería en Puerto Rico; B2B con funerarias, kioscos, Shopify, Hana Florist POS). Dicta por voz: deduce el contexto, porque hay errores fonéticos (“auyama” = Ollama, “clot” = Claude, “Hixfield” = Higgsfield, “GBD” = GB10).
- **Johnny (Juan González Vega):** Presidente y Maestro Floral. Valida todo dato floral, histórico o de taller antes de publicar.
- **Tono con Raphet:** Spanglish boricua, directo, sin introducciones. Resultados, no explicaciones largas.
- **Prioridad del negocio:** eficiencia y cero costos SaaS recurrentes. Por eso se genera en la GB10 y no en servicios pagos, salvo que la calidad no dé.

## 3. Decisiones ya tomadas (no re-discutir)

| Tema | Decisión |
|------|----------|
| Canales | **A. Bella Flor** (premium, elegante, vende) · **B. canal general de floristería** (jocoso y educativo, sin marca Bella Flor) · **C. interno** (videos no listados para empleados) |
| Imagen de Bella Flor | Premium: ilustración botánica editorial o fotorrealismo cálido. Nada de caricatura infantil. La caricatura solo va en el canal B |
| Voz | Voz agradable escogida por prueba, aplicada **voz a voz** sobre la grabación de Raphet (conserva el acento boricua y cambia el timbre). No se usa la voz de Johnny. Aún no se ha escogido la voz |
| Arranque | Serie del canal B **“¿Cómo le dices tú?”** (nombres de una flor por país) en **formato interactivo de 3 pistas** |
| Exigencia de Raphet | Debe verse **elaborado y visual**, con un gancho fuerte en los primeros 3 segundos y una portada que dé ganas de abrirlo. El borrador de texto sobre fondo plano **fue rechazado** por pobre |
| Herramienta de video | **GB10 con modelos locales.** Higgsfield queda como respaldo si la calidad local no da |

## 4. Archivos clave en el repo

| Archivo | Qué es |
|---------|--------|
| `glosario/G01-pascua-interactivo.md` | **Guion a producir:** 8 tomas con tiempos, texto, sonido, prompts de imagen y movimiento, portada e interacción |
| `glosario/G01-pascua-version-elaborada.md` | Formato alterno, “la vuelta al mundo” (la flor fija mientras cambia el país). Segundo video a producir |
| `glosario/episodios.json` | Nombres por país de 12 flores (los que tienen `"validar": true` están pendientes de Johnny) |
| `glosario/generar_shorts.py` | Generador simple con Pillow y ffmpeg. Reutilizar sus funciones de texto y xfade para el montaje; el formato visual en sí fue rechazado |
| `00-canales-marca-voz.md` | Estrategia de canales, línea visual (prompt base “editorial botánica” y “taller”) y voz |
| `navidad-2026/` | Campaña de Navidad del canal A: plan, guiones N1–N4 y B1, y el guion de grabación de voz. Viene después |
| `educativos/E1-corona-como-hacerla.md` | How-to de la corona: espera la nota de voz de Raphet con 10 respuestas |
| `01-tradiciones-outlines.md`, `04-como-funciona-outlines.md` | Outlines de las series largas |
| `handoff.md` | Visión general original del proyecto |

## 5. Plan de trabajo, en orden

### Paso 1 · Preparar
1. `git clone` del repo (o `git fetch`) y `git checkout claude/bella-flor-video-series-xuvnq7`.
2. Leer `glosario/G01-pascua-interactivo.md` completo.

### Paso 2 · Llegar a la GB10
1. Buscar el host en `~/.ssh/config`, `~/.ssh/known_hosts` o el historial de la terminal. Si no aparece, preguntarle a Raphet usuario e IP (una sola pregunta).
2. Puede haber estado apagada por un apagón. Si no responde a `ssh`, avisar a Raphet que hay que prenderla.
3. Ya adentro: `nvidia-smi`, `df -h`, `free -h`, `uname -m` (la GB10 es ARM64; algunas ruedas de Python no tienen build para aarch64).

### Paso 3 · Inventario de lo que ya hay
1. Buscar instalaciones existentes: ComfyUI, Ollama, venvs de Python, contenedores de Docker, carpetas `models/` o `checkpoints/`.
2. **Raphet dice que ya han generado videos ahí y “quedaron buenos, pero no tanto”.** Encontrar esos videos y el flujo o los ajustes que se usaron (modelo, resolución, pasos, CFG, cuadros). Diagnosticar por qué se ven flojos antes de cambiar nada.
3. Reportarle a Raphet en 5 líneas: qué hay, qué modelo se usó y qué se propone.

### Paso 4 · Montar la cadena de generación
- **Imagen:** el mejor modelo disponible para fotorrealismo (la familia FLUX.1 es la referencia; si no está, lo que haya). Verificar licencia de uso comercial.
- **Imagen a video:** el mejor modelo local disponible (opciones conocidas: Wan 2.x i2v, HunyuanVideo i2v, LTX-Video). Verificar qué corre bien en ARM64 con la memoria de la GB10, y su licencia comercial.
- Preferir **ComfyUI** si ya está instalado, controlándolo por su API desde scripts para que sea repetible.
- Puede bajar modelos (autorizado). Reportar el tamaño.
- **Prueba de calidad antes del lote:** generar solo la toma 6 (revelación de la pascua), enseñársela a Raphet y ajustar. Si después de ajustar la calidad local no llega al nivel de lo que pide, decirlo claro y proponer Higgsfield solo para las tomas difíciles.

### Paso 5 · Producir G01
1. Generar las imágenes iniciales de las tomas 1–8 con los prompts del guion, a 1080×1920 o lo más cercano al 9:16. Usar la toma 6 como referencia de la planta para que sea la misma pascua en las tomas 6, 7 y 8.
2. Pasar cada imagen a un clip de unos 5 s con su prompt de movimiento.
3. **Montaje con ffmpeg por script** (repetible para las próximas flores):
   - Cortes y tiempos exactos del guion. Escalar a 1080×1920 y 30 fps.
   - Texto: serif elegante, blanco con sombra suave o panel, siempre dentro de la zona segura (nada en los 350 px de abajo ni en los 170 px de la derecha). Bajar una fuente serif libre (Playfair Display o similar) en lugar de DejaVu.
   - Barra de tiempo que se vacía durante cada pista, y conteo 3 · 2 · 1 grande.
   - Sonido: música y efectos **libres de derechos** (golpe, tic-tac, campanitas, acorde de revelación, *pops*, cuatro y coquí al cierre). Si no hay en la máquina, buscar fuentes con licencia CC0 o la biblioteca de audio de YouTube, y documentar el origen de cada sonido. **Nada con copyright.**
   - Mezcla: música a -18 dB, efectos por encima, *fade out* final.
4. **Portada:** generar la imagen del guion y ponerle el texto “¿LA ADIVINAS?” y “3 PISTAS” en tres formatos: 1080×1920, 1280×720 y 1080×1350.
5. Guardar todo en `bella-flor-video-series/glosario/produccion/G01/`: `G01-pascua-final.mp4`, las portadas, `clips/`, `imagenes/` y un `RECETA.md` con modelo, semilla, pasos y ajustes de cada toma, para reproducirlo.
6. Enviarle a Raphet el MP4 y la portada para aprobación, y abrir el video en la Mac para que lo vea.

### Paso 6 · Dejarlo reutilizable
- Convertir el flujo en un comando: `python3 producir.py G02` toma un guion y saca el video. Las próximas flores (gipsófila, girasol, cala, anturio) ya tienen pistas en el guion de G01.
- Los clips y modelos pesados **no van a git** (`.gitignore`). Solo scripts, recetas, portadas y el MP4 final si pesa menos de 50 MB.
- Commit y push al mismo branch.

## 6. Reglas

- **No publicar** en YouTube, Instagram, Facebook ni TikTok. Todo pasa por Raphet.
- Los datos marcados ⚠️ o `"validar": true` no salen en un video final sin el visto bueno de Johnny. Para G01 están pendientes: que los aztecas usaban la pascua para tinte rojo y el nombre “Estrella federal” en Argentina. Se puede producir, pero hay que marcarlo como pendiente en la entrega.
- El canal B no lleva nombre ni logo de Bella Flor.
- No poner caras de personas reales ni imitar marcas.
- No dejar procesos corriendo en la GB10 al terminar, salvo que Raphet lo pida.
- Si algo bloquea (GB10 apagada, falta una credencial), decirlo en una línea y seguir con lo que no dependa de eso.

## 7. Pendientes del lado del negocio (no bloquean el Paso 5)

1. Nombre del canal B (opciones: “Entre Flores”, “El Taller Floral”, “Flor Adentro”; disponibilidad sin verificar).
2. Escoger la voz: Raphet graba el párrafo de prueba de `00-canales-marca-voz.md` (sección 4).
3. Johnny valida los ⚠️ de la campaña de Navidad y de `episodios.json`.
4. Nota de voz de Raphet para el how-to de la corona (10 preguntas en `educativos/E1-corona-como-hacerla.md`).
5. Calendario: la campaña de Navidad del canal A arranca el 27 de noviembre de 2026 (ver `navidad-2026/00-plan-navidad.md`).
