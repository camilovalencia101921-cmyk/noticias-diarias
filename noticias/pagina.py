"""Genera index.html autocontenido (CSS y JS dentro, sin librerías ni rastreadores)."""
import hashlib
import re
from html import escape

from .ilustraciones import DIBUJOS, simbolos
from .mercados import sparkline

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
SECCIONES = [("internacional", "Internacional", "🌎"), ("nacional", "Nacional", "🇨🇴"),
             ("local", "Local", "📍"), ("ocio", "Ocio", "🎮"), ("cine", "Cine", "🎬"),
             ("agenda", "Agenda", "📅"), ("alma", "Para el alma", "🕯️")]
ORDEN_LOCAL = ["seguridad", "orden_publico", "movilidad_servicios", "otros"]


def fecha_larga(d):
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def e(t):
    return escape(t or "", quote=True)


def color_fuente(nombre):
    h = int(hashlib.md5(nombre.encode()).hexdigest()[:4], 16) % 360
    return f"hsl({h} 45% 42%)"


def tiempo_relativo(fecha, ahora):
    s = max(0, (ahora - fecha).total_seconds())
    if s < 3600:
        return f"{int(s // 60)} min"
    if s < 86400:
        return f"{int(s // 3600)} h"
    return f"{int(s // 86400)} d"


