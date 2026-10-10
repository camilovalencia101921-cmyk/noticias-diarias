"""Filtros sin IA: publicidad, sensacionalismo, palabras prohibidas y duplicados."""
import re

from .utils import contar_palabras, contiene_frase, encontrar_palabras, jaccard, normalizar

PREGUNTAS = ("por que", "sabias", "sabes", "que pasa", "que paso", "que hay detras", "quien es",
             "realmente", "de verdad", "es posible", "sera", "estas", "conoces", "como es posible",
             "cual es el secreto", "que significa")


def revisar_publicidad(n, cfg):
    """Devuelve 'descartar', 'duda' o None."""
    fp = cfg.get("filtro_publicidad", {}) or {}
    if not fp.get("activo", True):
        return None
    texto = normalizar(" ".join([n.titulo, " ".join(n.etiquetas), n.enlace.replace("-", " ").replace("/", " ")]))
    if encontrar_palabras(texto, fp.get("frases", [])):
        return "descartar"
    if encontrar_palabras(normalizar(n.titulo + " " + n.descripcion[:300]), fp.get("frases_duda", [])):
        return "duda"
    return None


def sensacionalismo(titulo, modo, cfg):
    """Devuelve (penalización, [señales]). modo: estricto | flexible."""
    fs = cfg.get("filtro_sensacionalismo", {}) or {}
    if not fs.get("activo", True):
        return 0, []
    pen = fs.get("penalizaciones", {}) or {}
    t = normalizar(titulo)
    señales, total = [], 0

    if contiene_frase(titulo, fs.get("frases_gancho", [])):
        total += pen.get("frase_gancho", 3)
        señales.append("frase de gancho")
    if modo == "flexible":
        return total, señales

    crudo = titulo.strip()
    if crudo.endswith("?") or crudo.startswith("¿"):
        pregunta = normalizar(crudo.split("¿")[-1])
        if any(pregunta.startswith(p) for p in PREGUNTAS) or crudo.startswith("¿"):
            total += pen.get("pregunta_retorica", 2)
            señales.append("pregunta retórica")
    siglas = {s.upper().replace(".", "") for s in fs.get("siglas_permitidas", [])}
    palabras = re.findall(r"[A-Za-zÁÉÍÓÚÑÜáéíóúñü]{3,}", crudo)
    racha = maxr = 0
    for w in palabras:
        if w.isupper() and w.upper() not in siglas:
            racha += 1
            maxr = max(maxr, racha)
        else:
            racha = 0
    if maxr >= 3:
        total += pen.get("mayusculas_sostenidas", 2)
        señales.append("mayúsculas sostenidas")
    if crudo.count("!") >= 2 or "¡¡" in crudo:
        total += pen.get("exceso_exclamaciones", 2)
        señales.append("exceso de !")
    sup = encontrar_palabras(t, fs.get("superlativos", []))
    if sup:
        total += pen.get("superlativo", 1) * len(sup)
        señales.append("superlativos: " + ", ".join(sup))
    if any((t + " ").startswith(normalizar(p) + " ") for p in fs.get("inicios_sin_sujeto", [])):
        total += pen.get("sin_sujeto", 2)
        señales.append("titular sin sujeto")
    return total, señales


def palabras_descartadas(n, cfg):
    lista = (cfg.get("seleccion", {}) or {}).get("palabras_descartar", [])
    return encontrar_palabras(normalizar(n.titulo), lista)


def agrupar_duplicados(noticias, umbral=0.55):
    """Agrupa por similitud de título. Devuelve (representantes, n_duplicados)."""
    def calidad(n):
        return (n.aprobado, n.oficial, n.alcance == "local", bool(n.imagen), len(n.descripcion), not n.google_news)

    grupos = []           # [(tokens_union, [noticias])]
    for n in noticias:
        tk = n.tokens
        if not tk:
            continue
        mejor = None
        for g in grupos:
            if jaccard(tk, g[0]) >= umbral or (len(tk) >= 4 and len(tk & g[0]) >= max(4, int(0.8 * len(tk)))):
                mejor = g
                break
        if mejor:
            mejor[1].append(n)
        else:
            grupos.append((tk, [n]))
    reps, dups = [], 0
    for _, lista in grupos:
        lista.sort(key=calidad, reverse=True)
        r = lista[0]
        r.fuentes_cluster = {x.fuente for x in lista}
        vistos_f, r.cluster = set(), []
        for x in lista:                 # "N medios cubren esto": un enlace por medio
            if x.fuente not in vistos_f:
                vistos_f.add(x.fuente)
                r.cluster.append((x.fuente, x.enlace))
        r.cluster = r.cluster[:8]
        if not r.imagen:
            r.imagen = next((x.imagen for x in lista if x.imagen), "")
        if not r.descripcion:
            r.descripcion = next((x.descripcion for x in lista if x.descripcion), "")
        r.oficial = any(x.oficial for x in lista)
        if any(x.alcance == "local" for x in lista):
            r.zona_prioridad = min([x.zona_prioridad for x in lista if x.zona_prioridad] or [0])
        dups += len(lista) - 1
        reps.append(r)
    return reps, dups


def contiene(n, palabras):
    return contar_palabras(normalizar(n.titulo + " " + n.descripcion), palabras) > 0
