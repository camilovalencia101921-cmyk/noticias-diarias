"""Sección "Cine": estrenos de películas en Colombia (de la semana y próximos).

Orden de fuentes (nunca se inventan películas ni fechas):
 1. Gemini con la búsqueda de Google integrada: UNA llamada al día, solo con modelos
    cuyo nivel gratuito incluye esa herramienta. Solo se aceptan respuestas que traen
    metadatos de búsqueda (es decir, que de verdad consultaron la web).
 2. Datos públicos de la página de Cinemark Colombia (fuente web gratuita y real).
 3. Si nada es confiable: lista vacía -> "Sin estrenos confirmados hoy".
"""
import json
import re
from datetime import date, timedelta

from .gemini import GeminiError, _parsear_json, buscar_con_google
from .utils import dominio, http_get, normalizar

CINEMARK = "https://www.cinemark.com.co/"
EXCLUIR_TITULO = re.compile(r"\b(concierto|concert|live|tour|world tour|en vivo)\b", re.I)


def ventana(hoy, dias):
    lunes = hoy - timedelta(days=hoy.weekday())
    return lunes, hoy + timedelta(days=dias)


def _linea(texto, maximo=130):
    t = re.sub(r"\s+", " ", texto or "").strip()
    t = re.split(r"(?<=[.!?])\s", t)[0]
    return t if len(t) <= maximo else t[:maximo].rsplit(" ", 1)[0] + "…"


def _limpiar(pelis, hoy, cc):
    desde, hasta = ventana(hoy, int(cc.get("dias_hacia_adelante", 30)))
    excluir = {normalizar(g) for g in cc.get("excluir_generos", [])}
    vistos, out = set(), []
    for p in pelis:
        try:
            f = date.fromisoformat(str(p.get("fecha", ""))[:10])
        except ValueError:
            continue
        titulo = str(p.get("titulo", "")).strip()
        genero = str(p.get("genero", "")).strip()
        clave = normalizar(re.sub(r"\((?:dob|sub)[^)]*\)|\b(2d|3d|imax|4dx|xd)\b", "", titulo, flags=re.I))
        if (not titulo or not (desde <= f <= hasta) or clave in vistos or EXCLUIR_TITULO.search(titulo)
                or any(e and e in normalizar(genero) for e in excluir)):
            continue
        vistos.add(clave)
        out.append({"titulo": titulo, "genero": genero or "—", "sinopsis": _linea(p.get("sinopsis", "")),
                    "fecha": f, "enlace": p.get("enlace", ""), "fuente": p.get("fuente", ""),
                    "semana": f <= desde + timedelta(days=6)})
    out.sort(key=lambda p: (p["fecha"], p["titulo"]))
    return out[: int(cc.get("maximo", 10))]


# ------------------------------------------------------------ 1. Gemini + Google
def _con_gemini(ia, hoy, cc, log):
    desde, hasta = ventana(hoy, int(cc.get("dias_hacia_adelante", 30)))
    prompt = f"""Busca en la web los estrenos de PELÍCULAS en salas de cine de COLOMBIA con fecha de estreno
entre el {desde.isoformat()} y el {hasta.isoformat()} (hoy es {hoy.isoformat()}).
Usa solo información encontrada en la búsqueda (carteleras de Cine Colombia, Cinemark, Procinal, Cinépolis,
Royal Films o medios colombianos). Excluye conciertos, música y eventos que no sean películas.
No inventes nada: si no encuentras la fecha de estreno en Colombia, no incluyas la película.
Responde SOLO un JSON (lista) con objetos: {{"titulo": "...", "genero": "...", "sinopsis": "una línea",
"fecha": "AAAA-MM-DD", "fuente_url": "dirección de la página donde está el dato"}}."""
    texto, meta, modelo = buscar_con_google(ia, prompt, cc.get("modelos_busqueda_gratuita") or [])
    fuentes = [c.get("web", {}) for c in meta.get("groundingChunks", []) if c.get("web")]
    if not fuentes:
        raise GeminiError(f"{modelo}: la respuesta no trae resultados de búsqueda; no se usa")
    dominios = {(f.get("title") or "").lower() for f in fuentes} | {dominio(f.get("uri", "")) for f in fuentes}
    dominios = {x for x in dominios if x and "vertexaisearch" not in x and "google" not in x}
    datos = _parsear_json(texto)
    pelis = []
    for p in datos if isinstance(datos, list) else []:
        if not isinstance(p, dict):
            continue
        url = str(p.get("fuente_url", ""))
        d = dominio(url)
        # el enlace solo se muestra si su sitio aparece entre las fuentes reales de la búsqueda
        enlace = url if url.startswith("http") and d and any(d in x or x.endswith(d) for x in dominios if x) else ""
        pelis.append({**p, "enlace": enlace, "fuente": d if enlace else "Búsqueda de Google"})
    log(f"Cine: {len(pelis)} estrenos con búsqueda de Google ({modelo}, {len(fuentes)} fuentes)")
    return pelis


# ------------------------------------------------------------ 2. Cinemark
def _con_cinemark(log):
    r = http_get(CINEMARK, timeout=20)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        raise ValueError("la página cambió de formato")
    props = json.loads(m.group(1))["props"]["pageProps"]
    pelis = []
    for k in ("PremieresBillboard", "UpcomingReleases", "Presales"):
        for x in props.get(k) or []:
            pelis.append({"titulo": (x.get("TitleAlt") or x.get("Title") or "").strip().title(),
                          "genero": x.get("GenreName", ""), "sinopsis": x.get("Synopsis", ""),
                          "fecha": (x.get("OpeningDate") or "")[:10], "enlace": CINEMARK,
                          "fuente": "Cinemark Colombia"})
    log(f"Cine: {len(pelis)} películas leídas de Cinemark Colombia")
    return pelis


def construir(cfg, ia, hoy, log=print):
    """Devuelve (lista_de_estrenos, origen)."""
    cc = cfg.get("cine", {}) or {}
    if not cc.get("activo", True):
        return None, "apagado"
    if cc.get("busqueda_gemini", True) and ia.activo and cc.get("modelos_busqueda_gratuita"):
        try:
            pelis = _limpiar(_con_gemini(ia, hoy, cc, log), hoy, cc)
            if pelis:
                return pelis, "Búsqueda de Google (Gemini)"
            log("Cine: la búsqueda no dio estrenos confirmados en la fecha")
        except (GeminiError, ValueError) as ex:
            log(f"Cine: búsqueda de Google no disponible ({str(ex)[:200]})")
    if cc.get("respaldo_cinemark", True):
        try:
            pelis = _limpiar(_con_cinemark(log), hoy, cc)
            if pelis:
                return pelis, "Cinemark Colombia"
        except Exception as ex:  # noqa: BLE001
            log(f"Cine: Cinemark no disponible ({type(ex).__name__})")
    return [], ""
