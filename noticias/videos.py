"""Pestaña Videos: solo YouTube, solo canales aprobados.

- config/video_canales.json: canales por tema (noticias, futbol, nba, historia, ia, anime).
- config/humor_canales.json: canales de Humor (los pone el usuario; nunca se siembran).
- Filtro de palabras (contenido sexual + lista de Humor) sobre título y descripción.
- Los títulos pasan además por la revisión de Gemini en el mismo lote de las destacadas.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from . import filtro_sexual as FS
from . import humor
from .utils import RAIZ, ahora_utc
from .youtube import canal_id, videos_de_canal

ARCHIVO = RAIZ / "config" / "video_canales.json"
CACHE = RAIZ / "data" / "canales_cache.json"
TEMAS = {"noticias": "Noticias", "futbol": "Fútbol", "nba": "NBA", "historia": "Historia", "ia": "IA",
         "anime": "Anime y freestyle", "humor": "Humor"}


def _canales():
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        lista = [c for c in datos.get("canales", []) if c.get("activo", True) and c.get("link")]
    except (OSError, ValueError):
        lista = []
    lista += [{**c, "tema": "humor"} for c in humor.cargar_canales()]
    return lista


def construir(cfg, log=print):
    """Devuelve (videos, errores_por_canal)."""
    vc = cfg.get("videos", {}) or {}
    if not vc.get("activo", True):
        return [], {}
    canales = _canales()
    if not canales:
        return [], {}
    try:
        cache = json.loads(CACHE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    limite = ahora_utc() - timedelta(days=int(vc.get("dias_maximos", 7)))
    por_canal = int(vc.get("maximo_por_canal", 2))
    extra_humor = list((cfg.get("humor", {}) or {}).get("palabras_bloqueadas", []))
    errores = {}

    def leer(c):
        cid = cache.get(c["link"]) or canal_id(c["link"])
        if not cid:
            return c, None, [], "no se encontró el canal"
        try:
            vids, via = videos_de_canal(cid)
            return c, cid, vids, None
        except Exception as ex:  # noqa: BLE001
            return c, cid, [], str(ex)[:60]

    por_tema = {}
    with ThreadPoolExecutor(8) as ex:
        for c, cid, vids, err in ex.map(leer, canales):
            if cid:
                cache[c["link"]] = cid
            if err:
                errores[f"YouTube · {c.get('nombre', c['link'])}"] = err
                continue
            elegidos = 0
            for v in sorted(vids, key=lambda v: v["fecha"] or limite, reverse=True):
                if elegidos >= por_canal or not v["fecha"] or v["fecha"] < limite:
                    continue
                texto = v["titulo"] + " " + v["descripcion"]
                if FS.revisar(cfg, texto) or (c["tema"] == "humor" and extra_humor and FS.coincidencias(texto, extra_humor)):
                    continue                       # falla cerrado
                elegidos += 1
                por_tema.setdefault(c["tema"], []).append({
                    "id": hashlib.md5(v["vid"].encode()).hexdigest()[:10], "vid": v["vid"], "titulo": v["titulo"],
                    "canal": c.get("nombre") or v["canal"], "fecha": v["fecha"], "sub": c["tema"],
                    "tema": TEMAS.get(c["tema"], "Video"), "enlace": f"https://www.youtube.com/watch?v={v['vid']}",
                    "propuesto": "propuesto" in str(c.get("estado", ""))})
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    # mezcla por temas (uno de cada tema por turno) para que haya variedad
    for lista in por_tema.values():
        lista.sort(key=lambda v: v["fecha"], reverse=True)
    mezcla, i = [], 0
    while any(len(l) > i for l in por_tema.values()):
        for t in sorted(por_tema):
            if len(por_tema[t]) > i:
                mezcla.append(por_tema[t][i])
        i += 1
    mezcla = mezcla[: int(vc.get("candidatos", 40))]
    log(f"Videos: {len(mezcla)} candidatos de {len(canales)} canales ({len(errores)} canales sin respuesta)")
    return mezcla, errores
