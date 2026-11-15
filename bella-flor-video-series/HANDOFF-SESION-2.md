# HANDOFF · Serie de videos Bella Flor · Sesión 2 (MacBook + GB10)

**Para:** la nueva sesión de Claude Code que corre en la MacBook de Raphet, con acceso SSH a la GB10.
**De:** la sesión 1, que corría en la nube sin acceso a máquinas locales y solo pudo dejar guiones, prompts y herramientas.
**Repo:** `Raphet31/Complete-Python-3-Bootcamp` (https://github.com/Raphet31/Complete-Python-3-Bootcamp)
**Branch:** `claude/bella-flor-video-series-xuvnq7`
**Carpeta del proyecto:** `bella-flor-video-series/`. Todas las rutas de este documento son relativas a esa carpeta.
**Fecha del handoff:** 15 de noviembre de 2026.

---

## 0. Prompt de arranque (lo que Raphet pega en el chat nuevo)

```
Vas a continuar un proyecto de videos para Bella Flor Inc. que empezó en otra sesión de Claude que corría en la nube, sin acceso a máquinas locales. Tú sí tienes acceso a esta MacBook y, por SSH, a la GB10.

1. Clona o actualiza el repo https://github.com/Raphet31/Complete-Python-3-Bootcamp y haz checkout del branch claude/bella-flor-video-series-xuvnq7. Si ya existe localmente, haz pull de ese branch.
2. Lee completo bella-flor-video-series/HANDOFF-SESION-2.md. Ahí está todo el contexto, las decisiones tomadas y el plan paso a paso. Síguelo en orden.
3. Después lee bella-flor-video-series/glosario/G01-pascua-interactivo.md, que es el guion del video a producir.

Misión: producir el Short interactivo "Adivina la flor en 3 pistas · Pascua", generando las imágenes y los clips con modelos locales en la GB10 y montándolo con ffmpeg. Tiene que verse elaborado y premium, con gancho fuerte en los primeros 3 segundos y una portada que dé ganas de abrirlo.

Tienes permiso de meter mano en la MacBook y en la GB10 y de bajar modelos o herramientas si hacen falta; repórtame qué instalas y cuánto disco ocupa. Si la GB10 no responde (pudo apagarse con un apagón), avísame. Antes de generar el lote completo, enséñame una prueba de la toma 6. No publiques nada en ninguna red: me entregas el MP4 y la portada para aprobar.

Háblame en Spanglish boricua, directo y sin introducciones. Te dicto por voz, así que deduce cuando una palabra salga mal transcrita.
```

## 1. Misión de esta sesión

Producir el **primer video real y publicable**: el Short interactivo **“Adivina la flor en 3 pistas · Pascua”** (G01), generando imágenes y clips **en la GB10 con modelos locales**. Entregar a Raphet el MP4 final y la portada para aprobación. **No publicar nada en ninguna red.**

Meta de tiempo: tener G01 aprobado para publicarlo esta semana (16–20 de noviembre). Es temporada de pascuas.

Raphet autorizó a meter mano en la MacBook y en la GB10, y a bajar modelos o herramientas si hacen falta. Hay que reportar lo que se instale y cuánto disco ocupa.

## 2. Quién es quién y cómo comunicarse

- **Raphet Delgado:** VP de Innovación y Operaciones de Bella Flor Inc. (floristería en Puerto Rico; B2B con funerarias, kioscos, Shopify, Hana Florist POS). Dicta por voz, así que hay errores fonéticos: “auyama” = Ollama, “clot” = Claude, “Hixfield” = Higgsfield, “GBD” = GB10, “Facebook” puede ser “Fable” (un modelo de Claude). Deducir sin señalarlo.
- **Johnny (Juan González Vega):** Presidente y Maestro Floral. Valida todo dato floral, histórico o de taller antes de publicar.
- **Tono con Raphet:** Spanglish boricua, directo, sin introducciones. Resultados, no explicaciones largas.
- **Prioridad del negocio:** eficiencia y cero costos SaaS recurrentes. Por eso se genera en la GB10 y no en servicios pagos, salvo que la calidad no dé.

## 3. Decisiones ya tomadas (no re-discutir)

| Tema | Decisión |
|------|----------|
| Canales | **A. Bella Flor** (premium, elegante, vende) · **B. canal general de floristería** (jocoso y educativo, sin marca Bella Flor) · **C. interno** (videos no listados para empleados) |
| Imagen de Bella Flor | Premium: ilustración botánica editorial o fotorrealismo cálido. Nada de caricatura infantil. La caricatura solo va en el canal B |
| Voz | Voz agradable escogida por prueba, aplicada **voz a voz** sobre la grabación de Raphet (conserva el acento boricua y cambia el timbre). No se usa la voz de Johnny. Aún no se ha escogido la voz. **G01 no lleva voz** |
| Arranque | Serie del canal B **“¿Cómo le dices tú?”** (nombres de una flor por país) en **formato interactivo de 3 pistas** |
| Exigencia de Raphet | Debe verse **elaborado y visual**, con un gancho fuerte en los primeros 3 segundos y una portada que dé ganas de abrirlo. El borrador de texto sobre fondo plano que hizo `glosario/generar_shorts.py` **fue rechazado** por pobre |
| Herramienta de video | **GB10 con modelos locales.** Higgsfield (pago) queda como respaldo si la calidad local no da |

## 4. Archivos clave

| Archivo | Qué es |
|---------|--------|
| `glosario/G01-pascua-interactivo.md` | **Guion a producir:** 8 tomas con tiempos, texto, sonido, prompts, orden de generación, portada e interacción |
| `glosario/G01-pascua-version-elaborada.md` | Formato alterno, “la vuelta al mundo” (la flor fija mientras cambia el país). Segundo video a producir |
| `glosario/episodios.json` | Nombres por país de 12 flores. Los que tienen `"validar": true` están pendientes de Johnny |
| `glosario/generar_shorts.py` | Generador simple con Pillow y ffmpeg. Sus funciones de texto, zona segura y transiciones `xfade` sirven de base para el montaje; el formato visual en sí fue rechazado |
| `00-canales-marca-voz.md` | Estrategia de canales, línea visual (prompts base “editorial botánica” y “taller”) y plan de voz |
| `navidad-2026/` | Campaña de Navidad del canal A (plan, guiones N1–N4 y B1, guion de grabación). Viene después; arranca el 27 de noviembre |
| `educativos/E1-corona-como-hacerla.md` | How-to de la corona. Espera la nota de voz de Raphet con 10 respuestas |
| `01-tradiciones-outlines.md`, `04-como-funciona-outlines.md` | Outlines de las series largas |
| `handoff.md` | Visión general original del proyecto |

## 5. Plan de trabajo, en orden

### Paso 1 · Preparar
1. Clonar o actualizar el repo y hacer checkout del branch. Si el clone pide credenciales, usar las de GitHub que ya tenga la Mac (`gh auth status`); si no hay, preguntarle a Raphet.
2. Leer `glosario/G01-pascua-interactivo.md` completo.

### Paso 2 · Llegar a la GB10
1. Buscar el host en `~/.ssh/config`, `~/.ssh/known_hosts` o el historial de la terminal. Si no aparece, preguntarle a Raphet usuario e IP, en una sola pregunta.
2. Pudo apagarse con un apagón. Si no responde a `ssh`, avisar a Raphet que hay que prenderla y mientras tanto adelantar el Paso 5.3 (montaje) en la Mac.
3. Ya adentro: `nvidia-smi`, `df -h`, `free -h`, `uname -m`. La GB10 debe ser ARM64 (aarch64): algunas ruedas de Python y contenedores no tienen build para esa arquitectura.

### Paso 3 · Inventario de lo que ya hay
1. Buscar instalaciones existentes: ComfyUI, Ollama, venvs de Python, contenedores de Docker, carpetas `models/` o `checkpoints/`.
2. Raphet dice que videos que ya han generado “quedaron buenos, pero no tanto”. Encontrarlos (en la GB10 o en la Mac) y averiguar con qué se hicieron: modelo, resolución, pasos, CFG, número de cuadros. Diagnosticar por qué se ven flojos antes de cambiar nada.
3. Reportarle a Raphet en 5 líneas: qué hay, qué se usó antes y qué se propone.

### Paso 4 · Montar la cadena de generación
- **Tres capacidades hacen falta:**
  1. **Texto a imagen** fotorrealista (toma 6, pistas 1–3 y portada).
  2. **Edición de imagen con referencia**, para cambiar el fondo conservando la misma planta (tomas 7 y 8).
  3. **Imagen a video** (clips de unos 5 s).
- Escoger el mejor modelo disponible para cada una según lo que haya y lo que corra bien en ARM64 con la memoria de la GB10. Familias conocidas como referencia: FLUX.1 y Qwen-Image para imagen; Qwen-Image-Edit y FLUX.1 Kontext para edición; Wan 2.x, HunyuanVideo y LTX-Video para video. Confirmar versiones actuales y requisitos antes de bajar nada.
- **Licencias:** el contenido es comercial. Revisar la licencia de cada modelo y preferir las que permiten uso comercial (por ejemplo Apache 2.0). Algunas variantes de FLUX.1 tienen licencia no comercial. Si un modelo es dudoso, decírselo a Raphet antes de usarlo en el video final.
- Preferir **ComfyUI** si ya está instalado, controlándolo por su API desde scripts para que sea repetible.
- **Resolución:** generar en la resolución nativa del modelo (por ejemplo 720×1280 en video) y escalar a 1080×1920 en el montaje, con un escalador de IA si hay uno disponible. No forzar 1080×1920 en la generación, porque baja la calidad o se queda sin memoria.
- **Prueba de calidad antes del lote:** generar solo la toma 6 (imagen y clip), enseñársela a Raphet y ajustar. Si después de ajustar la calidad local no llega a lo que pide, decirlo claro y proponer Higgsfield solo para las tomas difíciles.

### Paso 5 · Producir G01
1. **Imágenes**, en este orden (el guion lo explica):
   - Toma 6 primero: la planta héroe.
   - Tomas 7 y 8: editando la imagen 6 (mismo tiesto y misma planta, otro fondo).
   - Tomas 1, 2 y 3: pistas.
   - La toma 4 no se genera (es la 6 desenfocada en el montaje) y la 5 es negro con números.
2. **Clips:** cada imagen a un clip de unos 5 s con su prompt de movimiento.
3. **Montaje con ffmpeg por script** (repetible para las próximas flores):
   - Cortes y tiempos exactos del guion, 1080×1920 a 30 fps.
   - Texto: serif elegante (bajar Playfair Display u otra serif libre de Google Fonts, licencia OFL), blanco con sombra suave o panel, siempre dentro de la zona segura: nada en los 350 px de abajo ni en los 170 px de la derecha.
   - Barra de tiempo que se vacía durante cada pista, y conteo 3 · 2 · 1 grande.
   - Toma 4 → 6: el desenfoque baja de golpe al revelar (detalle en el guion).
   - Banderas de la toma 7 como imágenes PNG (por ejemplo Twemoji, licencia CC-BY 4.0, con atribución en la descripción). ffmpeg no dibuja emoji.
   - Sonido: música y efectos **libres de derechos** (golpe, tic-tac, campanitas, acorde de revelación, *pops*, cuatro y coquí al cierre). Si no hay en la máquina, buscar fuentes CC0 y documentar el origen y la licencia de cada sonido en la receta. **Nada con copyright.**
   - Mezcla: música por debajo de los efectos, *fade out* final, y normalizar el audio final a unos -14 LUFS (`loudnorm`), que es el estándar de redes.
   - El primer cuadro tiene que funcionar como portada (YouTube Shorts a veces solo deja escoger un cuadro del video).
4. **Portada:** generar la imagen del guion, ponerle “¿LA ADIVINAS?” y “3 PISTAS”, y exportarla en 1080×1920, 1280×720 y 1080×1350.
5. **Guardar todo** en `glosario/produccion/G01/`:
   - `G01-pascua-final.mp4`
   - las portadas
   - `clips/` e `imagenes/`
   - `RECETA.md` con modelo, versión, semilla, pasos y ajustes de cada toma, y el origen y la licencia de cada sonido y fuente
6. **Entregar:** abrir el MP4 y la portada en la Mac para que Raphet los vea. Decirle qué datos siguen pendientes de Johnny (sección 6).

### Paso 6 · Dejarlo reutilizable
- Convertir el flujo en un comando, por ejemplo `python3 glosario/producir.py G02`, que tome un guion y saque el video. Las próximas flores (gipsófila, girasol, cala, anturio) ya tienen pistas al final del guion de G01.
- Los clips, imágenes y modelos pesados **no van a git**: añadirlos a `glosario/.gitignore`. Solo scripts, recetas, portadas y el MP4 final si pesa menos de 50 MB.
- Hacer pull antes de commit, commit en el mismo branch y push. Nunca force push.

## 6. Reglas

- **No publicar** en YouTube, Instagram, Facebook ni TikTok. Todo pasa por Raphet.
- Los datos marcados ⚠️ o con `"validar": true` no salen en un video publicado sin el visto bueno de Johnny. En G01 está pendiente que **los aztecas usaban la pascua para tinte rojo** (pista 2); las pistas 1 y 3 y los tres nombres de la toma 7 son seguros. Se puede producir, pero hay que señalarlo en la entrega.
- El canal B no lleva nombre ni logo de Bella Flor.
- No poner caras de personas reales ni imitar marcas.
- No dejar procesos corriendo en la GB10 al terminar, salvo que Raphet lo pida.
- Si algo bloquea (GB10 apagada, falta una credencial), decirlo en una línea y seguir con lo que no dependa de eso.

## 7. Pendientes del lado del negocio (no bloquean el Paso 5)

1. Nombre del canal B (opciones: “Entre Flores”, “El Taller Floral”, “Flor Adentro”; disponibilidad sin verificar).
2. Escoger la voz: Raphet graba el párrafo de prueba de `00-canales-marca-voz.md` (sección 4).
3. Johnny valida los ⚠️ de la campaña de Navidad y de `glosario/episodios.json`.
4. Nota de voz de Raphet para el how-to de la corona (10 preguntas en `educativos/E1-corona-como-hacerla.md`).
5. La campaña de Navidad del canal A arranca el 27 de noviembre de 2026 (ver `navidad-2026/00-plan-navidad.md`); necesita el canal de YouTube de Bella Flor creado y la voz escogida.
