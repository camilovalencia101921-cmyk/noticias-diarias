"""Agenda de hoy y mañana con fuentes gratuitas y sin clave.

- Fútbol y baloncesto: marcador público de ESPN (site.api.espn.com)
- Estrenos de anime: API pública de AniList
- FMS, Red Bull Batalla y otros: lista "eventos_manuales" de config.yaml
"""
from datetime import date, datetime, time, timedelta

from .utils import http_get, http_post

ESPN = "https://site.api.espn.com/apis/site/v2/sports/{}/scoreboard"
LIGAS = [
    ("liga_betplay", "soccer/col.1", "Liga BetPlay", "futbol", None),
    ("copa_colombia", "soccer/col.copa", "Copa Colombia", "futbol", None),
    ("champions", "soccer/uefa.champions", "Champions League", "futbol", None),
    ("premier", "soccer/eng.1", "Premier League", "futbol", None),
    ("laliga", "soccer/esp.1", "LaLiga", "futbol", None),
    ("seriea", "soccer/ita.1", "Serie A", "futbol", None),
    ("bundesliga", "soccer/ger.1", "Bundesliga", "futbol", None),
    ("ligue1", "soccer/fra.1", "Ligue 1", "futbol", None),
    ("libertadores", "soccer/conmebol.libertadores", "Libertadores", "futbol", None),
    ("sudamericana", "soccer/conmebol.sudamericana", "Sudamericana", "futbol", None),
    ("nba", "basketball/nba", "NBA", "baloncesto", None),
    ("wnba", "basketball/wnba", "WNBA", "baloncesto", None),
    ("seleccion_colombia", "soccer/fifa.friendly", "Selección Colombia", "futbol", "Colombia"),
    ("seleccion_colombia", "soccer/fifa.worldq.conmebol", "Selección Colombia", "futbol", "Colombia"),
    ("seleccion_colombia", "soccer/conmebol.america", "Selección Colombia", "futbol", "Colombia"),
    ("seleccion_colombia", "soccer/fifa.world", "Selección Colombia", "futbol", "Colombia"),
]
ANILIST_Q = """query($a:Int,$b:Int,$p:Int){Page(page:$p,perPage:50){pageInfo{hasNextPage}
airingSchedules(airingAt_greater:$a,airingAt_lesser:$b,sort:TIME){airingAt episode
media{title{romaji english} popularity isAdult siteUrl}}}}"""


def _espn(ruta, dias, tz, filtro_equipo):
    eventos = []
    fechas_utc = {d for d in dias} | {dias[-1] + timedelta(days=1)}
    vistos = set()
    for d in sorted(fechas_utc):
        r = http_get(ESPN.format(ruta), params={"dates": d.strftime("%Y%m%d")}, timeout=15)
        if r.status_code != 200:
            continue
        for e in r.json().get("events", []):
            if e.get("id") in vistos:
                continue
            vistos.add(e.get("id"))
            nombre = e.get("name", "")
            if filtro_equipo and filtro_equipo.lower() not in nombre.lower():
                continue
            inicio = datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(tz)
            if inicio.date() not in dias:
                continue
            enlace = next((l.get("href") for l in e.get("links", []) if l.get("href")), "")
            comp = (e.get("competitions") or [{}])[0]
            equipos = [c.get("team", {}).get("displayName", "") for c in comp.get("competitors", [])]
            texto = " vs. ".join(reversed(equipos)) if len(equipos) == 2 else nombre   # local primero
            eventos.append((inicio, texto, enlace))
    return eventos


def _anime(dias, tz, cfg_anime):
    inicio = int(datetime.combine(dias[0], time.min, tz).timestamp())
    fin = int(datetime.combine(dias[-1], time.max, tz).timestamp())
    out, pagina = [], 1
    while pagina <= 4:
        r = http_post("https://graphql.anilist.co", json={"query": ANILIST_Q,
                      "variables": {"a": inicio, "b": fin, "p": pagina}}, timeout=20)
        r.raise_for_status()
        data = r.json()["data"]["Page"]
        for x in data["airingSchedules"]:
            m = x["media"]
            if m.get("isAdult") or (m.get("popularity") or 0) < cfg_anime.get("popularidad_minima", 20000):
                continue
            titulo = m["title"].get("english") or m["title"].get("romaji")
            out.append((m.get("popularity", 0), datetime.fromtimestamp(x["airingAt"], tz),
                        f"{titulo} · episodio {x['episode']}", m.get("siteUrl", "")))
        if not data["pageInfo"]["hasNextPage"]:
            break
        pagina += 1
    out.sort(key=lambda t: -t[0])
    return [(t, txt, url) for _, t, txt, url in out[: int(cfg_anime.get("maximo", 6))]]


def construir(cfg, hoy, tz, log=print, estrenos=None):
    """Devuelve lista de dicts {dia, hora, categoria, tema, sub, texto, enlace} ordenada por hora de Colombia."""
    a = (cfg.get("mejoras", {}) or {}).get("agenda", {}) or {}
    if not a.get("activo", True):
        return []
    dias = [hoy, hoy + timedelta(days=1)]
    items = []
    for clave, ruta, nombre, tema, equipo in LIGAS:
        if not a.get(clave, True):
            continue
        try:
            for inicio, texto, enlace in _espn(ruta, dias, tz, equipo):
                items.append({"fecha": inicio, "categoria": nombre, "tema": tema, "texto": texto, "enlace": enlace,
                              "sub": "nba" if tema == "baloncesto" else "futbol"})
        except Exception as ex:  # noqa: BLE001
            log(f"Agenda: {nombre} no disponible ({type(ex).__name__})")
    ca = a.get("anime", {}) or {}
    if ca.get("activo", True):
        try:
            for inicio, texto, enlace in _anime(dias, tz, ca):
                items.append({"fecha": inicio, "categoria": "Estreno anime", "tema": "anime", "texto": texto, "enlace": enlace,
                              "sub": "estrenos"})
        except Exception as ex:  # noqa: BLE001
            log(f"Agenda: AniList no disponible ({type(ex).__name__})")
    for ev in a.get("eventos_manuales", []) or []:
        try:
            f = date.fromisoformat(str(ev.get("fecha")))
        except ValueError:
            continue
        if f in dias:
            items.append({"fecha": datetime.combine(f, time(0, 0), tz), "categoria": ev.get("categoria", "Evento"),
                          "tema": "freestyle" if "freestyle" in str(ev.get("categoria", "")).lower() else "general",
                          "texto": ev.get("nombre", ""), "enlace": ev.get("enlace", ""), "sin_hora": True, "sub": "eventos"})
    for p in estrenos or []:                     # estrenos de cine de hoy y mañana (Cinemark)
        if p.get("fecha") in dias:
            items.append({"fecha": datetime.combine(p["fecha"], time(0, 0), tz), "categoria": "Estreno de cine",
                          "tema": "cine", "texto": f'{p["titulo"]} ({p["genero"]})', "enlace": p.get("enlace", ""),
                          "sin_hora": True, "sub": "estrenos"})
    items.sort(key=lambda x: x["fecha"])
    for it in items:
        it["dia"] = "Hoy" if it["fecha"].date() == hoy else "Mañana"
        it["hora"] = "" if it.get("sin_hora") else it["fecha"].strftime("%H:%M")
    return items
