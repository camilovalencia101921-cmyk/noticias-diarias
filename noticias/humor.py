"""Pestaña Humor: videos de YouTube SOLO de canales aprobados (config/humor_canales.json).

- Acepta links de canal (https://www.youtube.com/@usuario, /channel/UC…, /c/…) y los
  convierte a su RSS de YouTube. El ID resuelto se guarda en data/humor_cache.json.
- Máximo 10 videos por día; sin reproductor ni miniaturas externas (bloque de color con ▶).
- Filtro de palabras (contenido sexual + lista propia) sobre título y descripción.
"""
import json
import re
from datetime import timedelta

from . import filtro_sexual as FS
from .fuentes import leer_rss
from .utils import RAIZ, ahora_utc, http_get

ARCHIVO = RAIZ / "config" / "humor_canales.json"
CACHE = RAIZ / "data" / "humor_cache.json"
CATEGORIAS = {"virales", "animales", "standup", "fails"}
PISTAS = [("animales", re.compile(r"\b(perr|gat|animal|mascota|dog|cat|pet|loro|mono)", re.I)),
          ("standup", re.compile(r"(stand ?up|mon[oó]logo|comedia en vivo|comedian|comediante)", re.I)),
          ("fails", re.compile(r"\b(fail|ca[ií]da|tropez|fallo|oops|epic fail)", re.I))]


def cargar_canales():
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        return [c for c in datos.get("canales", []) if isinstance(c, dict) and c.get("link") and c.get("activo", True)]
    except (OSError, ValueError):
        return []


def resolver_feed(link, cache):
    if "feeds/videos.xml" in link:
        return link
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", link)
    cid = m.group(1) if m else cache.get(link)
    if not cid:
        try:
            r = http_get(link, timeout=15, cookies={"CONSENT": "YES+1"})
            m = re.search(r'"externalId":"(UC[\w-]{22})"', r.text) or re.search(r"channel_id=(UC[\w-]{22})", r.text)
            cid = m.group(1) if m else None
        except Exception:  # noqa: BLE001
            cid = None
        if cid:
            cache[link] = cid
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}" if cid else None


def construir(cfg, log=print):
    """Devuelve (videos, mensaje). videos: lista de dicts para la página."""
    hc = cfg.get("humor", {}) or {}
    canales = cargar_canales()
    if not canales:
        return [], "Agrega canales aprobados en config/humor_canales.json"
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    limite = ahora_utc() - timedelta(hours=int(hc.get("horas_maximas", 72)))
    extra = list(hc.get("palabras_bloqueadas", []))
    videos, errores = [], []
    for c in canales:
        feed = resolver_feed(c["link"], cache)
        if not feed:
            errores.append(c.get("nombre") or c["link"])
            continue
        try:
            r = http_get(feed, timeout=15)
            items = leer_rss({"nombre": c.get("nombre") or "YouTube", "url": feed, "alcance": "internacional"}, r.content)
        except Exception:  # noqa: BLE001
            errores.append(c.get("nombre") or c["link"])
            continue
        for n in items:
            if n.fecha and n.fecha < limite:
                continue
            texto = n.titulo + " " + n.descripcion
            if FS.revisar(cfg, texto) or (extra and FS.coincidencias(texto, extra)):   # falla cerrado
                continue
            cat = c.get("categoria") if c.get("categoria") in CATEGORIAS else \
                next((k for k, rx in PISTAS if rx.search(texto)), "virales")
            videos.append({"titulo": n.titulo, "canal": n.fuente, "enlace": n.enlace, "fecha": n.fecha,
                           "sub": cat, "id": n.id})
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    if errores:
        log(f"Humor: no se pudieron leer {len(errores)} canales ({', '.join(errores[:5])})")
    videos.sort(key=lambda v: v["fecha"] or ahora_utc(), reverse=True)
    videos = videos[: int(hc.get("maximo_por_dia", 10))]
    log(f"Humor: {len(videos)} videos de {len(canales)} canales aprobados")
    return videos, "" if videos else "Hoy no hay videos nuevos de tus canales aprobados."
