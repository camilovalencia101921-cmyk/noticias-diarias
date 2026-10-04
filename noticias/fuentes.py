"""Descarga de feeds RSS/Atom y sitemaps de noticias."""
import calendar
import hashlib
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus

import feedparser

from .utils import ahora_utc, dominio, es_dominio_oficial, http_get, limpiar_html, tokens


@dataclass
class Noticia:
    titulo: str
    enlace: str
    fuente: str
    alcance: str = "nacional"          # local | nacional | internacional
    filtro: str = "estricto"
    descripcion: str = ""
    fecha: datetime | None = None
    imagen: str = ""
    video: str = ""
    etiquetas: list = field(default_factory=list)
    temas_pista: list = field(default_factory=list)
    oficial: bool = False
    google_news: bool = False
    youtube: bool = False
    # --- se completan durante el proceso ---
    tema: str | None = None
    categoria_local: str | None = None
    zona_prioridad: int = 0
    seccion: str = ""
    criterios: dict = field(default_factory=dict)
    puntaje: int = 0
    fuentes_cluster: set = field(default_factory=set)
    resumen: str = ""
    por_que: str = ""
    posible_patrocinio: bool = False
    vigilada: bool = False
    seguimiento_dia: int = 0
    penal_sensacionalismo: int = 0

    @property
    def id(self):
        return hashlib.md5(self.enlace.encode("utf-8")).hexdigest()[:10]

    @property
    def tokens(self):
        return tokens(self.titulo)


GN_SUFIJO = re.compile(r"\s+-\s+[^-]{2,60}$")


def url_google_news(consulta, dias=2):
    q = quote_plus(f"{consulta} when:{dias}d")
    return f"https://news.google.com/rss/search?q={q}&hl=es-419&gl=CO&ceid=CO:es-419"


def _fecha(entry):
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if t:
        return datetime.fromtimestamp(calendar.timegm(t), tz=timezone.utc)
    return None


