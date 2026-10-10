"""Clasificación y puntaje por reglas (modo de respaldo y prefiltro)."""
from .utils import ahora_utc, contar_palabras, encontrar_palabras, normalizar

PAISES_CO = ["colombia", "colombiano", "colombiana", "colombianos", "colombianas", "bogota", "medellin",
             "cali", "barranquilla", "cartagena", "petro", "de la espriella", "congreso de la republica",
             "consejo de estado", "corte constitucional", "corte suprema de justicia", "fiscalia general de la nacion",
             "procuraduria", "contraloria", "dian", "registraduria", "camara de representantes", "gobierno nacional",
             "minhacienda", "banco de la republica", "ecopetrol", "eln", "farc", "jep", "disidencias",
             "clan del golfo", "antioquia", "cordoba", "valle del cauca", "santander", "atlantico", "bolivar",
             "cauca", "narino", "huila", "tolima", "choco", "boyaca", "cundinamarca", "magdalena", "cesar",
             "sucre", "la guajira", "caqueta", "putumayo", "arauca", "casanare", "quindio", "risaralda", "caldas",
             "guaviare", "monteria", "lorica", "cucuta", "bucaramanga", "pereira", "manizales", "ibague", "neiva",
             "pasto", "villavicencio", "santa marta", "sincelejo", "valledupar", "popayan", "tunja", "trm",
             "liga betplay", "dimayor", "supersalud", "nueva eps", "ungrd", "ideam", "mindefensa", "cancilleria colombiana"]


def temas_activos(cfg):
    return {k: v for k, v in (cfg.get("temas") or {}).items() if v.get("activo", True)}


def _texto(n):
    return normalizar(n.titulo), normalizar(n.titulo + " " + n.descripcion[:600] + " " + " ".join(n.etiquetas[:8]))


def tema_valido(n, clave, tema, texto=None):
    """Aplica 'requiere' y 'excluir' de un tema."""
    texto = texto or _texto(n)[1]
    if contar_palabras(texto, tema.get("excluir")):
        return False
    if tema.get("solo_colombia") and n.alcance == "internacional" and not contar_palabras(texto, PAISES_CO):
        return False
    req = tema.get("requiere")
    pista_fuerte = clave in n.temas_pista and not n.pista_debil and not tema.get("requiere_siempre")
    if req and not pista_fuerte and not contar_palabras(texto, req):
        return False
    return True


def clasificar_tema(n, temas):
    titulo, texto = _texto(n)
    puntos = {}
    for clave, t in temas.items():
        if not tema_valido(n, clave, t, texto):
            continue
        p = contar_palabras(texto, t.get("palabras")) + contar_palabras(titulo, t.get("palabras"))
        if clave in n.temas_pista and (p > 0 or not n.pista_debil):
            p += 1.5
        if p > 0:
            puntos[clave] = p
    # tecnología solo si no encaja en IA ni ciberseguridad
    if "tecnologia" in puntos and (puntos.get("inteligencia_artificial", 0) >= 1 or puntos.get("ciberseguridad", 0) >= 1):
        puntos.pop("tecnologia")
    if not puntos:
        return None
    return max(puntos, key=puntos.get)


def categoria_local(n, cfg):
    cats = (cfg.get("local", {}) or {}).get("categorias", {}) or {}
    titulo, texto = _texto(n)
    mejor, mp = "otros", 0
    for clave, c in cats.items():
        p = contar_palabras(texto, c.get("palabras")) + 2 * contar_palabras(titulo, c.get("palabras"))
        if p > mp:
            mejor, mp = clave, p
    return mejor


def lugares_locales(cfg):
    loc = cfg.get("local", {}) or {}
    modo = loc.get("modo", "zonas")
    if modo == "ciudad":
        c = loc.get("ciudad", {}) or {}
        return [(c.get("nombre"), 1)] if c.get("nombre") else []
    if modo == "zonas":
        return [(l, i) for i, z in enumerate(loc.get("zonas", []) or [], 1) for l in (z.get("lugares") or [])]
    return [(p, 1) for p in (loc.get("personalizado", {}) or {}).get("palabras_clave", []) or []]


def detectar_local(n, cfg):
    """Marca como local una noticia nacional que menciona los lugares configurados."""
    if not (cfg.get("local", {}) or {}).get("activo", True):
        return
    if n.alcance == "local":
        return
    titulo = normalizar(n.titulo)
    for lugar, prio in lugares_locales(cfg):
        if lugar and contar_palabras(titulo, [lugar]):
            n.alcance = "local"
            n.zona_prioridad = prio
            return


def criterios_reglas(n, cfg):
    """Cinco criterios de 0 a 2: alcance, consecuencias, novedad, confirmación, profundidad."""
    sel = cfg.get("seleccion", {}) or {}
    titulo, texto = _texto(n)
    lista = list(sel.get("palabras_impacto", []))
    lista += ((cfg.get("temas") or {}).get(n.tema or "", {}) or {}).get("palabras_impacto", []) or []
    impacto = len(encontrar_palabras(texto, lista))
    impacto_tit = len(encontrar_palabras(titulo, lista))
    alcance = 1
    if n.alcance in ("nacional", "internacional") and (impacto_tit or n.oficial):
        alcance = 2
    elif n.alcance == "local" and n.zona_prioridad == 1:
        alcance = 1
    consecuencias = 2 if (impacto_tit >= 1 and impacto >= 2) else (1 if impacto else 0)
    horas = (ahora_utc() - n.fecha).total_seconds() / 3600 if n.fecha else 24
    novedad = 2 if horas <= 12 else (1 if horas <= 24 else 0)
    nf = len(n.fuentes_cluster or {n.fuente})
    confirmacion = 2 if (n.oficial or nf >= 3) else (1 if nf == 2 else 0)
    ld = len(n.descripcion)
    profundidad = 2 if ld > 280 else (1 if ld > 90 else 0)
    return {"alcance": alcance, "consecuencias": consecuencias, "novedad": novedad,
            "confirmacion": confirmacion, "profundidad": profundidad}


def puntaje_final(n, cfg):
    """Suma criterios (0-10), aplica peso del tema o categoría local y bonos."""
    base = sum(n.criterios.values())
    if n.seccion == "local":
        cat = ((cfg.get("local", {}) or {}).get("categorias", {}) or {}).get(n.categoria_local or "otros", {})
        peso = float(cat.get("peso", 1.0))
    else:
        peso = float(((cfg.get("temas") or {}).get(n.tema or "", {}) or {}).get("peso", 1.0))
    p = base * peso
    pv = (cfg.get("mejoras", {}) or {}).get("palabras_vigiladas", {}) or {}
    if pv.get("activo") and pv.get("lista"):
        if contar_palabras(normalizar(n.titulo + " " + n.descripcion), pv["lista"]):
            n.vigilada = True
            p += float(pv.get("bono", 2))
    if n.penal_sensacionalismo:
        p -= 1
    return max(1, min(10, round(p)))


def asignar_seccion(n, cfg):
    temas = cfg.get("temas") or {}
    grupo = (temas.get(n.tema or "", {}) or {}).get("grupo")
    if grupo in ("ocio", "deportes"):
        return grupo
    if n.alcance == "local":
        return "local"
    texto = normalizar(n.titulo + " " + n.descripcion[:300])
    menciona_co = contar_palabras(texto, PAISES_CO) > 0
    if n.alcance == "internacional" and menciona_co:
        return "nacional"
    if n.alcance == "nacional" and not menciona_co:
        return "internacional"         # medio nacional contando una noticia de otro país
    return "internacional" if n.alcance == "internacional" else "nacional"
