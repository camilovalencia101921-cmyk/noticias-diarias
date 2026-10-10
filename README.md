# Noticias diarias

Cuatro veces al día (hacia las **5:47 a. m., 11:17 a. m., 4:37 p. m. y 8:53 p. m.**, hora de Colombia), este proyecto arma una página de noticias pensada para el celular y la publica gratis con **GitHub Pages**.

- Costo: **cero**. Usa GitHub Actions, GitHub Pages y el nivel gratuito de Gemini (Google AI Studio).
- Si Gemini falla o se acaba la cuota, la página se genera igual en **modo de respaldo (sin IA)**.
- Todo lo que se puede cambiar está en **`config.yaml`**, con interruptores `activo: true` / `activo: false`.

> ⚠️ **ADVERTENCIA: el repositorio es PÚBLICO.** Cualquier persona puede ver `config.yaml` (tus temas, ciudades, palabras vigiladas, medios) y la carpeta `data/` (historial y registros). **No escribas datos personales en ningún archivo.** Las claves (Gemini, Telegram, correo) van SOLO como *Secrets* de GitHub, nunca en los archivos.

## Cómo se usa la página (Fase 1)

- **Pestañas:** 📰 Hoy · 📍 Local · 🌎 Mundo · 🧠 IA · 🎮 Ocio · 😂 Humor · 🏛️ Historia · 🙏 Fe · 🔖 Guardado. Cada una tiene **subfiltros** (por ejemplo, en Mundo: ✨ Todo, ⚔️ Guerras, 🌐 Geopolítica, ⛽ Energía, 🤝 Diplomacia).
- **Dos niveles:** primero vienen las **destacadas**, las de mayor impacto y con resumen corto. Al final de cada pestaña, el botón **"Ver N noticias más"** carga el resto: titular, medio, hora y enlace, sin IA y solo de **medios aprobados**. Las que parecen exageradas llevan la etiqueta "Posible sensacionalismo", pero no se ocultan.
- **"N medios cubren esto":** cuando varios medios publican la misma noticia, sale una sola tarjeta con la lista de enlaces.
- **Interruptor ⚡ Rápido · 2 min / 📚 Completo:** el modo Rápido muestra solo las noticias clave, sin "Ver más".
- **Barra inferior:** Inicio, Guardadas y Ajustes. En Ajustes está el tamaño de letra (A- / A+), los medios y palabras que bloqueaste, las noticias ocultas, el resumen del filtro del día y los días anteriores.
- **Tu información se queda en tu celular:** lo que lees, guardas o bloqueas se guarda solo en tu navegador, no en un servidor. Si cambias de celular o de navegador, empiezas de cero.
- **Escudo verde:** indica que el filtro de contenido sexual está activo. Ver [FILTRO.md](FILTRO.md).
- **Humor:** solo videos de YouTube de canales que tú apruebes. Agrégalos con el workflow **Agregar fuente**, eligiendo el alcance "humor", o en `config/humor_canales.json`.
- **Medios aprobados:** están en `config/medios_aprobados.json`. Para agregar uno, pega el link de su página en el workflow **Agregar fuente**. Los medios marcados `"sin_rss": true` no tienen RSS; sus noticias llegan por las búsquedas de Google News.

---

## Índice

