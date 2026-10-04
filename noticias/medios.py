"""Miniaturas y videos de las noticias elegidas.

Orden para video: media:content / enclosure del RSS (ya leídos), og:video, twitter:player,
iframes de YouTube o Vimeo. No se descargan videos ni imágenes: solo se guarda su dirección.
Cada página tiene un límite de tiempo (medios.limite_segundos).
"""
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

from .utils import _sesion

META = r'<meta[^>]+(?:property|name)=["\']{}["\'][^>]*>'


def _meta(texto, nombre):
    m = re.search(META.format(re.escape(nombre)), texto, re.I)
    if not m:
        return ""
    c = re.search(r'content=["\']([^"\']+)["\']', m.group(0), re.I)
    return html.unescape(c.group(1).strip()) if c else ""


def imagen_valida(url, cfg):
    if not url or not url.startswith("http"):
        return False
    m = (cfg.get("medios", {}) or {})
    u = url.lower()
    if any(p.lower() in u for p in m.get("descartar_imagenes_con", [])):
        return False
    # tamaños en la propia URL (ej. ?w=100 o -150x150.jpg)
    t = re.search(r"(?:[?&](?:w|width)=|-)(\d{2,4})x?(\d{2,4})?(?:\.|&|$)", u)
    if t and int(t.group(1)) < int(m.get("ancho_minimo", 200)) and (t.group(2) or "w=" in u or "width=" in u):
        return False
    return True


def leer_pagina(url, segundos):
    """Lee como máximo ~400 KB de la página dentro del límite de tiempo."""
    fin = time.monotonic() + segundos
    try:
        with _sesion.get(url, timeout=(3, segundos), stream=True, allow_redirects=True) as r:
            if r.status_code != 200 or "html" not in r.headers.get("content-type", "html"):
                return "", url
            partes, total = [], 0
            for trozo in r.iter_content(16384):
                partes.append(trozo)
                total += len(trozo)
                if total > 400_000 or time.monotonic() > fin or b"</head>" in trozo and total > 60_000:
                    break
            return b"".join(partes).decode(r.encoding or "utf-8", "replace"), r.url
    except Exception:  # noqa: BLE001
        return "", url


def video_en_pagina(texto, base):
    for nombre in ("og:video:secure_url", "og:video:url", "og:video", "twitter:player"):
        v = _meta(texto, nombre)
        if v:
            return urljoin(base, v)
    m = re.search(r'<iframe[^>]+src=["\']((?:https?:)?//(?:www\.)?(?:youtube\.com/embed|youtube-nocookie\.com/embed|player\.vimeo\.com/video)/[^"\']+)', texto, re.I)
    if m:
        src = m.group(1)
        src = "https:" + src if src.startswith("//") else src
        yt = re.search(r"embed/([\w-]{6,})", src)
        if yt:
            return f"https://www.youtube.com/watch?v={yt.group(1)}"
        vm = re.search(r"video/(\d+)", src)
        if vm:
            return f"https://vimeo.com/{vm.group(1)}"
        return src
    return ""


def enriquecer(noticias, cfg):
    m = cfg.get("medios", {}) or {}
    con_img = (m.get("miniaturas", {}) or {}).get("activo", True)
    con_vid = (m.get("videos", {}) or {}).get("activo", True)
    seg = float(m.get("limite_segundos", 5))

    for n in noticias:
        if not con_img or not imagen_valida(n.imagen, cfg):
            n.imagen = ""
        if not con_vid:
            n.video = ""

    def trabajo(n):
        if n.google_news or n.youtube:
            return
        if (n.imagen or not con_img) and (n.video or not con_vid):
            return
        texto, final = leer_pagina(n.enlace, seg)
        if not texto:
            return
        if con_img and not n.imagen:
            for nombre in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src"):
                img = _meta(texto, nombre)
                if img and imagen_valida(urljoin(final, img), cfg):
                    n.imagen = urljoin(final, img)
                    break
        if con_vid and not n.video:
            n.video = video_en_pagina(texto, final)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(trabajo, noticias))
