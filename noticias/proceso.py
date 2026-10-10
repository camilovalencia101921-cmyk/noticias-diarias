"""Proceso principal: filtros, clasificación (IA o reglas) y selección."""
from collections import Counter, defaultdict

from . import clasificar as C
from . import filtro_sexual as FS
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
    """Contenido sexual -> publicidad -> palabras prohibidas -> marca de sensacionalismo.

    El sensacionalismo ya no descarta aquí: marca la noticia. Las marcadas no pueden ser
    destacadas, pero sí aparecen en "Ver más" con la etiqueta "Posible sensacionalismo"."""
    fsens = cfg.get("filtro_sensacionalismo", {}) or {}
    limite = fsens.get("limite", 3)
    etiqueta_desde = fsens.get("etiqueta_desde", 2)
    out = []
    for n in noticias:
        sexo = FS.revisar(cfg, n.titulo, n.descripcion, " ".join(n.etiquetas), n.enlace.replace("-", " "))
        if sexo:
            reg.descarte("contenido_sexual", n, ", ".join(sexo[:3]))
            continue
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
        n.penal_sensacionalismo = pen
        n.sensacional = pen >= limite
        n.senales_sensacionalismo = señales
        pen_estricto, _ = FL.sensacionalismo(n.titulo, "estricto", cfg)
        n.posible_sensacionalismo = pen_estricto >= etiqueta_desde
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


def clasificar_ia(noticias, cfg, ia, reg, extras=None):
    """Lote 1 de Gemini sobre los mejores candidatos por reglas. Devuelve la lista final o lanza GeminiError."""
    temas = C.temas_activos(cfg)
    gcfg = cfg.get("gemini", {}) or {}
    maxc = int(gcfg.get("max_candidatos", 160))
    # prefiltro: todo lo que tenga tema o sea local, ordenado por puntaje de reglas
    candidatos = sorted(noticias, key=lambda n: n.puntaje, reverse=True)
    enviados, resto = candidatos[:maxc], candidatos[maxc:]
    for n in resto:
        reg.descarte("baja_importancia", n, f"prefiltro {n.puntaje}/10")
    respuesta = ia.generar_json(prompt_clasificar(enviados, temas, True, extras))
    if not isinstance(respuesta, list):
        raise GeminiError("la respuesta del lote 1 no es una lista")
    por_id = {str(x.get("id")): x for x in respuesta if isinstance(x, dict)}
    if len(por_id) < len(enviados) * 0.5:
        raise GeminiError(f"respuesta incompleta ({len(por_id)} de {len(enviados)})")
    for v in extras or []:                 # videos: pasan solo si la IA los revisó y dijo "no sexual"
        x = por_id.get(v["id"])
        v["revisado"] = bool(x) and str(x.get("s", "2")) == "0"
    out = []
    for n in enviados:
        x = por_id.get(n.id)
        if not x:                      # sin revisión de la IA: no puede ser destacada (falla cerrado)
            reg.descarte("sin_revision_ia", n)
            continue
        if str(x.get("s", "2")) != "0":   # 1 = sexual o sugerente, 2 = dudoso -> fuera
            n.sexual_ia = True
            reg.descarte("contenido_sexual", n, "revisión IA")
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
    grupos = {(v or {}).get("grupo", "serias") for v in temas.values()} | {"local"}
    # cada grupo (pestaña) tiene su mínimo y su tope: minimo_<grupo> y max_<grupo> en config.yaml
    minimos = {g: sel.get(f"minimo_{g}", 6 if g == "serias" else 5) for g in grupos}
    maximos = {g: sel.get(f"max_{g}", 10 if g == "serias" else 4) for g in grupos}
    cupo = sel.get("cupo_por_tema", 3)

    def grupo(n):
        if n.seccion == "local":
            return "local"
        return (temas.get(n.tema or "", {}) or {}).get("grupo", "serias")

    elegidas, sobrantes, cuenta, por_tema = [], [], Counter(), Counter()
    orden = sorted(noticias, key=lambda n: (getattr(n, "favorito", False), n.puntaje, -n.zona_prioridad if n.zona_prioridad else 0,
                                            len(n.fuentes_cluster), bool(n.imagen)), reverse=True)
    for n in orden:
        g = grupo(n)
        if getattr(n, "sensacional", False):
            reg.descarte("sensacionalismo", n, f"{n.penal_sensacionalismo} pts: " + "; ".join(getattr(n, "senales_sensacionalismo", [])))
            continue
        if n.puntaje < minimos.get(g, 5):
            reg.descarte("baja_importancia", n, f"{n.puntaje}/10 < {minimos.get(g, 5)}")
            continue
        clave_tema = (g, n.categoria_local if g == "local" else n.tema)
        if por_tema[clave_tema] >= (cupo + 1 if g == "local" else cupo):
            sobrantes.append((n, "cupo_tema"))
            continue
        if cuenta[g] >= maximos.get(g, 4):
            sobrantes.append((n, "cupo_seccion"))
            continue
        cuenta[g] += 1
        por_tema[clave_tema] += 1
        elegidas.append(n)
    return elegidas, sobrantes


def elegir_ver_mas(sobrantes, cfg, reg, aceptar=lambda n: True):
    """Bloque "Ver más": siguientes mejores noticias de cada sección que superaron el mínimo
    pero quedaron fuera por los topes. No cuentan para los topes. Lo que no entra se registra
    como descartado por cupo, igual que antes."""
    maximo = int((cfg.get("seleccion", {}) or {}).get("ver_mas_por_seccion", 6))
    cupo = (cfg.get("seleccion", {}) or {}).get("cupo_por_tema", 3)
    por_seccion, por_tema, extra = Counter(), Counter(), []
    for n, motivo in sobrantes:          # ya vienen ordenadas de mayor a menor puntaje
        tema = n.categoria_local if n.seccion == "local" else n.tema
        if (por_seccion[n.seccion] < maximo and por_tema[(n.seccion, tema)] < cupo and aceptar(n)):
            por_seccion[n.seccion] += 1
            por_tema[(n.seccion, tema)] += 1
            extra.append(n)
        else:
            reg.descarte(motivo, n, f"{n.puntaje}/10")
    return extra


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
            for n in list(elegidas):
                x = por_id.get(n.id, {})
                if x and str(x.get("s", "0")) != "0":
                    n.sexual_ia = True
                    reg.descarte("contenido_sexual", n, "revisión IA (destacadas)")
                    elegidas.remove(n)
                    continue
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