class Pagina:
    def __init__(self, cfg, ctx):
        self.cfg = cfg
        self.ctx = ctx                 # dict con todo lo necesario
        self.temas = cfg.get("temas") or {}
        self.cats = ((cfg.get("local", {}) or {}).get("categorias", {}) or {})

    # ------------------------------------------------------------ piezas
    def clave_ilu(self, n):
        if n.seccion == "local" and n.categoria_local and not n.tema:
            return f"local_{n.categoria_local}"
        if n.seccion == "local" and n.categoria_local in ("seguridad", "orden_publico", "movilidad_servicios"):
            return f"local_{n.categoria_local}"
        return n.tema if n.tema in DIBUJOS else "general"

    def etiqueta(self, n):
        if n.seccion == "local":
            c = self.cats.get(n.categoria_local or "otros", {})
            return c.get("nombre", "Local"), c.get("color", "#546E7A")
        t = self.temas.get(n.tema or "", {})
        return t.get("nombre", "General"), t.get("color", "#455A64")

    def miniatura(self, n, prefijo, clase="th"):
        clave = self.clave_ilu(n)
        propia = self.ctx["imagenes_categoria"].get(clave) or self.ctx["imagenes_categoria"].get(n.tema or "")
        if propia:
            fondo = f'<img class="ilu" src="{prefijo}{e(propia)}" alt="" loading="lazy">'
        else:
            fondo = f'<svg class="ilu" aria-hidden="true"><use href="#ilu-{clave}"/></svg>'
        foto = ""
        if n.imagen:
            foto = (f'<img class="foto" src="{e(n.imagen)}" alt="" loading="lazy" decoding="async" '
                    f'referrerpolicy="no-referrer" onerror="this.remove()" '
                    f'onload="if(this.naturalWidth&&this.naturalWidth<160)this.remove()">')
        play = ""
        if n.video:
            play = (f'<a class="play" href="{e(n.video)}" target="_blank" rel="noopener noreferrer" '
                    f'aria-label="Ver video">▶</a>')
        return f'<div class="{clase}">{fondo}{foto}{play}</div>'

    def insignias(self, n):
        out = []
        if n.vigilada:
            out.append('<span class="badge vig">⭐ Vigilada</span>')
        if n.seguimiento_dia:
            out.append(f'<span class="badge seg">Seguimiento · día {n.seguimiento_dia}</span>')
        if n.posible_patrocinio:
            out.append('<span class="badge pat">Posible patrocinio</span>')
        return f'<div class="badges">{"".join(out)}</div>' if out else ""

    def meta(self, n, compacta=False):
        nombre, color = self.etiqueta(n)
        ahora = self.ctx["ahora_utc"]
        tag = f'<span class="tag" style="--c:{color}">{e(nombre)} · {n.puntaje}/10</span>'
        fuente = e(n.fuente)
        inicial = e((n.fuente.strip("¡¿\"' ") or "?")[0].upper())
        rel = tiempo_relativo(n.fecha, ahora)
        compartir = (f'<button class="share" type="button" data-u="{e(n.enlace)}" data-t="{e(n.titulo)}" '
                     f'aria-label="Compartir">{ICONO_COMPARTIR}</button>')
        if compacta:
            return (f'<div class="meta"><span class="av" style="background:{color_fuente(n.fuente)}">{inicial}</span>'
                    f'<span class="src">{fuente}</span></div><div class="meta">{tag}{compartir}</div>')
        return (f'<div class="meta"><span class="av" style="background:{color_fuente(n.fuente)}">{inicial}</span>'
                f'<span class="src">{fuente}</span><span class="dot">·</span>'
                f'<time datetime="{n.fecha.isoformat()}" data-t="{int(n.fecha.timestamp())}">{rel}</time>'
                f'{tag}{compartir}</div>')

    def es_tec(self, n):
        ct = self.cfg.get("chip_tecnologia", {}) or {}
        return n.tema in (ct.get("temas") or [])

    def attrs(self, n):
        """Color del borde (el mismo de la etiqueta) y marca para el chip Tecnología."""
        _, color = self.etiqueta(n)
        return f' style="--bc:{color}"' + (' data-tec="1"' if self.es_tec(n) else "")

    def tarjeta(self, n, prefijo):
        resumen = f'<p class="res">{e(n.resumen)}</p>' if n.resumen else ""
        pq = f'<p class="pq"><b>Por qué importa:</b> {e(n.por_que)}</p>' if n.por_que else ""
        return (f'<article class="card"{self.attrs(n)}>{self.insignias(n)}<div class="fila">'
                f'<h3><a class="stretch" href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a></h3>'
                f'{self.miniatura(n, prefijo)}</div>{resumen}{pq}{self.meta(n)}</article>')

    def destacada(self, n, prefijo):
        pq = f'<p class="pq"><b>Por qué importa:</b> {e(n.por_que)}</p>' if n.por_que else ""
        resumen = f'<p class="res">{e(n.resumen)}</p>' if n.resumen else ""
        tec = ' data-tec="1"' if self.es_tec(n) else ""
        return (f'<section class="sec" data-sec="{n.seccion}"{tec}><article class="card top"{self.attrs(n)}>'
                f'{self.miniatura(n, prefijo, "th grande")}'
                f'<div class="cuerpo"><span class="kicker">Lo más importante hoy</span>{self.insignias(n)}'
                f'<h2><a class="stretch" href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a></h2>'
                f'{resumen}<div class="barra" title="Importancia {n.puntaje}/10"><i style="width:{n.puntaje * 10}%"></i></div>'
                f'{pq}{self.meta(n)}</div></article></section>')

    def tarjeta_ocio_ancha(self, n, prefijo):
        resumen = f'<p class="res">{e(n.resumen)}</p>' if n.resumen else ""
        return (f'<article class="card ancha"{self.attrs(n)}>{self.miniatura(n, prefijo, "th grande")}<div class="cuerpo">'
                f'{self.insignias(n)}<h3><a class="stretch" href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a></h3>'
                f'{resumen}{self.meta(n)}</div></article>')

    def tarjeta_ocio_mini(self, n, prefijo):
        return (f'<article class="card mini"{self.attrs(n)}>{self.miniatura(n, prefijo, "th media")}<div class="cuerpo">'
                f'{self.insignias(n)}<h3><a class="stretch" href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a></h3>'
                f'{self.meta(n, compacta=True)}</div></article>')

    def cabecera_seccion(self, clave, nombre, icono, cuenta):
        return (f'<h2 class="sh"><span class="ic" aria-hidden="true">{icono}</span>{nombre}'
                f'<span class="n">{cuenta}</span></h2>')

    def mercados(self):
        if not self.ctx["mercados"]:
            return ""
        out = []
        for m in self.ctx["mercados"]:
            sube = m["cambio"] > 0
            baja = m["cambio"] < 0
            flecha = "▲" if sube else ("▼" if baja else "▬")
            clase = "up" if sube else ("down" if baja else "flat")
            valor = f'{m["valor"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
            prefijo = "$" if m["unidad"] in ("COP", "USD") else ""
            out.append(f'<div class="mk {clase}"><div class="mk-n">{e(m["nombre"])}</div>'
                       f'<div class="mk-v">{prefijo}{valor}<small> {m["unidad"]}</small></div>'
                       f'<div class="mk-c">{flecha} {abs(m["pct"]):.2f}% <span>vs. día anterior</span></div>'
                       f'{sparkline(m["serie"])}<div class="mk-f">30 días · dato del {e(m["fecha"])}</div></div>')
        return f'<section class="mercados" aria-label="Mercados">{"".join(out)}</section>'

    def agenda(self):
        items = self.ctx["agenda"]
        if not items:
            return ""
        filas, dia_actual = [], None
        for it in items:
            if it["dia"] != dia_actual:
                dia_actual = it["dia"]
                filas.append(f'<li class="ag-dia">{dia_actual}</li>')
            color = (self.temas.get(it["tema"], {}) or {}).get("color", "#546E7A")
            texto = e(it["texto"])
            if it.get("enlace"):
                texto = f'<a href="{e(it["enlace"])}" target="_blank" rel="noopener noreferrer">{texto}</a>'
            filas.append(f'<li><span class="ag-h">{e(it["hora"]) or "—"}</span>'
                         f'<span class="tag" style="--c:{color}">{e(it["categoria"])}</span><span class="ag-t">{texto}</span></li>')
        return (f'<section class="sec" data-sec="agenda" id="agenda">'
                f'{self.cabecera_seccion("agenda", "Agenda", "📅", len(items))}'
                f'<ul class="agenda">{"".join(filas)}</ul></section>')

    def ver_mas(self, lista):
        """Bloque plegable sin JavaScript con las siguientes mejores noticias (filas compactas)."""
        if not lista:
            return ""
        filas = []
        for n in lista:
            nombre, color = self.etiqueta(n)
            filas.append(
                f'<li{self.attrs(n)}><a href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a>'
                f'<div class="meta"><span class="src">{e(n.fuente)}</span><span class="dot">·</span>'
                f'<time datetime="{n.fecha.isoformat()}" data-t="{int(n.fecha.timestamp())}">'
                f'{tiempo_relativo(n.fecha, self.ctx["ahora_utc"])}</time>'
                f'<span class="tag" style="--c:{color}">{e(nombre)} · {n.puntaje}/10</span></div></li>')
        tec = ' data-tec="1"' if any(self.es_tec(n) for n in lista) else ""
        return (f'<details class="mas"{tec}><summary>Ver más ({len(lista)})</summary>'
                f'<ul>{"".join(filas)}</ul></details>')

    def cine(self):
        pelis, origen = self.ctx.get("cine", (None, ""))
        if pelis is None:
            return ""
        color = (self.cfg.get("cine", {}) or {}).get("color", "#D64550")
        cab = self.cabecera_seccion("cine", "Cine · estrenos en Colombia", "🎬", len(pelis))
        if not pelis:
            return (f'<section class="sec" data-sec="cine" id="cine" style="--sc:{color}">{cab}'
                    f'<p class="aviso">Sin estrenos confirmados hoy.</p></section>')
        filas, grupo = [], None
        for p in pelis:
            g = "Esta semana" if p["semana"] else "Próximos"
            if g != grupo:
                grupo = g
                filas.append(f'<li class="ag-dia">{g}</li>')
            f = p["fecha"]
            fuente = (f'<a class="fte" href="{e(p["enlace"])}" target="_blank" rel="noopener noreferrer">'
                      f'{e(p["fuente"] or "Fuente")}</a>') if p.get("enlace") else ""
            filas.append(
                f'<li class="peli"><span class="fd"><b>{f.day}</b>{MESES[f.month - 1][:3]}</span><div class="pd">'
                f'<div class="pt">{e(p["titulo"])} <span class="tag" style="--c:{color}">{e(p["genero"])}</span></div>'
                f'<div class="ps">{e(p["sinopsis"])}</div><div class="pf">Estreno: {DIAS[f.weekday()]} {f.day} de '
                f'{MESES[f.month - 1]}{" · " + fuente if fuente else ""}</div></div></li>')
        return (f'<section class="sec" data-sec="cine" id="cine" style="--sc:{color}">{cab}'
                f'<ul class="agenda cine" style="--bc:{color}">{"".join(filas)}</ul>'
                f'<p class="nota">Datos: {e(origen)}. Las salas pueden cambiar las fechas.</p></section>')

    def alma(self):
        temas = self.ctx.get("alma")
        if temas is None:
            return ""
        color = (self.cfg.get("para_el_alma", {}) or {}).get("color", "#C98A1B")
        cab = self.cabecera_seccion("alma", "Para el alma", "🕯️", len(temas))
        if not temas:
            return (f'<section class="sec" data-sec="alma" id="alma" style="--sc:{color}">{cab}'
                    f'<p class="aviso">Hoy no disponible.</p></section>')
        tarjetas = "".join(
            f'<article class="card alma" style="--bc:{color}"><span class="tag" style="--c:{color}">{e(t["nombre_categoria"])}</span>'
            f'<h3>{e(t["titulo"])}</h3><p class="txt">{e(t["resumen"])}</p>'
            f'<p class="pq"><b>Por qué es interesante:</b> {e(t["interes"])}</p>'
            f'<p class="preg">🤔 {e(t["pregunta"])}</p></article>' for t in temas)
        return (f'<section class="sec" data-sec="alma" id="alma" style="--sc:{color}">{cab}{tarjetas}'
                f'<p class="nota">Texto generado por IA; verifica antes de citar.</p></section>')

    def logo(self, prefijo):
        if not (self.cfg.get("logo", {}) or {}).get("activo", True):
            return ""
        if self.ctx.get("logo_png"):
            return f'<img class="logo-img" src="{prefijo}logo.png" width="40" height="40" alt="News">'
        return '<span class="logo" role="img" aria-label="News">News<i></i></span>'

    def css_bordes(self):
        b = self.cfg.get("bordes_tema", {}) or {}
        if not b.get("activo", True):
            return ""
        g = float(b.get("grosor", 1.5))
        return (f":root{{--bw:{g}px;--bo:{int(b.get('opacidad_claro', 55))}%;--bod:{int(b.get('destacada_claro', 70))}%}}"
                f"@media (prefers-color-scheme:dark){{:root{{--bo:{int(b.get('opacidad_oscuro', 45))}%;"
                f"--bod:{int(b.get('destacada_oscuro', 60))}%}}}}" + CSS_BORDES)

    # ------------------------------------------------------------ página
    def html(self, prefijo=""):
        c = self.ctx
        titulo = (self.cfg.get("pagina", {}) or {}).get("titulo", "Noticias diarias")
        partes = []
        if c["destacada"]:
            partes.append(self.destacada(c["destacada"], prefijo))
        for clave, nombre, icono in SECCIONES:
            if clave == "agenda":
                partes.append(self.agenda())
                continue
            if clave == "cine":
                partes.append(self.cine())
                continue
            if clave == "alma":
                partes.append(self.alma())
                continue
            lista = c["secciones"].get(clave, [])
            if not lista:
                continue
            total = len(lista) + (1 if c["destacada"] and c["destacada"].seccion == clave else 0)
            cuerpo = ""
            if clave == "ocio":
                ancha = next((n for n in lista if n.video), None)
                resto = [n for n in lista if n is not ancha]
                if ancha:
                    cuerpo += self.tarjeta_ocio_ancha(ancha, prefijo)
                cuerpo += f'<div class="grid">{"".join(self.tarjeta_ocio_mini(n, prefijo) for n in resto)}</div>'
            elif clave == "local":
                lista = sorted(lista, key=lambda n: (ORDEN_LOCAL.index(n.categoria_local) if n.categoria_local in ORDEN_LOCAL else 9, -n.puntaje))
                cuerpo = "".join(self.tarjeta(n, prefijo) for n in lista)
            else:
                cuerpo = "".join(self.tarjeta(n, prefijo) for n in lista)
            cuerpo += self.ver_mas(c.get("ver_mas", {}).get(clave, []))
            tec = ' data-tec="1"' if any(self.es_tec(n) for n in lista + c.get("ver_mas", {}).get(clave, [])) else ""
            partes.append(f'<section class="sec" data-sec="{clave}" id="{clave}"{tec}>'
                          f'{self.cabecera_seccion(clave, nombre, icono, total)}{cuerpo}</section>')
        if not any(c["secciones"].values()) and not c["destacada"]:
            partes.append('<p class="vacio">Hoy ninguna noticia superó el puntaje mínimo.</p>')

        # contador de descartes
        cont = ""
        if c["contador"]:
            k = c["contador"]
            cont = (f'<section class="contador"><h2 class="sh">🧹 Filtro de hoy</h2><p>Revisamos <b>{k["revisados"]}</b> titulares; '
                    f'entraron <b>{k["entraron"]}</b>. Descartados por sensacionalismo: <b>{k["sensacionalismo"]}</b> · '
                    f'publicidad: <b>{k["publicidad"]}</b> · baja importancia: <b>{k["baja_importancia"]}</b>'
                    f'{" · duplicados: <b>" + str(k["duplicados"]) + "</b>" if k.get("duplicados") else ""}.</p></section>')
        insta = ""
        if c["instagram"]:
            botones = "".join(
                f'<a class="ig" href="{e(b["url"])}" target="_blank" rel="noopener noreferrer">{ICONO_IG}{e(b["nombre"])}</a>'
                for b in c["instagram"])
            insta = f'<section class="insta"><h2 class="sh">Tus medios locales en Instagram</h2><div class="igs">{botones}</div></section>'
        archivo = ""
        if c["archivo"]:
            enlaces = "".join(f'<li><a href="{prefijo}archivo/{d}.html">{e(t)}</a></li>' for d, t in c["archivo"])
            archivo = f'<details class="archivo"><summary>Días anteriores</summary><ul>{enlaces}</ul></details>'
        inicio = f'<a class="volver" href="{prefijo}index.html">← Ir a la edición de hoy</a>' if prefijo else ""
        respaldo = '<p class="nota">Hoy se usó el modo de respaldo (sin IA)</p>' if c["modo_respaldo"] else ""
        if not respaldo and c.get("respaldo_resumenes"):
            respaldo = '<p class="nota">Hoy los resúmenes se hicieron en modo de respaldo (sin IA)</p>'

        portada = ""
        if c["portada"]:
            portada = (f' style="background-image:linear-gradient(rgba(10,14,28,.55),rgba(10,14,28,.78)),'
                       f'url(\'{prefijo}{c["portada"]}\')"')
        ct = self.cfg.get("chip_tecnologia", {}) or {}
        col = {"cine": (self.cfg.get("cine", {}) or {}).get("color", "#D64550"),
               "alma": (self.cfg.get("para_el_alma", {}) or {}).get("color", "#C98A1B"),
               "tec": ct.get("color", "#1D9E75")}
        chips = "".join(f'<button type="button" class="chip{" on" if v == "todo" else ""}" data-f="{v}"'
                        + (f' style="--c:{col[v]}"' if v in col else "") + f'>{t}</button>'
                        for v, t in [("todo", "Todo"), ("local", "Local"), ("nacional", "Nacional"),
                                     ("internacional", "Internacional"), ("ocio", "Ocio")]
                        + ([("tec", "Tecnología")] if ct.get("activo", True) else [])
                        + [("cine", "Cine"), ("agenda", "Agenda"), ("alma", "Para el alma")])
        sin_tec = '<p class="vacio solo-tec">Hoy no hay noticias de tecnología.</p>'
        if any('data-tec="1"' in x for x in partes):
            sin_tec = ""
        cuerpo = "".join(partes) + sin_tec
        css_extra = self.css_bordes()
        logo = self.logo(prefijo)
        iconos = (f'<link rel="apple-touch-icon" href="{prefijo}icono-180.png">\n'
                  f'<link rel="manifest" href="{prefijo}manifest.webmanifest">') if c.get("iconos") else ""
        favicon = (f'{prefijo}logo.png' if c.get("logo_png") else FAVICON)
        return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#17203A">
