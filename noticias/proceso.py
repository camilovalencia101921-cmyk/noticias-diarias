"""Proceso principal: filtros, clasificación (IA o reglas) y selección."""
from collections import Counter, defaultdict

from . import clasificar as C
from . import filtros as FL
from .fuentes import consultas_departamento, descargar_todas, filtrar_por_edad, url_google_news
from .gemini import GeminiError, prompt_clasificar, prompt_resumir
from .utils import primeras_lineas


class Registro:
    """Acumula descartes y mensajes para el log diario y el contador."""

    def __init__(self):
        self.lineas = []
        self.descartes = defaultdict(list)          # motivo -> [(es_local, texto)]
        self.contador = Counter()

    def info(self, msg):
        print(msg, flush=True)
        self.lineas.append(msg)

    def descarte(self, motivo, n, detalle=""):
        self.contador[motivo] += 1
        self.descartes[motivo].append((n.alcance == "local", f"{n.fuente} | {n.titulo[:110]}{(' | ' + detalle) if detalle else ''}"))


def filtrar(noticias, cfg, reg):
    """Publicidad -> palabras prohibidas -> sensacionalismo."""
    out = []
    for n in noticias:
        p = FL.revisar_publicidad(n, cfg)
        if p == "descartar":
            reg.descarte("publicidad", n)
            continue
        n.posible_patrocinio = p == "duda"
        malas = FL.palabras_descartadas(n, cfg)
        if malas:
            reg.descarte("fuera_de_interes", n, ", ".join(malas))
            continue
        pen, señales = FL.sensacionalismo(n.titulo, n.filtro, cfg)
        limite = (cfg.get("filtro_sensacionalismo", {}) or {}).get("limite", 3)
        if pen >= limite:
            reg.descarte("sensacionalismo", n, f"{pen} pts: " + "; ".join(señales))
            continue
        n.penal_sensacionalismo = pen
        out.append(n)
    return out


def clasificar_reglas(noticias, cfg, reg):
    """Tema, sección y criterios por reglas. Descarta lo que no encaja en ningún tema."""
    temas = C.temas_activos(cfg)
    todos = cfg.get("temas") or {}
    out = []
    for n in noticias:
        C.detectar_local(n, cfg)
        n.tema = C.clasificar_tema(n, temas)
        if n.tema is None and n.alcance != "local":
            # ¿pertenece a un tema apagado? (p. ej. contratación)
            if any(t in n.temas_pista and not todos.get(t, {}).get("activo", True) for t in todos):
                reg.descarte("tema_apagado", n)
            else:
                reg.descarte("sin_tema", n)
            continue
        n.seccion = C.asignar_seccion(n, cfg)
        if n.seccion == "local":
            n.categoria_local = C.categoria_local(n, cfg)
        n.criterios = C.criterios_reglas(n, cfg)
        n.puntaje = C.puntaje_final(n, cfg)
        out.append(n)
    return out


def clasificar_ia(noticias, cfg, ia, reg):
    """Lote 1 de Gemini sobre los mejores candidatos por reglas. Devuelve la lista final o lanza GeminiError."""
    temas = C.temas_activos(cfg)
    gcfg = cfg.get("gemini", {}) or {}
    maxc = int(gcfg.get("max_candidatos", 160))
    # prefiltro: todo lo que tenga tema o sea local, ordenado por puntaje de reglas
    candidatos = sorted(noticias, key=lambda n: n.puntaje, reverse=True)
    enviados, resto = candidatos[:maxc], candidatos[maxc:]
    for n in resto:
        reg.descarte("baja_importancia", n, f"prefiltro {n.puntaje}/10")
    respuesta = ia.generar_json(prompt_clasificar(enviados, temas, True))
    if not isinstance(respuesta, list):
        raise GeminiError("la respuesta del lote 1 no es una lista")
    por_id = {str(x.get("id")): x for x in respuesta if isinstance(x, dict)}
    if len(por_id) < len(enviados) * 0.5:
        raise GeminiError(f"respuesta incompleta ({len(por_id)} de {len(enviados)})")
    out = []
    for n in enviados:
        x = por_id.get(n.id)
        if not x:
            out.append(n)              # se queda con el puntaje por reglas
            continue
        tema = x.get("tema")
        c = x.get("c") or []
        if tema in temas and C.tema_valido(n, tema, temas[tema]):
            n.tema = tema
        elif tema == "ninguno" and n.alcance != "local":
            reg.descarte("sin_tema", n, "IA")
            continue
        elif n.alcance != "local" and n.tema not in temas:
            reg.descarte("sin_tema", n, "IA")
            continue
        if len(c) == 5:
            try:
                n.criterios = dict(zip(["alcance", "consecuencias", "novedad", "confirmacion", "profundidad"],
                                       [max(0, min(2, int(v))) for v in c]))
            except (TypeError, ValueError):
                pass
        n.seccion = C.asignar_seccion(n, cfg)
        if n.seccion == "local":
            n.categoria_local = n.categoria_local or C.categoria_local(n, cfg)
        n.puntaje = C.puntaje_final(n, cfg)
        out.append(n)
    return out


