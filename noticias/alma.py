"""Sección "Para el alma": 3 temas de espiritualidad al día, escritos por Gemini.

- Sin modo de respaldo por reglas: si Gemini falla, la sección se omite ese día.
- No se repiten temas: temas-publicados.json guarda los últimos N títulos y se
  le pasan a Gemini para que elija temas distintos.
"""
import json
from datetime import date

from .gemini import GeminiError
from .utils import RAIZ, normalizar

ARCHIVO = RAIZ / "temas-publicados.json"
HOY = RAIZ / "data" / "alma-hoy.json"      # temas completos del día (se reutilizan en las demás actualizaciones)


def cargar_historial():
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
        return [d for d in datos if isinstance(d, dict) and d.get("titulo")]
    except (OSError, ValueError):
        return []


def guardar_historial(lista, maximo):
    lista = sorted(lista, key=lambda d: d.get("fecha", ""))[-maximo:]
    ARCHIVO.write_text(json.dumps(lista, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def categorias_del_dia(cfg_alma, historial, hoy):
    """Elige las tradiciones de hoy: cristianismo según su frecuencia y el resto por rotación
    (la que lleva más tiempo sin salir va primero)."""
    cats = cfg_alma.get("categorias") or []
    n = int(cfg_alma.get("temas_por_dia", 3))
    ultima = {}
    for d in historial:
        ultima[d.get("categoria")] = max(ultima.get(d.get("categoria"), ""), d.get("fecha", ""))
    elegidas = []
    for c in cats:
        f = int(c.get("frecuencia", 1))
        if f >= 2 and hoy.toordinal() % 3 < f:      # aparece f de cada 3 días
            elegidas.append(c)
    resto = sorted((c for c in cats if c not in elegidas), key=lambda c: (ultima.get(c["clave"], ""), c["clave"]))
    for c in resto:
        if len(elegidas) >= n:
            break
        elegidas.append(c)
    return elegidas[:n]


def prompt(categorias, anteriores):
    lista = "\n".join(f'- {c["clave"]}: {c["nombre"]}' for c in categorias)
    previos = "\n".join(f"- {t}" for t in anteriores[-120:]) or "- (ninguno)"
    return f"""Eres un divulgador serio de historia de las religiones y de la filosofía. Escribe en español
{len(categorias)} temas para leer con calma, uno por cada tradición de esta lista (usa la clave exacta):
{lista}

Cada tema debe ser concreto (una práctica, una idea, una figura histórica, un texto, un símbolo, un lugar o un ritual),
y DISTINTO de todos estos temas ya publicados (no repitas ni hagas variaciones cercanas):
{previos}

Reglas:
- Tono informativo y respetuoso: explica lo que cada tradición enseña o practica ("según el budismo…", "para los estoicos…").
  No afirmes que una tradición sea la verdadera ni la compares para descalificar otras.
- NO inventes citas textuales ni atribuciones. Si no tienes certeza absoluta de una cita, parafrasea sin atribuirla.
- No inventes fechas, cifras ni datos dudosos; si no estás seguro, omítelos.

Para cada tema devuelve:
"categoria": la clave, "titulo": título breve (máx. 10 palabras),
"resumen": 4 a 5 líneas (70 a 100 palabras), "interes": por qué es interesante, 1 a 2 líneas (máx. 35 palabras),
"pregunta": una pregunta para reflexionar.

Responde SOLO un JSON: lista de objetos con esas claves."""


def generar(cfg, ia, hoy: date, log=print):
    """Devuelve (temas, motivo_si_no_hay). Actualiza temas-publicados.json si hay temas."""
    ca = cfg.get("para_el_alma", {}) or {}
    if not ca.get("activo", True):
        return None, "apagado"
    try:
        guardado = json.loads(HOY.read_text(encoding="utf-8"))
        if guardado.get("fecha") == hoy.isoformat() and guardado.get("temas"):
            log("Para el alma: se reutilizan los temas de hoy (sin llamar a Gemini)")
            return guardado["temas"], ""
    except (OSError, ValueError):
        pass
    historial = cargar_historial()
    previos = [d for d in historial if d.get("fecha") != hoy.isoformat()]   # una nueva ejecución hoy reemplaza las de hoy
    cats = categorias_del_dia(ca, previos, hoy)
    if not cats:
        return None, "sin categorías"
    try:
        r = ia.generar_json(prompt(cats, [d["titulo"] for d in previos]))
    except GeminiError as ex:
        log(f"Para el alma: Gemini no disponible ({ex}); se omite hoy")
        return [], "Gemini no disponible"
    validas = {c["clave"]: c["nombre"] for c in cats}
    vistos = {normalizar(d["titulo"]) for d in previos}
    temas = []
    for x in r if isinstance(r, list) else []:
        if not isinstance(x, dict):
            continue
        t = {k: str(x.get(k, "")).strip() for k in ("categoria", "titulo", "resumen", "interes", "pregunta")}
        if t["categoria"] not in validas or not all(t.values()) or normalizar(t["titulo"]) in vistos:
            continue
        vistos.add(normalizar(t["titulo"]))
        t["nombre_categoria"] = validas[t["categoria"]]
        temas.append(t)
    if not temas:
        log("Para el alma: la respuesta no trajo temas válidos; se omite hoy")
        return [], "respuesta no válida"
    nuevos = [{"fecha": hoy.isoformat(), "categoria": t["categoria"], "titulo": t["titulo"]} for t in temas]
    guardar_historial(previos + nuevos, int(ca.get("historial_maximo", 120)))
    HOY.parent.mkdir(exist_ok=True)
    HOY.write_text(json.dumps({"fecha": hoy.isoformat(), "temas": temas}, ensure_ascii=False, indent=1), encoding="utf-8")
    log(f"Para el alma: {len(temas)} temas ({', '.join(t['categoria'] for t in temas)})")
    return temas, ""
