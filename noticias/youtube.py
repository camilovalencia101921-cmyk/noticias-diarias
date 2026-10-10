"""Lectura gratuita de canales de YouTube (sin clave de API).

1. RSS oficial del canal (youtube.com/feeds/videos.xml?channel_id=…)
2. Si el RSS falla (YouTube lo tiene caído a ratos), se lee la página pública del canal
   (/videos) y se toman título, identificador y fecha aproximada ("hace 3 días").
"""
import json
import re
from calendar import timegm
from datetime import datetime, timedelta, timezone

import feedparser

from .utils import ahora_utc, http_get, limpiar_html

UA_NAV = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
          "Accept-Language": "es-CO,es;q=0.9"}
UNIDADES = {"segundo": 1 / 3600, "second": 1 / 3600, "minuto": 1 / 60, "minute": 1 / 60, "hora": 1, "hour": 1,
            "dia": 24, "día": 24, "day": 24, "semana": 168, "week": 168, "mes": 720, "month": 720, "año": 8760, "year": 8760}


def canal_id(link):
    """Devuelve el ID UC… de un link de canal (@usuario, /channel/UC…, /c/…)."""
    m = re.search(r"(UC[\w-]{22})", link)
    if m:
        return m.group(1)
    try:
        r = http_get(link, timeout=15, headers=UA_NAV, cookies={"CONSENT": "YES+1"})
        m = re.search(r'"externalId":"(UC[\w-]{22})"', r.text) or re.search(r'"channelId":"(UC[\w-]{22})"', r.text)
        return m.group(1) if m else None
    except Exception:  # noqa: BLE001
        return None


def _hace(texto):
    t = (texto or "").lower()
    m = re.search(r"(\d+)\s*(segundo|second|minuto|minute|hora|hour|día|dia|day|semana|week|mes|month|año|year)", t)
    if not m:
        return None
    return ahora_utc() - timedelta(hours=int(m.group(1)) * UNIDADES[m.group(2)])


def por_rss(cid):
    r = http_get(f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}", timeout=15)
    if r.status_code != 200:
        raise ValueError(f"RSS HTTP {r.status_code}")
    f = feedparser.parse(r.content)
    nombre = f.feed.get("title", "")
    out = []
    for e in f.entries:
        vid = e.get("yt_videoid")
        if not vid:
            continue
        t = e.get("published_parsed")
        out.append({"vid": vid, "titulo": limpiar_html(e.get("title", "")), "canal": nombre,
                    "descripcion": limpiar_html(e.get("summary", ""))[:400],
                    "fecha": datetime.fromtimestamp(timegm(t), tz=timezone.utc) if t else None,
                    "short": "/shorts/" in e.get("link", "")})
    return out, "rss"


def por_pagina(cid):
    r = http_get(f"https://www.youtube.com/channel/{cid}/videos", timeout=20, headers=UA_NAV, cookies={"CONSENT": "YES+1"})
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", r.text, re.S)
    if r.status_code != 200 or not m:
        raise ValueError(f"página HTTP {r.status_code}")
    data = json.loads(m.group(1))
    nombre = (data.get("metadata", {}).get("channelMetadataRenderer", {}) or {}).get("title", "")
    out = []

    def recorrer(o):
        if isinstance(o, dict):
            lk = o.get("lockupViewModel")
            if lk and lk.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
                md = lk.get("metadata", {}).get("lockupMetadataViewModel", {})
                partes = [x for fila in md.get("metadata", {}).get("contentMetadataViewModel", {}).get("metadataRows", [])
                          for p in fila.get("metadataParts", [])
                          for x in (p.get("accessibilityLabel", ""), p.get("text", {}).get("content", ""))]
                out.append({"vid": lk.get("contentId"), "titulo": md.get("title", {}).get("content", ""), "canal": nombre,
                            "descripcion": "", "fecha": next((f for f in map(_hace, partes) if f), None), "short": False})
            vr = o.get("videoRenderer")
            if vr and vr.get("videoId"):
                out.append({"vid": vr["videoId"], "titulo": "".join(x.get("text", "") for x in vr.get("title", {}).get("runs", [])),
                            "canal": nombre, "descripcion": "", "fecha": _hace(vr.get("publishedTimeText", {}).get("simpleText")),
                            "short": False})
            for v in o.values():
                recorrer(v)
        elif isinstance(o, list):
            for v in o:
                recorrer(v)
    recorrer(data)
    return [v for v in out if v["vid"] and v["titulo"]], "pagina"


def videos_de_canal(cid):
    """Devuelve (videos, via) o lanza ValueError si ninguna vía funciona."""
    try:
        v, via = por_rss(cid)
        if v:
            return v, via
    except Exception:  # noqa: BLE001
        pass
    return por_pagina(cid)
