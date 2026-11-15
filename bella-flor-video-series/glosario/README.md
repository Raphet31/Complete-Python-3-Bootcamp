# Serie “¿Cómo le dices tú?” · canal B

Una flor por Short: sus nombres en científico, inglés, México, España, LatAm y en el taller de PR. 15–18 s, texto en pantalla + música, **sin voz**. Lo genera `generar_shorts.py` solo.

## Para producir un episodio

1. **Foto** de la flor con el celular, **vertical**, fondo limpio (pared o papel crema), luz de ventana. La flor en la mitad de arriba; la de abajo la tapa el texto. Guardar como `fotos/<slug>.jpg` (ej. `fotos/pascua.jpg`).
2. **Johnny valida** los nombres marcados `"validar": true` en `episodios.json` y cambia el valor a `false`.
3. **Música** con licencia en `musica/` (opcional; la de la biblioteca de YouTube/TikTok también sirve si se pone al subir).
4. Correr: `python3 generar_shorts.py` → video y texto de publicación en `salida/`.

`--demo` genera borradores sin foto y sin validar, solo para revisión interna.

## Orden de publicación (3 por semana: lun, mié, vie)

| Semana | Episodios |
|--------|-----------|
| 16–20 nov | G01 Pascua · G12 Hypericum · G02 Gipsófila |
| 23–27 nov | G04 Cala · G05 Pompón · G03 Alstroemeria |
| 30 nov–4 dic | G06 Stock · G07 Leatherleaf · G08 Statice |
| 7–11 dic | G09 Gladiola · G10 Anturio · G11 Ave del paraíso |

Para añadir flores: copiar un bloque en `episodios.json` y cambiar los datos.
