"""Medios aprobados (config/medios_aprobados.json): capa 1 del filtro.

- "Ver más" y las imágenes solo muestran noticias de estos medios.
- Si un medio tiene "rss", se lee directamente; si no, sus noticias llegan por las
  búsquedas de Google News (se reconoce por su dominio).
"""
import json

from .utils import RAIZ, dominio

ARCHIVO = RAIZ / "config" / "medios_aprobados.json"


def cargar():
    try:
        return json.loads(ARCHIVO.read_text(encoding="utf-8")).get("medios", [])
    except (OSError, ValueError):
        return []


def dominios(medios=None):
    return {m["dominio"].lower().removeprefix("www.") for m in (medios or cargar()) if m.get("dominio")}


def es_aprobado(dom, aprobados):
    d = (dom or "").lower().removeprefix("www.")
    return bool(d) and any(d == a or d.endswith("." + a) for a in aprobados)


def fuentes_rss(medios, ya):
    """Feeds de medios aprobados que no estén ya en config.yaml."""
    ya = {u.rstrip("/") for u in ya}
    out = []
    for m in medios:
        rss = m.get("rss")
        if rss and m.get("activo", True) and rss.rstrip("/") not in ya:
            alc = m.get("alcance", "nacional")
            out.append({"nombre": m["nombre"], "url": rss, "alcance": alc, "aprobada": True,
                        "filtro": "flexible" if alc == "local" else "estricto", "tipo": m.get("tipo", "rss")})
    return out


def dominio_de_link(link):
    return dominio(link)