def _imagen_entry(e):
    for m in e.get("media_content", []) or []:
        tipo = (m.get("type") or "") + (m.get("medium") or "")
        if "image" in tipo and m.get("url"):
            try:
                if int(m.get("width") or 999) < 200:
                    continue
            except ValueError:
                pass
            return m["url"]
    for m in e.get("media_thumbnail", []) or []:
        if m.get("url"):
            return m["url"]
    for l in e.get("links", []) or []:
        if l.get("rel") == "enclosure" and "image" in (l.get("type") or ""):
            return l.get("href", "")
    for enc in e.get("enclosures", []) or []:
        if "image" in (enc.get("type") or ""):
            return enc.get("href", "")
    html_txt = (e.get("content") or [{}])[0].get("value", "") + (e.get("summary") or "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html_txt)
    return m.group(1) if m else ""


def _video_entry(e):
    for m in e.get("media_content", []) or []:
        tipo = (m.get("type") or "") + (m.get("medium") or "")
        if ("video" in tipo or "shockwave" in tipo) and m.get("url"):
            return m["url"]
    for l in (e.get("links") or []) + (e.get("enclosures") or []):
        if "video" in (l.get("type") or ""):
            return l.get("href", "")
    return ""


def leer_rss(fuente, contenido):
    f = feedparser.parse(contenido)
    url = fuente["url"]
    es_gn = "news.google.com" in url
    es_yt = "youtube.com/feeds" in url
    salida = []
    for e in f.entries:
        titulo = limpiar_html(e.get("title", ""))
        enlace = e.get("link", "")
        if not titulo or not enlace:
            continue
        nombre = fuente["nombre"]
        desc = limpiar_html(e.get("summary") or "")
        if es_gn:
            src = (e.get("source") or {}).get("title") or ""
            titulo = GN_SUFIJO.sub("", titulo) if src else titulo
            nombre = src or nombre
            desc = ""                                   # en Google News solo trae enlaces
        if fuente.get("solo_alertas") and not re.search(r"\b(orange|red)\b", titulo, re.I):
            continue                                    # GDACS: solo alertas naranja/roja
        n = Noticia(
            titulo=titulo, enlace=enlace, fuente=nombre,
            alcance=fuente.get("alcance", "nacional"), filtro=fuente.get("filtro", "estricto"),
            descripcion=desc[:1200], fecha=_fecha(e),
            imagen=_imagen_entry(e), video=_video_entry(e),
            etiquetas=[t.get("term", "") for t in e.get("tags", []) or []],
            temas_pista=list(fuente.get("temas") or []),
            oficial=bool(fuente.get("oficial")) or es_dominio_oficial(enlace),
            google_news=es_gn, youtube=es_yt,
        )
        if es_yt:
            n.video = enlace
            n.descripcion = desc[:600]
        salida.append(n)
    return salida


def leer_sitemap(fuente, contenido):
    texto = contenido.decode("utf-8", "replace") if isinstance(contenido, bytes) else contenido
    salida = []
    excl = fuente.get("excluir_rutas") or []
    for bloque in re.findall(r"<url>(.*?)</url>", texto, re.S):
        loc = re.search(r"<loc>\s*(.*?)\s*</loc>", bloque, re.S)
        tit = re.search(r"<news:title>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</news:title>", bloque, re.S)
        if not loc or not tit:
            continue
        url = loc.group(1).strip()
        if any(r in url for r in excl):
            continue
        fec = re.search(r"<news:publication_date>\s*(.*?)\s*</news:publication_date>", bloque, re.S)
        img = re.search(r"<image:loc>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</image:loc>", bloque, re.S)
        kw = re.search(r"<news:keywords>\s*(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?\s*</news:keywords>", bloque, re.S)
        fecha = None
        if fec:
            try:
                fecha = datetime.fromisoformat(fec.group(1).strip().replace("Z", "+00:00"))
                fecha = fecha.astimezone(timezone.utc)
            except ValueError:
                pass
        salida.append(Noticia(
            titulo=limpiar_html(tit.group(1)), enlace=url, fuente=fuente["nombre"],
            alcance=fuente.get("alcance", "local"), filtro=fuente.get("filtro", "flexible"),
            fecha=fecha, imagen=img.group(1).strip() if img else "",
            etiquetas=[k.strip() for k in (kw.group(1).split(",") if kw else [])],
            temas_pista=list(fuente.get("temas") or []),
            oficial=bool(fuente.get("oficial")),
        ))
    return salida


def descargar_fuente(fuente):
    """Devuelve (lista_de_noticias, error_o_None)."""
    try:
        r = http_get(fuente["url"], timeout=20)
        if r.status_code != 200:
            return [], f"HTTP {r.status_code}"
        if fuente.get("tipo") == "sitemap":
            items = leer_sitemap(fuente, r.content)
        else:
            items = leer_rss(fuente, r.content)
        if not items:
            return [], "sin titulares"
        return items, None
    except Exception as ex:  # noqa: BLE001
        return [], f"{type(ex).__name__}: {str(ex)[:80]}"


def fuentes_activas(cfg):
    """Une fuentes nacionales/internacionales, locales y las búsquedas de local."""
    lista = [f for f in cfg.get("fuentes", []) if f.get("activo", True)]
    loc = cfg.get("local", {}) or {}
    if loc.get("activo", True):
        for f in loc.get("fuentes", []) or []:
            if f.get("activo", True):
                lista.append({**f, "alcance": "local", "filtro": f.get("filtro", "flexible")})
        modo = loc.get("modo", "zonas")
        if modo == "personalizado":
            for f in (loc.get("personalizado", {}) or {}).get("feeds", []) or []:
                if f and f.get("url"):
                    lista.append({"nombre": f.get("nombre", dominio(f["url"])), "url": f["url"],
                                  "alcance": "local", "filtro": f.get("filtro", "flexible")})
        if loc.get("buscar_en_google_news", True):
            for nombre, consulta, prio in consultas_locales(loc):
                lista.append({"nombre": f"{nombre} (Google News)", "url": url_google_news(consulta),
                              "alcance": "local", "filtro": "flexible", "zona_prioridad": prio})
    return lista


def consultas_locales(loc):
    modo = loc.get("modo", "zonas")
    out = []
    if modo == "ciudad":
        c = loc.get("ciudad", {}) or {}
        if c.get("nombre"):
            out.append((c["nombre"], f'"{c["nombre"]}"', 1))
    elif modo == "zonas":
        for i, z in enumerate(loc.get("zonas", []) or [], start=1):
            lugares = z.get("lugares") or [z.get("nombre")]
            q = " OR ".join(f'"{l}"' for l in lugares if l)
            if q:
                out.append((z.get("nombre", "Zona"), q, i))
    elif modo == "personalizado":
        pals = (loc.get("personalizado", {}) or {}).get("palabras_clave", []) or []
        if pals:
            out.append(("Local", " OR ".join(f'"{p}"' for p in pals[:8]), 1))
    return out


def consultas_departamento(loc):
    modo = loc.get("modo", "zonas")
    if modo == "ciudad":
        c = loc.get("ciudad", {}) or {}
        q = c.get("busqueda_departamento") or c.get("departamento")
        return [(c.get("departamento", "Departamento"), q, 1)] if q else []
    if modo == "zonas":
        return [(z.get("nombre", "Zona"), z.get("busqueda_departamento"), i)
                for i, z in enumerate(loc.get("zonas", []) or [], start=1) if z.get("busqueda_departamento")]
    return []


def descargar_todas(fuentes, hilos=12):
    noticias, errores = [], {}
    with ThreadPoolExecutor(hilos) as ex:
        for f, (items, err) in zip(fuentes, ex.map(descargar_fuente, fuentes)):
            if err:
                errores[f["nombre"]] = err
            for n in items:
                n.zona_prioridad = f.get("zona_prioridad", 0)
            noticias.extend(items)
    return noticias, errores


def filtrar_por_edad(noticias, horas):
    limite = ahora_utc() - timedelta(hours=horas)
    futuro = ahora_utc() + timedelta(hours=30)
    out, viejas = [], 0
    for n in noticias:
        if n.fecha is None:
            n.fecha = ahora_utc()
        if n.fecha > futuro:
            viejas += 1
            continue
        if n.fecha > ahora_utc():
            n.fecha = ahora_utc()       # algunos medios fechan la edición del día siguiente
        if n.fecha < limite:
            viejas += 1
            continue
        out.append(n)
    return out, viejas