def seleccionar(noticias, cfg, reg):
    sel = cfg.get("seleccion", {}) or {}
    temas = cfg.get("temas") or {}
    minimos = {"serias": sel.get("minimo_serias", 6), "ocio": sel.get("minimo_ocio", 5),
               "local": sel.get("minimo_local", 5)}
    maximos = {"serias": sel.get("max_serias", 10), "ocio": sel.get("max_ocio", 7),
               "local": sel.get("max_local", 8)}
    cupo = sel.get("cupo_por_tema", 3)

    def grupo(n):
        if n.seccion == "local":
            return "local"
        return (temas.get(n.tema or "", {}) or {}).get("grupo", "serias")

    elegidas, cuenta, por_tema = [], Counter(), Counter()
    orden = sorted(noticias, key=lambda n: (n.puntaje, -n.zona_prioridad if n.zona_prioridad else 0,
                                            len(n.fuentes_cluster), bool(n.imagen)), reverse=True)
    for n in orden:
        g = grupo(n)
        if n.puntaje < minimos[g]:
            reg.descarte("baja_importancia", n, f"{n.puntaje}/10 < {minimos[g]}")
            continue
        clave_tema = (g, n.categoria_local if g == "local" else n.tema)
        if por_tema[clave_tema] >= (cupo + 1 if g == "local" else cupo):
            reg.descarte("cupo_tema", n, f"{n.puntaje}/10")
            continue
        if cuenta[g] >= maximos[g]:
            reg.descarte("cupo_seccion", n, f"{n.puntaje}/10")
            continue
        cuenta[g] += 1
        por_tema[clave_tema] += 1
        elegidas.append(n)
    return elegidas


def completar_departamento(cfg, ya_locales, reg, procesar):
    """Si no hay noticias locales, intenta con noticias del departamento (modos ciudad y zonas)."""
    loc = cfg.get("local", {}) or {}
    if ya_locales or not loc.get("activo", True) or loc.get("modo") == "personalizado":
        return []
    fuentes = [{"nombre": f"{nom} (Google News)", "url": url_google_news(q), "alcance": "local",
                "filtro": "flexible", "zona_prioridad": p} for nom, q, p in consultas_departamento(loc)]
    if not fuentes:
        return []
    reg.info("Sin noticias locales: se buscan noticias del departamento")
    items, _ = descargar_todas(fuentes)
    items, _ = filtrar_por_edad(items, (cfg.get("seleccion", {}) or {}).get("horas_maximas", 36))
    return procesar(items)


def resumir(elegidas, cfg, ia, usar_ia, reg):
    """Lote 2: resumen y 'por qué importa'. En respaldo: primeras 2 líneas de la descripción."""
    mej = cfg.get("mejoras", {}) or {}
    con_resumen = (mej.get("resumen", {}) or {}).get("activo", True)
    pq = mej.get("por_que_importa", {}) or {}
    con_pq = pq.get("activo", True)
    if usar_ia and (con_resumen or con_pq) and elegidas:
        try:
            r = ia.generar_json(prompt_resumir(elegidas, pq.get("perfil_lector", "un lector en Colombia"), con_pq))
            por_id = {str(x.get("id")): x for x in r if isinstance(x, dict)}
            for n in elegidas:
                x = por_id.get(n.id, {})
                n.resumen = (x.get("r") or "").strip() if con_resumen else ""
                n.por_que = (x.get("pq") or "").strip() if con_pq else ""
                if con_resumen and not n.resumen:
                    n.resumen = primeras_lineas(n.descripcion)
            return True
        except GeminiError as ex:
            reg.info(f"Lote 2 de Gemini falló ({ex}); resúmenes por reglas")
    for n in elegidas:
        n.resumen = primeras_lineas(n.descripcion) if con_resumen else ""
        n.por_que = ""
    return False
