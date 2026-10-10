"""Resultados recientes y tablas de posiciones (Deportes).

Fuente gratuita y sin clave: el marcador público de ESPN (site.api.espn.com), el mismo que usa la Agenda.
Si no responde, la franja simplemente no aparece (no se inventa ningún resultado).
"""
from datetime import datetime, timedelta, timezone

from .utils import http_get

# (clave del subfiltro, ruta ESPN, nombre visible)
LIGAS = [("colombia", "soccer/col.1", "Liga BetPlay"), ("colombia", "soccer/col.copa", "Copa Colombia"),
         ("premier", "soccer/eng.1", "Premier League"), ("laliga", "soccer/esp.1", "LaLiga"),
         ("seriea", "soccer/ita.1", "Serie A"), ("bundesliga", "soccer/ger.1", "Bundesliga"),
         ("ligue1", "soccer/fra.1", "Ligue 1"), ("champions", "soccer/uefa.champions", "Champions League"),
         ("conmebol", "soccer/conmebol.libertadores", "Libertadores"),
         ("conmebol", "soccer/conmebol.sudamericana", "Sudamericana"),
         ("nba", "basketball/nba", "NBA"), ("nba", "basketball/wnba", "WNBA")]
TABLAS = [("colombia", "soccer/col.1", "Liga BetPlay"), ("premier", "soccer/eng.1", "Premier League"),
          ("laliga", "soccer/esp.1", "LaLiga"), ("seriea", "soccer/ita.1", "Serie A"),
          ("bundesliga", "soccer/ger.1", "Bundesliga"), ("ligue1", "soccer/fra.1", "Ligue 1")]


def resultados(tz, log=print, horas=36):
    """Partidos terminados o en juego de las últimas `horas`, más recientes primero."""
    ahora = datetime.now(timezone.utc)
    dias = sorted({(ahora - timedelta(hours=h)).astimezone(tz).date() for h in (0, horas // 2, horas)} |
                  {(ahora - timedelta(hours=h)).date() for h in (0, horas)})
    out, vistos, fallas = [], set(), 0
    for sub, ruta, nombre in LIGAS:
        for d in dias:
            try:
                r = http_get(f"https://site.api.espn.com/apis/site/v2/sports/{ruta}/scoreboard",
                             params={"dates": d.strftime("%Y%m%d")}, timeout=15)
                eventos = r.json().get("events", []) if r.ok else []
            except Exception:  # noqa: BLE001
                fallas += 1
                continue
            for e in eventos:
                if e.get("id") in vistos:
                    continue
                vistos.add(e.get("id"))
                comp = (e.get("competitions") or [{}])[0]
                estado = (comp.get("status") or e.get("status") or {}).get("type", {})
                if estado.get("state") not in ("post", "in"):
                    continue
                inicio = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
                if ahora - inicio > timedelta(hours=horas):
                    continue
                eq = comp.get("competitors", [])
                if len(eq) != 2:
                    continue
                local = next((c for c in eq if c.get("homeAway") == "home"), eq[0])
                visita = next((c for c in eq if c is not local), eq[1])
                out.append({"sub": sub, "liga": nombre, "inicio": inicio.astimezone(tz),
                            "local": local["team"].get("shortDisplayName") or local["team"].get("displayName", ""),
                            "visita": visita["team"].get("shortDisplayName") or visita["team"].get("displayName", ""),
                            "gl": local.get("score", ""), "gv": visita.get("score", ""),
                            "en_juego": estado.get("state") == "in", "detalle": estado.get("shortDetail", ""),
                            "enlace": next((l.get("href") for l in e.get("links", []) if l.get("href")), "")})
    if fallas:
        log(f"Resultados: {fallas} consultas a ESPN fallaron")
    out.sort(key=lambda x: (not x["en_juego"], -x["inicio"].timestamp()))
    return out[:30]


def tablas(log=print, filas=8):
    out = []
    for sub, ruta, nombre in TABLAS:
        try:
            j = http_get(f"https://site.api.espn.com/apis/v2/sports/{ruta}/standings", timeout=20).json()
        except Exception:  # noqa: BLE001
            log(f"Tablas: {nombre} no disponible")
            continue
        grupos = j.get("children") or [j]
        entradas = (grupos[0].get("standings") or {}).get("entries", []) if grupos else []
        tabla = []
        for en in entradas:
            st = {s.get("name"): s.get("displayValue") for s in en.get("stats", [])}
            tabla.append({"pos": int(float(st.get("rank") or 0)) or len(tabla) + 1,
                          "equipo": en.get("team", {}).get("shortDisplayName") or en.get("team", {}).get("displayName", ""),
                          "pj": st.get("gamesPlayed", ""), "pts": st.get("points", "")})
        tabla.sort(key=lambda x: x["pos"])
        if tabla:
            out.append({"sub": sub, "liga": nombre, "titulo": grupos[0].get("name") or nombre, "filas": tabla[:filas]})
    return out