1. [Primera instalación (una sola vez)](#1-primera-instalación-una-sola-vez)
2. [Ver la página y ponerla como inicio en Chrome (Android)](#2-ver-la-página-y-ponerla-como-inicio-en-chrome-android)
3. [Cómo editar `config.yaml` desde GitHub](#3-cómo-editar-configyaml-desde-github)
4. [Personalizar](#4-personalizar)
5. [Agregar, listar y eliminar fuentes](#5-agregar-listar-y-eliminar-fuentes)
6. [Canales opcionales: Telegram y correo](#6-canales-opcionales-telegram-y-correo)
7. [Cómo funciona por dentro](#7-cómo-funciona-por-dentro)
8. [Problemas frecuentes](#8-problemas-frecuentes)

---

## 1. Primera instalación (una sola vez)

### 1.1 Crear la clave gratuita de Gemini
1. Entra a **https://aistudio.google.com/apikey** con tu cuenta de Google.
2. Pulsa **"Create API key"** (Crear clave de API). Si te pide un proyecto, elige o crea uno cualquiera.
3. Copia la clave (empieza por `AIza...`). **No la pegues en ningún archivo.**

> El nivel gratuito no cobra nada y no necesita tarjeta. El programa solo envía titulares y descripciones públicas de noticias. Google puede usar lo que se envía en el nivel gratuito para mejorar sus productos; por eso nunca se envían datos personales.

> ⛔ **NO actives la facturación (Billing) de Google Cloud en el proyecto de esta clave.** Mientras no haya facturación, Google no puede cobrarte: si se acaba la cuota, simplemente responde "límite alcanzado" y la página sale en modo de respaldo. Con la facturación activada, la búsqueda de Google integrada (usada en la sección Cine) y el uso por encima de la cuota **se cobran**.

### 1.2 Guardar la clave como secreto en GitHub
1. En tu repositorio de GitHub, entra a **Settings** (Configuración).
2. Menú izquierdo: **Secrets and variables → Actions**.
3. Botón **New repository secret**.
4. *Name*: `GEMINI_API_KEY` — *Secret*: pega la clave. Pulsa **Add secret**.

### 1.3 Activar GitHub Pages
1. **Settings → Pages**.
2. En **Build and deployment → Source** elige **GitHub Actions**. (Importante: NO "Deploy from a branch").

### 1.4 Probar con una ejecución manual
1. Pestaña **Actions** del repositorio. Si aparece un aviso, pulsa **"I understand my workflows, go ahead and enable them"**.
2. A la izquierda elige **Noticias diarias** → botón **Run workflow** → **Run workflow**.
3. Espera 2–4 minutos. Si sale ✅ verde, la página quedó publicada. Si sale ❌ rojo, mira la sección [Problemas frecuentes](#8-problemas-frecuentes).

Desde ese momento se ejecuta sola **4 veces al día**. GitHub a veces arranca las tareas programadas con retraso, incluso de horas, cuando sus servidores están muy ocupados; por eso los horarios usan minutos "no redondos", que se retrasan menos. La página siempre muestra la hora real de actualización.

Si una ejecución falla, GitHub te envía un correo automáticamente (a la cuenta dueña del repositorio).

---

## 2. Ver la página y ponerla como inicio en Chrome (Android)

La dirección es: **`https://TU-USUARIO.github.io/noticias-diarias/`** (cambia `TU-USUARIO` por tu usuario de GitHub). También aparece en **Settings → Pages** y en cada ejecución de **Actions**.

Para que Chrome la abra al pulsar el botón de inicio (🏠):
1. Abre Chrome en el celular → menú **⋮** → **Configuración** (Ajustes).
2. **Página principal** (Página de inicio) → actívala.
3. Elige **Introducir dirección web personalizada** y pega la dirección de tu página.

La página no aparece en buscadores (tiene `noindex` y `robots.txt` que lo impide), pero cualquiera que tenga el enlace puede verla.

Opcional: escribe la dirección en `config.yaml` → `pagina: url_publica:` para que Telegram y correo incluyan el enlace.

---

## 3. Cómo editar `config.yaml` desde GitHub

1. En el repositorio, abre el archivo **`config.yaml`**.
2. Pulsa el **lápiz ✏️** (Edit this file).
3. Cambia lo que necesites. Respeta los espacios al inicio de cada línea (la "sangría"): son importantes.
4. Abajo pulsa **Commit changes…** → **Commit changes**.
5. El cambio se aplica en la siguiente ejecución (o pulsa **Run workflow** para verlo ya).

Reglas básicas del formato:
- Las listas se escriben entre corchetes y separadas por comas: `[palabra1, "frase con espacios", palabra3]`.
- Si una palabra tiene `:` o `#`, ponla entre comillas: `"atención:"`.
- `true` = encendido, `false` = apagado.

---

## 4. Personalizar

### 4.1 Encender o apagar temas
En `config.yaml` → sección `temas:`. Cada tema tiene:
```yaml
  justicia:
    nombre: "Justicia"
    activo: true      # false para apagarlo
    peso: 1.3         # más alto = más importante (1.0 es normal)
    color: "#AD1457"  # color de su etiqueta
    palabras: [...]   # palabras clave (se usan en el modo de respaldo)
```
Temas serios: seguridad, orden público, economía, inteligencia artificial, fenómenos naturales, geopolítica, guerras, justicia, mercados, política nacional, ciberseguridad, energía, salud pública, tecnología y contratación pública.
Temas de ocio: anime, fútbol, básquet (solo NBA/WNBA), freestyle e historia antigua.

**Reencender "Contratación pública y control":** en `temas: contratacion:` cambia `activo: false` por `activo: true`. Sus feeds (Procuraduría, Contraloría, Colombia Compra Eficiente) ya están en la lista de fuentes.

### 4.2 Cuántas noticias entran
Sección `seleccion:`:
- `minimo_serias: 6`, `minimo_ocio: 5`, `minimo_local: 5`: puntaje mínimo (de 1 a 10) para entrar.
- `max_serias: 10`, `max_ocio: 7`, `max_local: 8`, `max_fe: 4`: topes de **destacadas**. Lo local tiene su propio tope, aparte. **No son metas**: si pocas noticias superan el mínimo, la página trae menos. Para cambiarlos, edita el número.
- `cupo_por_tema: 3`: para que ningún tema acapare la página.
- `ver_mas_por_pestana: 40`: cuántas noticias carga "Ver N noticias más" en cada pestaña. `ver_mas_por_medio: 3` y `ver_mas_por_tema: 12` evitan que un solo medio o un solo tema llene la lista.

**"Ver N noticias más"**: es el resto de noticias de la pestaña, sin IA y solo de medios aprobados. Pasan los filtros de contenido sexual y de publicidad. No cuentan para los topes.

### 4.3 Encender o apagar mejoras
Sección `mejoras:`
| Mejora | Qué hace |
|---|---|
| `resumen` | Resumen de 2 líneas con hechos |
| `por_que_importa` | Una línea con el impacto para el lector. Edita `perfil_lector` para describirte (sin datos personales). |
| `palabras_vigiladas` | Si la enciendes (`activo: true`) y llenas `lista: [Ecopetrol, "Corte Constitucional"]`, esas noticias suben de importancia y llevan ⭐ |
| `seguimiento` | Si una historia ya salió en días anteriores, solo muestra lo nuevo con la etiqueta "Seguimiento · día N" |
| `mercados` | Dólar (TRM) y petróleo Brent con flecha y mini-gráfica de 30 días. Colcap y S&P 500 están listos pero apagados (`activo: false`). |
| `agenda` | Partidos de hoy y mañana (Liga BetPlay, Selección Colombia, Champions, NBA, WNBA) y estrenos de anime |
| `contador_descartes` | Al final: cuántos titulares se revisaron y cuántos se descartaron |

**Fechas de FMS y Red Bull Batalla:** no existe una fuente gratuita y automática con esas fechas, así que se agregan a mano en `mejoras: agenda: eventos_manuales:`:
```yaml
    eventos_manuales:
      - {fecha: "2026-11-29", nombre: "Final Internacional Red Bull Batalla", categoria: "Freestyle", enlace: "https://www.redbull.com/..."}
```
Aparecen en la Agenda el día anterior y el mismo día.

### 4.4 Editar listas de palabras (filtros)
- `filtro_sensacionalismo: frases_gancho`: frases de "clickbait" ("no vas a creer"…). Agrega o quita las que quieras.
- `filtro_sensacionalismo: superlativos`: "histórico", "brutal", "impactante"…
- `filtro_sensacionalismo: limite: 3`: cuántos puntos de "sensacionalismo" se aceptan antes de descartar.
- `filtro_publicidad: frases`: si aparecen en título, etiquetas o dirección, la nota se descarta (contenido patrocinado).
- `filtro_publicidad: frases_duda`: si aparecen, la nota entra con la etiqueta **"Posible patrocinio"**.
- `seleccion: palabras_descartar`: titulares que nunca entran (loterías, horóscopos…).
- `temas: <tema>: palabras`: palabras clave de cada tema.

### 4.5 Noticias locales: los 3 modos
Sección `local:`. Cambia `modo:` por uno de estos (los datos de los tres se guardan a la vez):
- **`"ciudad"`**: usa `ciudad: nombre` y `departamento`. Busca noticias de esa ciudad.
- **`"zonas"`** (el inicial): lista de zonas **en orden de prioridad**. Los ejemplos (Córdoba: Montería y Lorica; Medellín) están marcados con `# EJEMPLO`: **reemplázalos por los tuyos**.
- **`"personalizado"`**: usa `personalizado: palabras_clave` (barrios, alcaldía, gobernación, lugares) y `personalizado: feeds` (tus medios con `url` y `nombre`).

Además, `local: fuentes` son los medios locales que se leen siempre (El Meridiano, Q'hubo Medellín, etc.). Si un día no hay noticias locales, el bloque se omite; en "ciudad" y "zonas" primero intenta completar con noticias del departamento.

Categorías del bloque Local (con color propio): seguridad, orden público, movilidad y servicios públicos, y otros. Seguridad y orden público tienen peso extra.

**Botones de Instagram** (sección "Tus medios locales en Instagram"): el programa NO lee Instagram; solo muestra botones. La lista está en `local: instagram:`:
```yaml
  instagram:
    - {nombre: "El Meridiano", url: "https://www.instagram.com/elmeridiano.co", activo: true}
    - {nombre: "Chica Noticias", url: "", activo: false}     # pendiente de enlace
```
- Se muestran como máximo **6** botones, y solo los que tienen `activo: true` y una URL válida (`https://www.instagram.com/usuario`).
- Los perfiles **no están verificados** (Instagram exige iniciar sesión para revisarlos). Ábrelos tú una vez para confirmar que son los correctos.
- **Reactivar un pendiente** (Chica Noticias, El Propio, Q'hubo Medellín): escribe su `url` y cambia `activo: false` por `activo: true`. O más fácil: usa el workflow **Agregar fuente** (sección 5) con el link del perfil; si el nombre coincide con un pendiente, lo completa y lo reactiva.
- Para ocultar un botón sin borrarlo: `activo: false`.

### 4.5.1 "Para el alma" y "Cine"
- **Para el alma** (`para_el_alma:`): 3 temas al día para leer con calma (cristianismo y misticismo cristiano con frecuencia, budismo, estoicismo, sufismo, meditación y ciencia, símbolos, rituales y lugares sagrados). Los escribe Gemini, con la nota "Texto generado por IA; verifica antes de citar". Los títulos publicados se guardan en `temas-publicados.json` (últimos 120) para no repetirlos. Si Gemini falla ese día, la sección dice "Hoy no disponible" (no hay modo de respaldo para esta sección). Puedes cambiar la `frecuencia` de cada tradición o apagarla toda con `activo: false`.
- **Cine** (`cine:`): estrenos de películas en Colombia de la semana y próximos (sin conciertos ni música). Primero intenta la búsqueda de Google integrada de Gemini (una sola llamada al día, solo con modelos cuyo nivel gratuito la incluye). Si no está disponible, usa los datos públicos de la página de Cinemark Colombia. Si nada es confiable, muestra "Sin estrenos confirmados hoy". Nunca inventa películas ni fechas.

### 4.6 Cambiar el filtro de una fuente
Cada fuente tiene `filtro: estricto` o `filtro: flexible`:
- **estricto** (por defecto): aplica todas las reglas anti-sensacionalismo.
- **flexible** (medios locales): solo descarta los ganchos claros; los titulares directos o crudos de sucesos y judiciales no restan puntos.

Busca la fuente en `config.yaml` y cambia la palabra. Para apagar una fuente sin borrarla: `activo: false`.

### 4.7 Reemplazar las imágenes de categoría y la portada
- **Categorías:** cada tema tiene una ilustración automática. Para usar tu propia imagen, súbela a la carpeta `assets/categorias/` con el nombre de la clave del tema: por ejemplo `assets/categorias/justicia.png` o `assets/categorias/futbol.jpg`. Las de local se llaman `local_seguridad`, `local_orden_publico`, `local_movilidad_servicios` y `local_otros`.
- **Portada:** sube una foto como `assets/portada.jpg`. Se reduce sola a menos de 150 KB y se le pone una capa oscura para que el título se lea. Para apagarla: `portada_imagen: activo: false`. Sin portada se usa el azul oscuro `#17203A`.

Para subir un archivo desde GitHub: entra a la carpeta → **Add file → Upload files** → arrastra la imagen → **Commit changes**.

### 4.8 Logo "News", colores y bordes de las tarjetas
- **Logo:** el recuadro coral "News ●" a la derecha del título está dibujado con código (se ve nítido a cualquier tamaño). Para **apagarlo**: `logo: activo: false`. Para usar tu propio logo, sube `assets/logo.png` **cuadrado y de menos de 50 KB**; también se usará como ícono al "Añadir a pantalla de inicio" en el celular. Si la imagen no cumple, se usa el logo dibujado y el registro del día lo explica.
- **Ícono del celular:** en Chrome (Android) abre la página → menú **⋮** → **Añadir a pantalla de inicio**. El acceso directo usa el recuadro coral con la "N".
- **Cambiar colores:** cada tema tiene su `color:` en `temas:` (y las categorías locales en `local: categorias:`). Ese color se usa en la etiqueta y en el borde de la tarjeta. "Para el alma" usa `para_el_alma: color` y "Cine" usa `cine: color`. Escribe el color en formato `"#RRGGBB"` (puedes elegirlo en cualquier selector de color de internet).
- **Intensidad de los bordes** (`bordes_tema:`):
  - `opacidad_oscuro: 45` y `opacidad_claro: 55`: porcentaje de color del borde normal en modo oscuro y claro. Más alto = más visible.
  - `destacada_oscuro: 60` y `destacada_claro: 70`: lo mismo para "Lo más importante hoy".
  - `grosor: 1.5`: grosor en píxeles.
  - Para quitar los bordes: `bordes_tema: activo: false`.
- **Chip "Tecnología":** muestra solo las noticias de tecnología, inteligencia artificial y ciberseguridad de cualquier zona (incluidas las de "Ver más"). Puedes cambiar la lista en `chip_tecnologia: temas` o apagarlo con `activo: false`.

---

## 5. Agregar, listar y eliminar fuentes

### Opción fácil: desde el sitio de GitHub (sin programar)
1. Pestaña **Actions** → **Agregar fuente** → **Run workflow**.
2. Pega el **link** del medio (su página web, su feed, un canal de YouTube o un perfil de Instagram).
3. Elige **alcance** (local, nacional o internacional) y **filtro** (estricto o flexible; para locales usa flexible).
4. **Run workflow**. Abre la ejecución para ver el resultado: muestra los últimos 3 titulares si funcionó, o explica por qué no se guardó.

### Opción en computador (si tienes Python)
```bash
pip install -r requirements.txt
python agregar_fuente.py "https://www.ejemplo.com" --alcance nacional --filtro estricto
python agregar_fuente.py "https://www.youtube.com/@canal" --alcance local --filtro flexible
python agregar_fuente.py --listar
python agregar_fuente.py --eliminar 12
python agregar_fuente.py --eliminar "instagram.com/medio"
```

Qué hace el comando:
1. Si es Instagram: no lo lee; lo guarda como botón (o reactiva el que ya existía, incluso uno "pendiente de enlace" con el mismo nombre) y avisa.
2. Si es YouTube: obtiene el ID del canal desde el @usuario y usa su feed.
3. Busca el RSS en la página (`<link rel="alternate">`), luego prueba `/feed`, `/rss`, `/rss.xml`, `/feeds/all.rss`.
4. Si el sitio no tiene RSS, prueba su "sitemap de noticias" (enlaces directos).
5. **Plan B:** Google News filtrado por el dominio del medio (te avisa que lo usó).
6. Comprueba que haya titulares reales y recientes. Si es válido lo guarda sin duplicar (los locales dentro de `local:`); si no, no guarda nada y explica el motivo.

---

## 6. Canales opcionales: Telegram y correo

Están **apagados**. Si los enciendes sin poner los secretos, simplemente no hacen nada.

### Telegram
1. En Telegram, habla con **@BotFather** → `/newbot` → sigue los pasos y copia el **token**.
2. Escríbele cualquier mensaje a tu bot nuevo.
3. Abre en el navegador `https://api.telegram.org/botTU_TOKEN/getUpdates` y busca `"chat":{"id":NUMERO`. Ese número es el **chat id**.
4. Crea los secretos `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` (como en el paso 1.2).
5. En `config.yaml`: `canales: telegram: activo: true`.

### Correo (Gmail)
1. Tu cuenta de Google debe tener la **verificación en dos pasos** activa.
2. Crea una **contraseña de aplicación** en https://myaccount.google.com/apppasswords.
3. Crea los secretos `GMAIL_USUARIO` (tu correo de Gmail), `GMAIL_CLAVE_APP` (la contraseña de aplicación) y `CORREO_DESTINO` (a dónde enviar).
4. En `config.yaml`: `canales: correo: activo: true`.

---

## 7. Cómo funciona por dentro

1. **Fuentes:** lee los feeds de `config.yaml` (RSS, YouTube, sitemaps de noticias y búsquedas de Google News). Ignora lo de más de 36 horas.
2. **Filtros sin IA:** publicidad → palabras descartadas → sensacionalismo → duplicados (por similitud de títulos; si varios medios cuentan lo mismo, cuenta como "confirmación").
3. **Clasificación:** Gemini recibe en un solo lote los mejores candidatos y devuelve tema y 5 criterios (alcance, consecuencias, novedad, confirmación, profundidad). Un segundo lote escribe el resumen y "Por qué importa" solo de las elegidas. Máximo 2 llamadas al día.
4. **Respaldo:** si Gemini falla, el tema sale de palabras clave, el puntaje de reglas (fuente oficial, varias fuentes sobre el mismo hecho, palabras de impacto) y el resumen son las 2 primeras líneas del feed. Se omite "Por qué importa" y la página dice "Hoy se usó el modo de respaldo (sin IA)".
5. **Página:** `sitio/index.html`, un solo archivo con todo (sin librerías externas ni rastreadores). Las imágenes se cargan directamente desde el sitio de cada medio (no se copian).
6. **Archivo:** las ediciones anteriores quedan en `sitio/archivo/AAAA-MM-DD.html` (las últimas 7) con el enlace "Días anteriores".
7. **Historial y registros:** `data/historial.db` (SQLite) y `data/logs/AAAA-MM-DD.log` (qué se descartó y por qué, separando lo local). Se guardan 30 días de registros. El commit diario también evita que GitHub desactive la tarea por inactividad.

Fuentes de datos gratuitas: TRM de datos.gov.co (Superintendencia Financiera), Brent de Yahoo Finance, partidos del marcador público de ESPN y estrenos de anime de AniList.

Archivos principales:
```
config.yaml              ← todo lo configurable
generar.py               ← programa principal
agregar_fuente.py        ← agregar / listar / eliminar fuentes
noticias/                ← módulos (fuentes, filtros, IA, página…)
assets/                  ← tus imágenes opcionales (portada y categorías)
sitio/                   ← la página publicada
data/                    ← historial y registros (públicos)
.github/workflows/       ← tareas automáticas de GitHub
```

---

## 8. Problemas frecuentes

- **La ejecución sale en rojo (❌):** entra a la ejecución → paso que falló → lee el mensaje. Causas comunes:
  - *"Pages site not found"* o error en "Publicar": falta el paso 1.3 (Source = GitHub Actions).
  - *Error en el commit/push:* en **Settings → Actions → General → Workflow permissions** elige **Read and write permissions**.
  - *"casi ninguna fuente respondió":* problema temporal de internet; vuelve a ejecutar.
- **Dice "modo de respaldo (sin IA)":** revisa que el secreto se llame exactamente `GEMINI_API_KEY`. Si la cuota del día se agotó, al día siguiente vuelve a funcionar. El registro del día en `data/logs/` dice el motivo.
- **El modelo de Gemini cambió de nombre:** el programa busca solo el modelo Flash más reciente. Si quieres fijarlo, cambia `gemini: modelo:` en `config.yaml`.
- **Una fuente dejó de funcionar:** aparece en el registro del día en "Fuentes con problemas". Apágala (`activo: false`) o elimínala.
- **Quiero ver qué se descartó:** abre `data/logs/` y el archivo del día.
- **Se desactivó la tarea diaria:** GitHub desactiva tareas programadas tras 60 días sin actividad; el commit diario lo evita, pero si pasa, entra a **Actions → Noticias diarias → Enable workflow**.