<title>{e(titulo)} · {e(c["fecha_corta"])}</title>
<link rel="icon" href="{favicon}">
{iconos}
<style>{CSS}{css_extra}</style>
</head>
<body data-f="todo">
{simbolos(c["colores"])}
<header class="cab"{portada}>
  <div class="tit"><h1>{e(titulo)}</h1>{logo}</div>
  <p class="fecha">{e(c["fecha_larga"]).capitalize()}</p>
  <p class="act">{e(c["actualizado"])}</p>
</header>
<main>
{inicio}
{self.mercados()}
<nav class="chips" aria-label="Filtrar">{chips}</nav>
{respaldo}
{cuerpo}
{cont}
{insta}
{archivo}
</main>
<footer>Resumen generado automáticamente. Cada noticia enlaza a su fuente original.</footer>
<div class="toast" id="toast" role="status"></div>
<script>{JS}</script>
</body>
</html>"""


FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
           "%3Crect width='100' height='100' rx='24' fill='%23D85A30'/%3E"
           "%3Cpath d='M30 74V26h10l20 31V26h10v48H60L40 43v31z' fill='%23fff'/%3E%3C/svg%3E")

CSS_BORDES = """
.card,.mas li,.agenda.cine{border:var(--bw) solid color-mix(in srgb,var(--bc,transparent) var(--bo),transparent)}
.card.top{border-color:color-mix(in srgb,var(--bc,transparent) var(--bod),transparent)}
.alma{border-left:4px solid var(--sc)}
.mas ul{padding:0 10px 4px}
.mas li{border-radius:12px;padding:10px 12px;margin-bottom:8px}
"""


def _usuario_ig(url):
    m = re.search(r"instagram\.com/([^/?#]+)", url)
    return m.group(1) if m else url


ICONO_COMPARTIR = ('<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="none" stroke="currentColor" '
                   'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7'
                   'M16 6l-4-4-4 4M12 2v13"/></svg>')
ICONO_IG = ('<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="5" '
            'fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" '
            'stroke-width="2"/><circle cx="17.5" cy="6.5" r="1.2" fill="currentColor"/></svg>')

CSS = """
:root{--bg:#eef0f4;--card:#fff;--tx:#15181e;--mu:#5d6472;--ln:#e3e6ec;--chip:#e3e7ef;--chipon:#17203A;--chiptx:#fff;
--acc:#17203A;--up:#1b8a4b;--down:#c62828;--sh:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.08)}
@media (prefers-color-scheme:dark){:root{--bg:#0e1116;--card:#181c23;--tx:#e8ebf0;--mu:#9aa2af;--ln:#2a2f39;
--chip:#232833;--chipon:#c8d3ff;--chiptx:#0e1116;--up:#4cc27f;--down:#ff6b6b;--sh:none}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;overflow-x:hidden;background:var(--bg);color:var(--tx);font:16px/1.45 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
main,.cab,footer{max-width:600px;margin:0 auto}
a{color:inherit}
.cab{background:#17203A center/cover no-repeat;color:#fff;padding:28px 16px 22px}
.cab h1{margin:0;font-size:1.75rem;letter-spacing:-.01em}
.tit{display:flex;align-items:center;gap:12px}
.tit h1{flex:0 1 auto;min-width:0;overflow-wrap:anywhere}
.logo{flex:none;display:inline-flex;align-items:center;gap:7px;background:#D85A30;color:#fff;border-radius:12px;
padding:8px 12px;font-size:19px;font-weight:500;line-height:1;letter-spacing:0;white-space:nowrap}
.logo i{display:block;width:9px;height:9px;border-radius:50%;background:#fff}
.logo-img{flex:none;width:40px;height:40px;border-radius:12px;object-fit:cover}
.cab .fecha{margin:4px 0 0;opacity:.92}
.cab .act{margin:2px 0 0;font-size:.85rem;opacity:.75}
main{padding:0 12px 24px}
.volver{display:inline-block;margin:12px 4px 0;font-size:.9rem}
.mercados{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}
.mk{background:var(--card);border-radius:16px;padding:12px;box-shadow:var(--sh);min-width:0}
.mk-n{font-size:.8rem;color:var(--mu)}
.mk-v{font-size:1.2rem;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mk-v small{font-size:.7rem;font-weight:500;color:var(--mu)}
.mk-c{font-size:.82rem;font-weight:600}.mk-c span{font-weight:400;color:var(--mu)}
.mk.up .mk-c,.mk.up .spark{color:var(--up)}.mk.down .mk-c,.mk.down .spark{color:var(--down)}.mk.flat .spark{color:var(--mu)}
.spark{display:block;width:100%;height:36px;margin-top:6px}
.mk-f{font-size:.7rem;color:var(--mu);margin-top:2px}
.chips{position:sticky;top:0;z-index:5;display:flex;gap:8px;overflow-x:auto;padding:12px 2px;margin:0 -2px;background:var(--bg);scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;border:0;border-radius:999px;padding:8px 14px;background:var(--chip);color:var(--tx);font:inherit;font-size:.9rem;cursor:pointer}
.chip.on{background:var(--chipon);color:var(--chiptx);font-weight:600}
.nota{font-size:.78rem;color:var(--mu);margin:0 4px 8px}
.sh{display:flex;align-items:center;gap:8px;font-size:1.1rem;margin:22px 4px 10px}
.sh .ic{font-size:1.1rem}
.sh .n{margin-left:auto;font-size:.78rem;font-weight:600;color:var(--mu);background:var(--chip);border-radius:999px;padding:2px 9px}
.card{position:relative;background:var(--card);border-radius:18px;padding:14px;margin-bottom:10px;box-shadow:var(--sh)}
.card:active{transform:scale(.995)}
.fila{display:flex;gap:12px;align-items:flex-start}
.card h3{flex:1;min-width:0;overflow-wrap:anywhere;margin:0;font-size:1.06rem;line-height:1.3;font-weight:650;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card h2{margin:6px 0 0;font-size:1.3rem;line-height:1.25}
.stretch{text-decoration:none}
.stretch::after{content:"";position:absolute;inset:0;border-radius:inherit;z-index:1}
.th{position:relative;flex:none;width:92px;height:92px;border-radius:14px;overflow:hidden;background:var(--chip)}
.th .ilu,.th .foto{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.th.grande{width:auto;height:auto;aspect-ratio:16/9;border-radius:14px}
.th.media{width:100%;height:auto;aspect-ratio:4/3;border-radius:12px}
.play{position:absolute;z-index:2;left:50%;top:50%;transform:translate(-50%,-50%);width:44px;height:44px;border-radius:50%;
background:rgba(0,0,0,.62);color:#fff;display:grid;place-items:center;text-decoration:none;font-size:18px;padding-left:3px;border:2px solid rgba(255,255,255,.85)}
.th:not(.grande):not(.media) .play{width:34px;height:34px;font-size:14px}
.res{margin:8px 0 0;color:var(--mu);font-size:.92rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pq{margin:8px 0 0;font-size:.88rem;padding:8px 10px;border-radius:10px;background:var(--chip)}
.meta{display:flex;align-items:center;gap:6px;margin-top:10px;font-size:.8rem;color:var(--mu);min-width:0}
.av{flex:none;width:22px;height:22px;border-radius:50%;color:#fff;display:grid;place-items:center;font-size:.72rem;font-weight:700}
.src{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:40%;color:var(--tx);font-weight:500}
.dot{opacity:.6}time{white-space:nowrap}
.tag{--c:#546E7A;margin-left:auto;flex:none;font-size:.74rem;font-weight:650;color:var(--c);background:color-mix(in srgb,var(--c) 14%,transparent);
border-radius:999px;padding:3px 9px;white-space:nowrap}
@media (prefers-color-scheme:light){.tag{color:color-mix(in srgb,var(--c) 80%,#000)}}
@media (prefers-color-scheme:dark){.tag{color:color-mix(in srgb,var(--c) 55%,#fff)}}
.share{position:relative;z-index:2;flex:none;border:0;background:transparent;color:var(--mu);padding:6px;margin:-6px -6px -6px 0;border-radius:50%;cursor:pointer;display:grid}
.share:hover{background:var(--chip)}
.badges{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px}
.badge{font-size:.72rem;font-weight:650;border-radius:6px;padding:2px 7px;background:var(--chip)}
.badge.seg{color:#1565C0}.badge.pat{color:#8a6d00;background:#fff3c4}.badge.vig{color:#8a5a00}
@media (prefers-color-scheme:dark){.badge.seg{color:#90caf9}.badge.pat{background:#4a3d00;color:#ffe082}}
.top{padding:0;overflow:hidden;margin-top:6px}
.top .th.grande{border-radius:0}
.top .cuerpo{padding:14px}
.kicker{display:inline-block;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#fff;background:#c62828;border-radius:6px;padding:3px 8px;margin-bottom:6px}
.barra{height:6px;border-radius:99px;background:var(--chip);margin-top:12px;overflow:hidden}
.barra i{display:block;height:100%;border-radius:99px;background:linear-gradient(90deg,#f9a825,#c62828)}
.ancha{padding:0;overflow:hidden}.ancha .th.grande{border-radius:0}.ancha .cuerpo{padding:12px 14px 14px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.mini{padding:8px;margin:0;display:flex;flex-direction:column;min-width:0}
.mini .cuerpo{padding:8px 2px 0;display:flex;flex-direction:column;flex:1}
.mini h3{font-size:.92rem}
.mini .meta{margin-top:8px}.mini .meta:last-child{margin-top:6px}.mini .src{max-width:none}
.mini .tag{margin-left:0;margin-right:auto}.mini .share{margin-right:0}
.agenda{list-style:none;margin:0;padding:6px 14px;background:var(--card);border-radius:18px;box-shadow:var(--sh)}
.agenda li{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--ln);font-size:.9rem}
.agenda li:last-child{border-bottom:0}
.agenda .ag-dia{font-weight:700;font-size:.8rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mu);padding-top:14px}
.ag-h{flex:none;width:44px;font-variant-numeric:tabular-nums;font-weight:600}
.agenda .tag{margin-left:0;flex:none}
.ag-t{flex:1;min-width:0}.ag-t a{text-decoration:none}
.contador p{margin:0 4px;font-size:.9rem;color:var(--mu)}
.igs{display:flex;flex-wrap:wrap;gap:8px;margin:0 4px}
.ig{display:inline-flex;align-items:center;gap:6px;text-decoration:none;font-weight:600;font-size:.9rem;color:#fff;border-radius:999px;padding:8px 14px;
background:linear-gradient(45deg,#f58529,#dd2a7b 50%,#8134af)}
.archivo{margin:22px 4px 0;font-size:.92rem}.archivo summary{cursor:pointer;font-weight:600}
.archivo ul{margin:8px 0 0;padding-left:20px}.archivo li{margin:4px 0}
.vacio{text-align:center;color:var(--mu);padding:30px 0}
footer{padding:18px 16px 40px;text-align:center;font-size:.8rem;color:var(--mu)}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#222;color:#fff;padding:10px 16px;border-radius:10px;font-size:.88rem;opacity:0;pointer-events:none;transition:opacity .2s}
.toast.on{opacity:1}
body:not([data-f="todo"]) .sec:not([data-sec]),body:not([data-f="todo"]) .contador,body:not([data-f="todo"]) .insta{display:none}
body[data-f="local"] .sec:not([data-sec="local"]),body[data-f="nacional"] .sec:not([data-sec="nacional"]),
body[data-f="internacional"] .sec:not([data-sec="internacional"]),body[data-f="ocio"] .sec:not([data-sec="ocio"]),
body[data-f="agenda"] .sec:not([data-sec="agenda"]),body[data-f="cine"] .sec:not([data-sec="cine"]),
body[data-f="alma"] .sec:not([data-sec="alma"]){display:none}
body[data-f="tec"] .sec:not([data-tec]),body[data-f="tec"] .card:not([data-tec]),body[data-f="tec"] .mas:not([data-tec]),
body[data-f="tec"] .mas li:not([data-tec]),body[data-f="tec"] .sh .n{display:none}
.solo-tec{display:none}body[data-f="tec"] .solo-tec{display:block}
.chip[style].on{background:var(--c);color:#fff}
.sec[style] .sh .ic{display:inline-grid;place-items:center;width:30px;height:30px;border-radius:9px;background:color-mix(in srgb,var(--sc) 18%,transparent)}
.aviso{margin:0 4px;padding:14px;border-radius:14px;background:var(--card);color:var(--mu);font-size:.92rem}
.mas{margin:2px 0 12px;background:var(--card);border-radius:16px;box-shadow:var(--sh)}
.mas summary{cursor:pointer;padding:12px 14px;font-weight:650;font-size:.92rem;list-style:none}
.mas summary::-webkit-details-marker{display:none}
.mas summary::after{content:"\25BE";float:right;color:var(--mu)}.mas[open] summary::after{content:"\25B4"}
.mas ul{list-style:none;margin:0;padding:0 14px 6px}
.mas li{padding:10px 0;border-top:1px solid var(--ln)}
.mas li>a{text-decoration:none;font-weight:600;font-size:.95rem;line-height:1.3;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}
.mas .meta{margin-top:6px}
.cine .peli{align-items:flex-start}
.fd{flex:none;width:44px;text-align:center;border-radius:10px;padding:4px 0;background:color-mix(in srgb,var(--sc) 14%,transparent);font-size:.72rem;text-transform:uppercase;color:var(--mu)}
.fd b{display:block;font-size:1.15rem;color:var(--tx)}
.pd{flex:1;min-width:0}.pt{font-weight:650}.pt .tag{margin-left:4px;vertical-align:1px}
.ps{color:var(--mu);font-size:.86rem;margin-top:2px}.pf{font-size:.78rem;color:var(--mu);margin-top:3px}
.fte{color:var(--tx)}
.alma{border-left:4px solid var(--sc)}
.alma .tag{margin-left:0}
.alma h3{-webkit-line-clamp:unset;display:block;margin-top:8px;font-size:1.1rem}
.alma .txt{margin:8px 0 0;font-size:.95rem;line-height:1.55}
.preg{margin:10px 0 0;font-style:italic;font-size:.92rem}
@media (min-width:640px){main{padding:0 0 24px}.cab{border-radius:0 0 22px 22px}}
"""

JS = """
(function(){
var b=document.body;
document.querySelectorAll('.chip').forEach(function(c){c.addEventListener('click',function(){
document.querySelectorAll('.chip').forEach(function(x){x.classList.toggle('on',x===c)});
b.setAttribute('data-f',c.getAttribute('data-f'));
if(c.getAttribute('data-f')==='tec'){document.querySelectorAll('details.mas[data-tec]').forEach(function(d){d.open=true});}});});
var now=Date.now()/1000;
document.querySelectorAll('time[data-t]').forEach(function(t){var s=Math.max(0,now-(+t.getAttribute('data-t')));
t.textContent=s<3600?Math.max(1,Math.floor(s/60))+' min':s<86400?Math.floor(s/3600)+' h':Math.floor(s/86400)+' d';});
var toast=document.getElementById('toast');
function aviso(m){toast.textContent=m;toast.classList.add('on');setTimeout(function(){toast.classList.remove('on')},1800);}
document.querySelectorAll('.share').forEach(function(btn){btn.addEventListener('click',function(ev){
ev.preventDefault();ev.stopPropagation();var u=btn.getAttribute('data-u'),t=btn.getAttribute('data-t');
if(navigator.share){navigator.share({title:t,url:u}).catch(function(){});}
else if(navigator.clipboard){navigator.clipboard.writeText(u).then(function(){aviso('Enlace copiado')});}
else{prompt('Copia el enlace:',u);}});});
})();
"""
