"""Funciones de apoyo: texto, fechas, red y configuración."""
import html
import re
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from ruamel.yaml import YAML

RAIZ = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; noticias-diarias/1.0; +https://github.com)"
UA_NAVEGADOR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

_sesion = requests.Session()
_sesion.headers.update({"User-Agent": UA, "Accept-Language": "es-CO,es;q=0.9,en;q=0.6"})


def http_get(url, timeout=15, **kw):
    """GET con un segundo intento usando otro agente si el sitio lo rechaza."""
    r = _sesion.get(url, timeout=timeout, **kw)
    if r.status_code in (202, 403, 406, 429) or (r.status_code == 200 and not r.content):
        r2 = _sesion.get(url, timeout=timeout, headers={"User-Agent": UA_NAVEGADOR}, **kw)
        if r2.status_code == 200:
            return r2
    return r


def http_post(url, timeout=30, **kw):
    return _sesion.post(url, timeout=timeout, **kw)


def cargar_config(ruta=None):
    ruta = Path(ruta or RAIZ / "config.yaml")
    with open(ruta, encoding="utf-8") as f:
        return YAML(typ="safe").load(f)


def zona(cfg):
    return ZoneInfo(cfg.get("pagina", {}).get("zona_horaria", "America/Bogota"))


def ahora_utc():
    return datetime.now(timezone.utc)


# ------------------------------------------------------------------ texto
STOPWORDS = set("""a al ante bajo con contra de del desde durante e el en entre esta este esto estos
hacia hasta la las le les lo los mas más no o para pero por que qué se sin sobre su sus tras un una unos
unas y ya es son fue ser ha han hay como cómo tras sus the of to and in on for at with from by is are
was were be its his her their this that""".split())


def sin_tildes(texto):
    t = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in t if not unicodedata.combining(c))


def normalizar(texto):
    t = sin_tildes((texto or "").lower())
    t = re.sub(r"[^a-z0-9&ñ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def tokens(texto):
    return {w for w in normalizar(texto).split() if len(w) > 2 and w not in STOPWORDS}


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def limpiar_html(texto):
    if not texto:
        return ""
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", texto)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=4096)
def _patron(palabra):
    p = normalizar(palabra)
    if not p:
        return None
    # palabras cortas: palabra completa; largas: también cuenta como prefijo
    fin = r"\b" if (len(p) < 6 or " " in p) else ""
    return re.compile(r"\b" + re.escape(p) + fin)


def contar_palabras(texto_normalizado, palabras):
    n = 0
    for w in palabras or []:
        pat = _patron(str(w))
        if pat and pat.search(texto_normalizado):
            n += 1
    return n


def encontrar_palabras(texto_normalizado, palabras):
    return [w for w in (palabras or []) if (p := _patron(str(w))) and p.search(texto_normalizado)]


def contiene_frase(texto, frases):
    """Busca frases literales (respeta signos como ':'), sin tildes ni mayúsculas."""
    t = sin_tildes((texto or "").lower())
    return [f for f in (frases or []) if sin_tildes(str(f).lower()) in t]


def primeras_lineas(texto, max_frases=2, max_chars=240):
    t = limpiar_html(texto)
    if not t:
        return ""
    frases = re.split(r"(?<=[.!?])\s+", t)
    r = " ".join(frases[:max_frases])
    if len(r) > max_chars:
        r = r[:max_chars].rsplit(" ", 1)[0] + "…"
    return r


def dominio(url):
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith("www.") else d
    except Exception:
        return ""


def es_dominio_oficial(url):
    d = dominio(url)
    return d.endswith(".gov.co") or d.endswith(".gov") or d.endswith(".int") or ".gob." in d
