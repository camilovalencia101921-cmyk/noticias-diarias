"""Capa 2 del filtro de contenido sexual: lista de palabras (español e inglés).

Normaliza el texto antes de comparar:
  - minúsculas y sin tildes
  - "leet" dentro de palabras: p0rn0 -> porno, s3xy -> sexy, @ -> a, $ -> s
  - letras separadas: "p o r n o", "p.o.r.n.o", "s-e-x-y" -> porno / sexy
  - letras repetidas: "pooorno", "sexxxy" -> porno / sexy (se compara también una versión sin repeticiones)

Sintaxis de la lista (config.yaml, filtro_sexual):
  "porn*"  -> cualquier palabra que EMPIECE así (porno, pornografía, pornhub…)
  "sexy"   -> solo la palabra completa (no bloquea "sexto" ni "Essex")
  "video de sexo" -> frase completa
Falla cerrado: si el texto no se puede revisar, se considera bloqueado.
"""
import re
import unicodedata
from functools import lru_cache

LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i"})


def _sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


def normalizar(texto):
    t = _sin_tildes((texto or "").lower())
    # leet solo en "palabras" que mezclan letras con números/símbolos (no toca años como 2026)
    def leet(m):
        w = m.group(0)
        return w.translate(LEET) if re.search(r"[a-z]", w) and re.search(r"[0-9@$!]", w) else w
    t = re.sub(r"[a-z0-9@$!]+", leet, t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    # une letras sueltas consecutivas (3 o más): "p o r n o" -> "porno"
    t = re.sub(r"\b(?:[a-z] ){2,}[a-z]\b", lambda m: m.group(0).replace(" ", ""), t)
    return re.sub(r"\s+", " ", t).strip()


def sin_repeticiones(t):
    return re.sub(r"([a-z])\1+", r"\1", t)


@lru_cache(maxsize=2048)
def _patron(termino):
    prefijo = termino.endswith("*")
    base = normalizar(termino.rstrip("*"))
    if not base:
        return None, None
    fin = "" if prefijo else r"\b"
    p1 = re.compile(r"\b" + re.escape(base) + fin)
    b2 = sin_repeticiones(base)
    # la versión sin letras repetidas solo para términos que siguen siendo largos ("xxx" -> "x" no sirve)
    p2 = re.compile(r"\b" + re.escape(b2) + fin) if (b2 != base and len(b2) >= 4) else p1
    return p1, p2


def coincidencias(texto, terminos):
    try:
        n = normalizar(texto)
        n2 = sin_repeticiones(n)
        out = []
        for term in terminos or []:
            p1, p2 = _patron(str(term))
            if p1 and (p1.search(n) or p2.search(n2)):
                out.append(str(term))
        return out
    except Exception:  # noqa: BLE001  (falla cerrado)
        return ["error al revisar"]


def terminos(cfg):
    fs = cfg.get("filtro_sexual", {}) or {}
    lista = list(fs.get("palabras_es", [])) + list(fs.get("palabras_en", []))
    if fs.get("ocultar_delitos_sexuales", False):
        lista += list(fs.get("delitos_sexuales", []))
    return lista


def revisar(cfg, *textos):
    """Devuelve la lista de términos encontrados (vacía = pasa el filtro)."""
    return coincidencias(" | ".join(t or "" for t in textos), terminos(cfg))
