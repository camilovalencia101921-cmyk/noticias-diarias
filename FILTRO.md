# Filtro de contenido sexual

Es obligatorio y no se puede apagar. Funciona en **cinco capas**. La regla general es **"falla cerrado"**: si un filtro tiene una duda o un error, la noticia o la imagen **no se muestra**.

| Capa | Qué hace | Dónde se ajusta |
|---|---|---|
| **1. Lista blanca de medios** | "Ver más" y Humor solo muestran contenido de **medios y canales aprobados**. Si Gemini no está disponible, las destacadas también salen solo de medios aprobados. | `config/medios_aprobados.json` y `config/humor_canales.json` |
| **2. Lista de palabras** | Revisa el título, la descripción, las etiquetas y el enlace de **todo** lo que entra, en español y en inglés. Detecta variantes disfrazadas: `p0rn0`, `s.e.x.y`, `P O R N O`, `sexxxy`, `0nlyF4ns`. Si encuentra una palabra de la lista, la noticia se descarta. | `config.yaml` → `filtro_sexual` |
| **3. Revisión con Gemini** | En la misma llamada en que Gemini elige las destacadas, también responde si cada noticia tiene contenido sexual o sugerente. Si responde "sí" o "dudoso", la noticia se descarta, y también sale de "Ver más". Si Gemini no revisó una noticia, esa noticia no puede ser destacada. | Automático |
| **4. Imágenes** | Solo se muestra una miniatura si el medio está aprobado y la noticia pasó todos los filtros. En los demás casos se muestra el ícono del tema. En Humor **nunca** hay miniaturas externas: solo un bloque de color con ▶. | Automático |
| **5. Tus bloqueos** | El botón **⋯ / Ocultar** de cada noticia permite ocultar esa noticia, **bloquear el medio** o **bloquear una palabra**. Se guarda en tu navegador y se puede deshacer en **Ajustes**. | En la página |

## Cómo escribir palabras en la lista (capa 2)
- `"porn*"`: bloquea toda palabra que **empiece** así (porno, pornografía, pornhub…).
- `"sexy"`: bloquea solo la palabra completa. Así no se bloquean "sexto" ni "Essex".
- `"video de sexo"`: bloquea esa frase completa.

## Decisiones tomadas (puedes cambiarlas)
- **Noticias judiciales sobre delitos sexuales** (abuso, violación, acoso): **no** se ocultan por palabras, porque son información judicial y no contenido sexual. Las destacadas igual pasan por la revisión de Gemini. Para ocultarlas también, cambia `ocultar_delitos_sexuales: true` en `config.yaml`.
- Algunas palabras pueden ocultar noticias inocentes. Por ejemplo, "desnuda" en "la reforma desnuda las fallas del sistema". Se aceptó ese costo porque el filtro falla cerrado.

## Cómo comprobarlo
```bash
python pruebas/probar_filtro.py
```
Revisa titulares de ejemplo: los que deben bloquearse, incluidas las variantes disfrazadas, y los normales que deben pasar.

```bash
python pruebas/probar_imagenes.py
```
Comprueba que un medio no aprobado nunca muestre imagen.

En la página, el **escudo verde** del encabezado indica que el filtro está activo. En **Ajustes → Filtro de hoy** aparece cuántas noticias descartó cada capa ese día.
