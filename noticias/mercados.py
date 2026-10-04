"""Tablero de mercados con fuentes gratuitas y sin clave.

- Dólar (TRM): datos abiertos de la Superintendencia Financiera en datos.gov.co
- Brent, Colcap (ETF iColcap) y S&P 500: gráfico diario público de Yahoo Finance
El historial se guarda en SQLite; si una fuente falla se usa lo guardado.
"""
from datetime import datetime, timezone

from .utils import http_get

TRM_URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"


def _trm():
    r = http_get(TRM_URL, params={"$order": "vigenciadesde DESC", "$limit": 45}, timeout=20)
    r.raise_for_status()
    return [(x["vigenciadesde"][:10], float(x["valor"])) for x in r.json()]


def _yahoo(simbolo):
    r = http_get(YAHOO_URL.format(simbolo), params={"range": "3mo", "interval": "1d"}, timeout=20)
    r.raise_for_status()
    res = r.json()["chart"]["result"][0]
    cierres = res["indicators"]["quote"][0]["close"]
    out = []
    for t, v in zip(res["timestamp"], cierres):
        if v is not None:
            out.append((datetime.fromtimestamp(t, tz=timezone.utc).date().isoformat(), round(float(v), 2)))
    return out


def actualizar(cfg, historial, log=print):
    """Devuelve lista de tarjetas: {nombre, valor, cambio, pct, serie, fecha, unidad}."""
    m = (cfg.get("mejoras", {}) or {}).get("mercados", {}) or {}
    if not m.get("activo", True):
        return []
    tarjetas = []
    defs = [("dolar", _trm, "COP"), ("brent", None, "USD"), ("colcap", None, "COP"), ("sp500", None, "pts")]
    for clave, fn, unidad in defs:
        c = m.get(clave, {}) or {}
        if not c.get("activo", False):
            continue
        try:
            puntos = fn() if fn else _yahoo(c.get("simbolo"))
            historial.guardar_serie(clave, puntos)
        except Exception as ex:  # noqa: BLE001
            log(f"Mercados: {clave} no disponible ({type(ex).__name__}); se usa el historial guardado")
        serie = historial.serie(clave, 30)
        if not serie:
            continue
        valor = serie[-1][1]
        previo = serie[-2][1] if len(serie) > 1 else valor
        cambio = valor - previo
        tarjetas.append({
            "clave": clave, "nombre": c.get("nombre", clave), "valor": valor, "cambio": cambio,
            "pct": (cambio / previo * 100) if previo else 0, "serie": [v for _, v in serie],
            "fecha": serie[-1][0], "unidad": unidad,
        })
    return tarjetas


def sparkline(valores, ancho=120, alto=36):
    if len(valores) < 2:
        return ""
    lo, hi = min(valores), max(valores)
    rango = (hi - lo) or 1
    paso = ancho / (len(valores) - 1)
    pts = " ".join(f"{i * paso:.1f},{alto - 3 - (v - lo) / rango * (alto - 6):.1f}" for i, v in enumerate(valores))
    return (f'<svg class="spark" viewBox="0 0 {ancho} {alto}" preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline points="{pts}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/></svg>')
