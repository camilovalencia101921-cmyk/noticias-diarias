"""Genera la página (diseño Fase 1, pensado para celular de 390 px).

- index.html: encabezado, pestañas, destacadas de cada pestaña y secciones especiales.
- mas.json: las noticias de "Ver N noticias más" (sin IA, solo medios aprobados);
  se cargan al tocar el botón, así la página inicial es liviana.
El estado del usuario (leídas, guardadas, letra, medios y palabras bloqueadas) vive en el
almacenamiento del navegador (localStorage); no hay servidor.
"""
import json
from html import escape

from .ilustraciones import DIBUJOS, simbolos
from .mercados import sparkline
from .pestanas import FONDOS, PESTANAS, SUBFILTROS

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
ORDEN_LOCAL = ["seguridad", "orden_publico", "movilidad_servicios", "otros"]
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E"
           "%3Crect width='100' height='100' rx='24' fill='%23D85A30'/%3E"
           "%3Cpath d='M30 74V26h10l20 31V26h10v48H60L40 43v31z' fill='%23fff'/%3E%3C/svg%3E")
FUENTES_GOOGLE = ("https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,700"
                  "&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap")


def fecha_larga(d):
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def e(t):
    return escape(t or "", quote=True)


def tiempo_relativo(fecha, ahora):
    s = max(0, (ahora - fecha).total_seconds())
    if s < 3600:
        return f"{max(1, int(s // 60))} min"
    if s < 86400:
        return f"{int(s // 3600)} h"
    return f"{int(s // 86400)} d"


class Pagina:
    def __init__(self, cfg, ctx):
        self.cfg = cfg
        self.ctx = ctx
        self.temas = cfg.get("temas") or {}
        self.cats = ((cfg.get("local", {}) or {}).get("categorias", {}) or {})

    # ------------------------------------------------------------ datos de una noticia
    def etiqueta(self, n):
        if n.seccion == "local":
            c = self.cats.get(n.categoria_local or "otros", {})
            return c.get("nombre", "Local"), c.get("color", "#546E7A")
        t = self.temas.get(n.tema or "", {})
        return t.get("nombre", "General"), t.get("color", "#455A64")

    def clave_ilu(self, n):
        if n.seccion == "local" and n.categoria_local in ("seguridad", "orden_publico", "movilidad_servicios", "otros"):
            return f"local_{n.categoria_local}"
        return n.tema if n.tema in DIBUJOS else "general"

    def ilustracion(self, n, prefijo):
        clave = self.clave_ilu(n)
        propia = self.ctx["imagenes_categoria"].get(clave) or self.ctx["imagenes_categoria"].get(n.tema or "")
        if propia:
            return f'<img class="ilu" src="{prefijo}{e(propia)}" alt="" loading="lazy">'
        return f'<svg class="ilu" aria-hidden="true"><use href="#ilu-{clave}"/></svg>'

    def miniatura(self, n, prefijo, clase):
        foto = ""
        if n.imagen and n.aprobado:          # capa 4: solo medios aprobados que pasaron los filtros
            foto = (f'<img class="foto" src="{e(n.imagen)}" alt="" loading="lazy" decoding="async" '
                    f'referrerpolicy="no-referrer" onerror="this.remove()" '
                    f'onload="if(this.naturalWidth&&this.naturalWidth<160)this.remove()">')
        play = (f'<a class="play" href="{e(n.video)}" target="_blank" rel="noopener noreferrer" aria-label="Ver video">▶</a>'
                if n.video and n.aprobado else "")
        return f'<div class="{clase}">{self.ilustracion(n, prefijo)}{foto}{play}</div>'

    def atributos(self, n):
        nombre, color = self.etiqueta(n)
        return (f' data-id="{n.id}" data-sub="{" ".join(getattr(n, "subs", []))}" data-src="{e(n.fuente)}"'
                f' data-dom="{e(n.dominio_medio)}" data-u="{e(n.enlace)}" data-t="{e(n.titulo)}"'
                f' data-tm="{e(nombre)}" data-c="{color}" data-h="{int(n.fecha.timestamp())}" style="--c:{color}"')

    def cobertura(self, n):
        if len(n.cluster) < 2:
            return ""
        links = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{e(f)}</a></li>'
                        for f, u in n.cluster)
        return f'<details class="cob"><summary>{len(n.cluster)} medios cubren esto</summary><ul>{links}</ul></details>'

    def insignias(self, n):
        out = []
        if n.vigilada:
            out.append('<span class="ins">⭐ Vigilada</span>')
        if n.seguimiento_dia:
            out.append(f'<span class="ins seg">Seguimiento · día {n.seguimiento_dia}</span>')
        if n.posible_patrocinio:
            out.append('<span class="ins pat">Posible patrocinio</span>')
        return "".join(out)

    def meta(self, n):
        rel = tiempo_relativo(n.fecha, self.ctx["ahora_utc"])
        return (f'<p class="meta"><span class="src">{e(n.fuente)}</span> · '
                f'<time data-h="{int(n.fecha.timestamp())}">{rel}</time></p>')

    # ------------------------------------------------------------ tarjetas
    def tarjeta_grande(self, n, prefijo):
        nombre, _ = self.etiqueta(n)
        res = f'<p class="res">{e(n.resumen)}</p>' if n.resumen else ""
        pq = f'<p class="pq"><b>Por qué importa:</b> {e(n.por_que)}</p>' if n.por_que else ""
        return (f'<article class="card grande it"{self.atributos(n)}>{self.miniatura(n, prefijo, "th16")}'
                f'<div class="cu"><div class="fila-chips"><span class="chip-t">{e(nombre)}</span>{self.insignias(n)}</div>'
                f'<h3 class="tit-g"><a class="lk" href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a></h3>'
                f'{res}{pq}{self.meta(n)}{self.cobertura(n)}'
                f'<div class="acc"><button type="button" class="b-guardar" aria-label="Guardar">{ICONO_GUARDAR}<span>Guardar</span></button>'
                f'<button type="button" class="b-compartir" aria-label="Compartir">{ICONO_COMPARTIR}<span>Compartir</span></button>'
                f'<button type="button" class="b-menu" aria-label="Ocultar o bloquear">{ICONO_OCULTAR}<span>Ocultar</span></button></div>'
                f'</div></article>')

    def tarjeta(self, n, prefijo):
        nombre, _ = self.etiqueta(n)
        res = f'<p class="res">{e(n.resumen)}</p>' if n.resumen else ""
        return (f'<article class="card comp it"{self.atributos(n)}><div class="cu">'
                f'<div class="fila-chips"><span class="chip-t">{e(nombre)}</span>{self.insignias(n)}</div>'
                f'<h3 class="tit-c"><a class="lk" href="{e(n.enlace)}" target="_blank" rel="noopener noreferrer">{e(n.titulo)}</a></h3>'
                f'{res}<div class="pie">{self.meta(n)}<button type="button" class="b-menu mini" aria-label="Opciones: guardar, compartir, ocultar">⋯</button></div>'
                f'{self.cobertura(n)}</div>{self.miniatura(n, prefijo, "th76")}</article>')

    # ------------------------------------------------------------ bloques especiales
    def mercados(self):
        out = []
        for m in self.ctx["mercados"]:
            clase = "up" if m["cambio"] > 0 else ("down" if m["cambio"] < 0 else "flat")
            flecha = {"up": "▲", "down": "▼", "flat": "▬"}[clase]
            valor = f'{m["valor"]:,.2f}'.replace(",", "X").replace(".", ",").replace("X", ".")
            out.append(f'<div class="mk {clase}"><div class="mk-n">{e(m["nombre"])}</div>'
                       f'<div class="mk-v">${valor} <small>{m["unidad"]}</small></div>'
                       f'<div class="mk-c">{flecha} {abs(m["pct"]):.2f}%</div>{sparkline(m["serie"])}</div>')
        return f'<div class="mercados w" data-sub="economia">{"".join(out)}</div>' if out else ""

    def agenda(self):
        items = self.ctx["agenda"]
        if not items:
            return ""
        filas, dia = [], None
        for it in items:
            if it["dia"] != dia:
                dia = it["dia"]
                filas.append(f'<li class="lh">{dia}</li>')
            color = (self.temas.get(it["tema"], {}) or {}).get("color", "#546E7A")
            texto = e(it["texto"])
            if it.get("enlace"):
                texto = f'<a href="{e(it["enlace"])}" target="_blank" rel="noopener noreferrer">{texto}</a>'
            filas.append(f'<li data-sub="{it.get("sub", "eventos")}"><span class="hr">{e(it["hora"]) or "—"}</span><span class="tx">'
                         f'<span class="chip-t" style="--c:{color}">{e(it["categoria"])}</span><br>{texto}</span></li>')
        return f'<div class="bloque"><ul class="lista-s">{"".join(filas)}</ul><p class="nota">Horas de Colombia.</p></div>'

    def resultados(self):
        rs = self.ctx.get("resultados") or []
        if not rs:
            return ""
        tarj = "".join(
            f'<a class="res-p w" data-sub="{r["sub"]}" href="{e(r["enlace"])}" target="_blank" rel="noopener noreferrer">'
            f'<span class="rl">{e(r["liga"])} · {"🔴 en juego" if r["en_juego"] else e(r["detalle"])}</span>'
            f'<span class="re"><b>{e(r["gl"])}</b> {e(r["local"])}</span><span class="re"><b>{e(r["gv"])}</b> {e(r["visita"])}</span></a>'
            for r in rs)
        return f'<h3 class="bt">Resultados recientes</h3><div class="franja">{tarj}</div>'

    def tablas(self):
        ts = self.ctx.get("tablas") or []
        if not ts:
            return ""
        out = []
        for t in ts:
            filas = "".join(f'<tr><td>{f["pos"]}</td><td>{e(f["equipo"])}</td><td>{e(f["pj"])}</td><td><b>{e(f["pts"])}</b></td></tr>'
                            for f in t["filas"])
            out.append(f'<details class="tabla w" data-sub="{t["sub"]}"><summary>📊 {e(t["liga"])}: tabla de posiciones</summary>'
                       f'<table><thead><tr><th>#</th><th>Equipo</th><th>PJ</th><th>Pts</th></tr></thead><tbody>{filas}</tbody></table>'
                       f'<p class="nota">{e(t["titulo"])} · primeros {len(t["filas"])} · datos: ESPN</p></details>')
        return "".join(out)

    def cine(self):
        pelis, origen = self.ctx.get("cine") or (None, "")
        if pelis is None:
            return ""
        color = (self.cfg.get("cine", {}) or {}).get("color", "#D64550")
        if not pelis:
            return '<div class="bloque w" data-sub="cine"><h3 class="bt">🎬 Estrenos en Colombia</h3><p class="aviso">Sin estrenos confirmados hoy.</p></div>'
        filas, grupo = [], None
        for p in pelis:
            g = "Esta semana" if p["semana"] else "Próximos"
            if g != grupo:
                grupo = g
                filas.append(f'<li class="lh">{g}</li>')
            f = p["fecha"]
            filas.append(f'<li><span class="hr">{f.day} {MESES[f.month - 1][:3]}</span><span class="tx"><b>{e(p["titulo"])}</b> '
                         f'<span class="chip-t" style="--c:{color}">{e(p["genero"])}</span><br><small>{e(p["sinopsis"])}</small></span></li>')
        return (f'<div class="bloque w" data-sub="cine" style="--c:{color}"><h3 class="bt">🎬 Estrenos en Colombia</h3>'
                f'<ul class="lista-s">{"".join(filas)}</ul><p class="nota">Datos: {e(origen)}. Las salas pueden cambiar las fechas.</p></div>')

    def alma(self):
        temas = self.ctx.get("alma")
        if temas is None:
            return ""
        color = (self.cfg.get("para_el_alma", {}) or {}).get("color", "#C98A1B")
        if not temas:
            return '<div class="bloque w" data-sub="alma"><h3 class="bt">🕯️ Para el alma</h3><p class="aviso">Hoy no disponible.</p></div>'
        tarjetas = "".join(
            f'<article class="card alma" style="--c:{color}"><span class="chip-t">{e(t["nombre_categoria"])}</span>'
            f'<h3 class="tit-c">{e(t["titulo"])}</h3><p class="txt">{e(t["resumen"])}</p>'
            f'<p class="pq"><b>Por qué es interesante:</b> {e(t["interes"])}</p><p class="preg">🤔 {e(t["pregunta"])}</p></article>'
            for t in temas)
        return (f'<div class="w" data-sub="alma"><h3 class="bt">🕯️ Para el alma</h3>{tarjetas}'
                f'<p class="nota">Texto generado por IA; verifica antes de citar.</p></div>')

    def videos(self):
        """Pantalla estilo Instagram: un video por pantalla (scroll vertical), reproductor oficial de YouTube."""
        vs = self.ctx.get("videos") or []
        if not vs:
            return ""
        slides = []
        for v in vs:
            h = int(v["fecha"].timestamp()) if v.get("fecha") else 0
            slides.append(
                f'<div class="vs it" data-vid="{e(v["vid"])}" data-id="{v["id"]}" data-sub="{v["sub"]}" data-src="{e(v["canal"])}" '
                f'data-dom="youtube.com" data-u="{e(v["enlace"])}" data-t="{e(v["titulo"])}" data-tm="Video · {e(v["tema"])}" '
                f'data-c="#C25E14" data-h="{h}"><div class="vplayer"></div><div class="vtap" aria-hidden="true"><span class="vpl">▶</span></div>'
                f'<div class="vinfo"><div class="fila-chips"><span class="vchip ok">✔ Canal aprobado</span><span class="vchip">{e(v["tema"])}</span></div>'
                f'<h3 class="vtit">{e(v["titulo"])}</h3><p class="vcan">{e(v["canal"])} · <time data-h="{h}"></time></p></div>'
                f'<div class="vacc"><button type="button" class="b-guardar" aria-label="Guardar">{ICONO_GUARDAR}<span>Guardar</span></button>'
                f'<button type="button" class="b-compartir" aria-label="Compartir">{ICONO_COMPARTIR}<span>Compartir</span></button>'
                f'<button type="button" class="b-bloquear" aria-label="Bloquear canal">{ICONO_OCULTAR}<span>Bloquear canal</span></button></div></div>')
        slides.append('<div class="vs vfin"><p>✅ Estás al día en Videos</p><small>Tope de 20 videos por sesión.</small></div>')
        return (f'<div class="vtop"><p class="vcont" id="vcont">1 de {len(vs)} · tope por sesión</p>'
                f'<button type="button" class="vsonido" id="vsonido">🔇 Activar sonido</button></div>'
                f'<div class="vfeed" id="vfeed">{"".join(slides)}</div>')

    def instagram(self):
        botones = self.ctx.get("instagram") or []
        if not botones:
            return ""
        b = "".join(f'<a class="ig" href="{e(x["url"])}" target="_blank" rel="noopener noreferrer">{ICONO_IG}{e(x["nombre"])}</a>'
                    for x in botones)
        return f'<div class="bloque"><h3 class="bt">Tus medios locales en Instagram</h3><div class="igs">{b}</div></div>'

    # ------------------------------------------------------------ pestañas
    def destacadas_de(self, clave):
        el = self.ctx["elegidas"]
        if clave == "hoy":                  # las clave del día (serias) + hasta 3 deportivas
            lista = [n for n in el if n.seccion in ("nacional", "internacional")
                     and (self.temas.get(n.tema or "", {}) or {}).get("grupo", "serias") == "serias"]
            dep = sorted((n for n in el if getattr(n, "pestana", "") == "deportes"),
                         key=lambda n: (-getattr(n, "favorito", False), -n.puntaje))
            dep = dep[: int((self.cfg.get("seleccion", {}) or {}).get("hoy_max_deportes", 3))]
            for n in dep:
                if "deportes" not in n.subs:
                    n.subs = n.subs + ["deportes"]
            return sorted(lista, key=lambda n: (-n.puntaje, -bool(n.imagen))) + dep
        lista = [n for n in el if getattr(n, "pestana", "") == clave]
        if clave == "local":
            return sorted(lista, key=lambda n: (ORDEN_LOCAL.index(n.categoria_local) if n.categoria_local in ORDEN_LOCAL else 9, -n.puntaje))
        return sorted(lista, key=lambda n: (-getattr(n, "favorito", False), -n.puntaje, -bool(n.imagen)))

    def contenido(self, clave, prefijo):
        """(antes, cuerpo, despues, ids_destacadas, subs_con_contenido) de una pestaña."""
        antes = cuerpo = despues = ""
        ids, subs = [], set()
        if clave == "videos":
            vs = self.ctx.get("videos") or []
            cuerpo = self.videos()
            ids = [v["id"] for v in vs]
            subs |= {v["sub"] for v in vs}
        elif clave == "agenda":
            cuerpo = self.agenda()
            subs |= {it.get("sub", "eventos") for it in self.ctx["agenda"]}
        else:
            lista = self.destacadas_de(clave)
            ids = [n.id for n in lista]
            for n in lista:
                subs |= set(n.subs)
            cuerpo = (self.tarjeta_grande(lista[0], prefijo) + "".join(self.tarjeta(n, prefijo) for n in lista[1:])) if lista else ""
        if clave == "hoy":
            antes = self.mercados() + self.nota_respaldo()
            if self.ctx["mercados"]:
                subs.add("economia")
            k = self.ctx["contador"]
            despues = (f'<p class="nota">🛡️ Filtro de hoy: {k["revisados"]} titulares revisados · {k["sexual"]} descartados por '
                       f'contenido sexual · {k["sensacionalismo"]} por sensacionalismo · {k["publicidad"]} por publicidad.</p>')
        elif clave == "deportes":
            antes = self.resultados() + self.tablas()
            subs |= {r["sub"] for r in self.ctx.get("resultados") or []} | {t["sub"] for t in self.ctx.get("tablas") or []}
        elif clave == "ocio":
            despues = self.cine()
            if (self.ctx.get("cine") or (None, ""))[0]:
                subs.add("cine")
        elif clave == "fe":
            antes = self.alma()
            if self.ctx.get("alma"):
                subs.add("alma")
        elif clave == "local":
            despues = self.instagram()
        for n in self.ctx["ver_mas"].get(clave, []):
            subs |= set(getattr(n, "subs", []))
        return antes, cuerpo, despues, ids, subs

    def tiene_contenido(self, clave, archivo):
        antes, cuerpo, despues, ids, _ = self.contenido(clave, "")
        n_mas = 0 if archivo else len(self.ctx["ver_mas"].get(clave, []))
        if clave == "local":                      # los botones de Instagram solos no cuentan como contenido
            despues = ""
        if clave == "hoy":
            return True
        if clave == "videos":
            return bool(ids) and not archivo
        return bool(ids or n_mas or cuerpo or (antes and clave in ("fe", "deportes")) or (despues and clave == "ocio"))

    def panel(self, clave, icono, nombre, prefijo, archivo, primera):
        antes, cuerpo, despues, _, subs_ok = self.contenido(clave, prefijo)
        subs = [(k, ic, t) for k, ic, t in SUBFILTROS.get(clave, []) if k == "todo" or k in subs_ok]
        chips = "".join(f'<button type="button" class="sf{" on" if k == "todo" else ""}" data-sf="{k}" '
                        f'aria-pressed="{"true" if k == "todo" else "false"}">{ic} {t}</button>' for k, ic, t in subs)
        fondo = FONDOS.get(clave)
        estilo = f' style="background:{fondo}"' if fondo else ""
        cab = (f'<div class="ph{" grad" if fondo else ""}"{estilo}>'
               f'<h2>{icono} {nombre}</h2><p class="nuevas" data-nuevas></p></div>')
        n_mas = len(self.ctx["ver_mas"].get(clave, []))
        vermas = ""
        if n_mas and not archivo:
            vermas = (f'<button type="button" class="vermas" data-tab="{clave}">Ver {n_mas} noticias más</button>'
                      f'<div class="masl" id="mas-{clave}"></div>')
        filtros = f'<div class="subs">{chips}</div>' if len(subs) > 1 else ""
        oculto = "" if primera else " hidden"
        if clave == "videos":
            return (f'<section class="panel videos-p" id="p-{clave}" data-tab="{clave}"{oculto}>{filtros}{cuerpo}</section>')
        return (f'<section class="panel" id="p-{clave}" data-tab="{clave}"{oculto}>{cab}{filtros}{antes}'
                f'<div class="lista">{cuerpo}</div>{despues}{vermas}'
                f'<p class="aldia">Estás al día en {nombre}</p></section>')

    def panel_guardadas(self):
        return ('<section class="panel" id="p-guardado" data-tab="guardado" hidden><div class="ph"><h2>🔖 Guardadas</h2>'
                '<p class="nuevas" data-nuevas></p></div><div class="lista" id="lista-guardadas"></div>'
                '<p class="aldia">Estás al día en Guardadas</p></section>')

    def estado_fuentes(self):
        errores = self.ctx.get("errores") or {}
        hora = e(self.ctx.get("hora", ""))
        if not errores:
            return f'<p>Última actualización: <b>{hora}</b>. Todas las fuentes respondieron.</p>'
        lista = "".join(f"<li>{e(k)}: {e(v)}</li>" for k, v in sorted(errores.items()))
        return (f'<p>Última actualización: <b>{hora}</b>. Fuentes que fallaron en esta actualización '
                f'({len(errores)}):</p><ul class="aj-l">{lista}</ul>')

    def nota_respaldo(self):
        if self.ctx["modo_respaldo"]:
            return '<p class="nota">Hoy se usó el modo de respaldo (sin IA): solo medios aprobados.</p>'
        if self.ctx.get("respaldo_resumenes"):
            return '<p class="nota">Hoy los resúmenes se hicieron en modo de respaldo (sin IA).</p>'
        return ""

    def datos_ver_mas(self):
        """JSON con el resto de noticias por pestaña (sin IA, solo medios aprobados)."""
        out = {}
        for pest, lista in self.ctx["ver_mas"].items():
            filas = []
            for n in lista:
                nombre, color = self.etiqueta(n)
                f = {"id": n.id, "t": n.titulo, "u": n.enlace, "f": n.fuente, "d": n.dominio_medio,
                     "h": int(n.fecha.timestamp()), "tm": nombre, "c": color, "s": getattr(n, "subs", [])}
                if n.posible_sensacionalismo:
                    f["z"] = 1
                if len(n.cluster) >= 2:
                    f["o"] = [[a, b] for a, b in n.cluster]
                filas.append(f)
            out[pest] = filas
        return json.dumps({"generado": self.ctx["ahora_utc"].isoformat(), "pestanas": out}, ensure_ascii=False,
                          separators=(",", ":"))

    # ------------------------------------------------------------ página
    def html(self, prefijo="", archivo=False):
        c = self.ctx
        titulo = (self.cfg.get("pagina", {}) or {}).get("titulo", "Noticias Diarias")
        repo = (self.cfg.get("pagina", {}) or {}).get("repositorio", "")
        visibles = [(k, ic, t) for k, ic, t in PESTANAS if self.tiene_contenido(k, archivo)]   # nunca una pestaña vacía
        tabs = "".join(f'<button type="button" class="tab{" on" if i == 0 else ""}" data-tab="{k}" role="tab" '
                       f'aria-selected="{"true" if i == 0 else "false"}">{ic} {t}<span class="bd" data-bd="{k}"></span></button>'
                       for i, (k, ic, t) in enumerate(visibles))
        paneles = "".join(self.panel(k, ic, t, prefijo, archivo, i == 0) for i, (k, ic, t) in enumerate(visibles))
        paneles += self.panel_guardadas()
        meta = {"ids": {} if archivo else {k: [n.id for n in v] for k, v in c["ver_mas"].items()},
                "dest": {k: self.contenido(k, prefijo)[3] for k, _, _ in visibles},
                "mas": "" if archivo else f"{prefijo}mas.json"}
        k = c["contador"]
        contador = (f'<p>Revisamos <b>{k["revisados"]}</b> titulares. Destacadas: <b>{k["entraron"]}</b>; en "Ver más": <b>{k["ver_mas"]}</b>.<br>'
                    f'Descartadas por contenido sexual: <b>{k["sexual"]}</b> · sensacionalismo (fuera de destacadas): <b>{k["sensacionalismo"]}</b> · '
                    f'publicidad: <b>{k["publicidad"]}</b> · baja importancia: <b>{k["baja_importancia"]}</b> · duplicados agrupados: <b>{k["duplicados"]}</b>.</p>')
        dias = "".join(f'<li><a href="{prefijo}archivo/{d}.html">{e(t)}</a></li>' for d, t in c["archivo"])
        iconos = (f'<link rel="apple-touch-icon" href="{prefijo}icono-180.png">'
                  f'<link rel="manifest" href="{prefijo}manifest.webmanifest">') if c.get("iconos") else ""
        favicon = f"{prefijo}logo.png" if c.get("logo_png") else FAVICON
        aviso_archivo = (f'<p class="nota">Edición archivada. <a href="{prefijo}index.html">Ir a la edición de hoy</a></p>'
                         if archivo else "")
        filtro_link = (f'<a href="{e(repo)}/blob/main/FILTRO.md" target="_blank" rel="noopener noreferrer">Cómo funciona el filtro</a>'
                       if repo else "")
        return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<meta name="referrer" content="no-referrer">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#F3F5F8" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#0B0F14" media="(prefers-color-scheme: dark)">
<title>{e(titulo)} · {e(c["fecha_corta"])}</title>
<link rel="icon" href="{favicon}">{iconos}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FUENTES_GOOGLE}">
<style>{CSS}{self.css_bordes()}</style>
</head>
<body>
{simbolos(c["colores"])}
<header class="cab">
  <div class="cab-t"><p class="fecha">{e(c["fecha_larga"]).upper()} · ACTUALIZADO {e(c["hora"])}</p><h1>{e(titulo)}</h1></div>
  <div class="cab-b">
    <button type="button" class="ic-b" disabled aria-disabled="true" title="Buscar (llega en la Fase 2)" aria-label="Buscar (próximamente)">{ICONO_BUSCAR}</button>
    <button type="button" class="ic-b escudo" id="escudo" title="Filtro de contenido activo" aria-label="Filtro de contenido activo">{ICONO_ESCUDO}</button>
  </div>
</header>
<nav class="tabs" role="tablist" aria-label="Pestañas">{tabs}</nav>
<div class="modo" role="group" aria-label="Modo de lectura">
  <button type="button" class="md" data-modo="rapido" aria-pressed="false">⚡ Rápido · 2 min</button>
  <button type="button" class="md on" data-modo="completo" aria-pressed="true">📚 Completo</button>
</div>
<main>
{aviso_archivo}
{paneles}
</main>
<nav class="barra" aria-label="Navegación">
  <button type="button" data-ir="hoy">{ICONO_INICIO}<span>Inicio</span></button>
  <button type="button" data-ir="guardado">{ICONO_GUARDAR}<span>Guardadas</span></button>
  <button type="button" data-ir="ajustes">{ICONO_AJUSTES}<span>Ajustes</span></button>
</nav>
<dialog id="d-menu" aria-label="Opciones de la noticia"><form method="dialog">
  <p class="dm-t" id="dm-t"></p>
  <button type="button" data-acc="guardar">🔖 <span id="dm-g">Guardar</span></button>
  <button type="button" data-acc="compartir">📤 Compartir</button>
  <button type="button" data-acc="ocultar">🙈 Ocultar esta noticia</button>
  <button type="button" data-acc="bloquear">⛔ Bloquear el medio <b id="dm-src"></b></button>
  <div class="dm-p"><input id="dm-pal" type="text" placeholder="Bloquear una palabra…" aria-label="Palabra a bloquear"><button type="button" data-acc="palabra">Bloquear</button></div>
  <button value="cerrar" class="cerrar">Cerrar</button>
</form></dialog>
<dialog id="d-ajustes" aria-label="Ajustes"><form method="dialog">
  <h2>Ajustes</h2>
  <div class="aj"><span>Tamaño de letra</span><div><button type="button" data-letra="-1" aria-label="Letra más pequeña">A-</button><button type="button" data-letra="1" aria-label="Letra más grande">A+</button></div></div>
  <div class="aj"><span>Modo oscuro</span><small>Automático, según tu celular</small></div>
  <h3>Medios bloqueados</h3><ul id="aj-medios" class="aj-l"></ul>
  <h3>Palabras bloqueadas</h3><ul id="aj-palabras" class="aj-l"></ul>
  <div class="dm-p"><input id="aj-pal" type="text" placeholder="Nueva palabra a bloquear" aria-label="Nueva palabra a bloquear"><button type="button" id="aj-pal-b">Agregar</button></div>
  <div class="aj"><span>Noticias ocultas: <b id="aj-ocultas">0</b></span><button type="button" id="aj-mostrar">Mostrar</button></div>
  <div class="aj"><span>Historial de leídas</span><button type="button" id="aj-leidas">Borrar</button></div>
  <h3>🛡️ Filtro de hoy</h3>{contador}<p class="nota">{filtro_link}</p>
  <h3>📡 Estado de las fuentes</h3>{self.estado_fuentes()}
  <h3>Días anteriores</h3><ul class="aj-l">{dias or "<li>Aún no hay.</li>"}</ul>
  <button value="cerrar" class="cerrar">Cerrar</button>
</form></dialog>
<div class="toast" id="toast" role="status" aria-live="polite"></div>
<script type="application/json" id="meta">{json.dumps(meta, separators=(",", ":"))}</script>
<script>{JS}</script>
</body>
</html>"""

    def css_bordes(self):
        b = self.cfg.get("bordes_tema", {}) or {}
        if not b.get("activo", True):
            return ""
        g = float(b.get("grosor", 1.5))
        return (f":root{{--bw:{g}px;--bo:{int(b.get('opacidad_claro', 55))}%;--bod:{int(b.get('destacada_claro', 70))}%}}"
                f"@media (prefers-color-scheme:dark){{:root{{--bo:{int(b.get('opacidad_oscuro', 45))}%;--bod:{int(b.get('destacada_oscuro', 60))}%}}}}"
                ".card,.fila-m{border:var(--bw) solid color-mix(in srgb,var(--c,transparent) var(--bo),transparent)}"
                ".card.grande{border-color:color-mix(in srgb,var(--c,transparent) var(--bod),transparent)}")


def _svg(d):
    return (f'<svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{d}</svg>')


ICONO_GUARDAR = _svg('<path d="M6 3h12v18l-6-4-6 4z"/>')
ICONO_COMPARTIR = _svg('<path d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M16 6l-4-4-4 4M12 2v13"/>')
ICONO_OCULTAR = _svg('<path d="M3 3l18 18M10.6 10.6a2 2 0 0 0 2.8 2.8M9.9 5.1A9.8 9.8 0 0 1 12 5c5 0 9 5 10 7a13 13 0 0 1-3 3.9M6.6 6.6A13 13 0 0 0 2 12c1 2 5 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/>')
ICONO_BUSCAR = _svg('<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>')
ICONO_ESCUDO = _svg('<path d="M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>')
ICONO_INICIO = _svg('<path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1z"/>')
ICONO_AJUSTES = _svg('<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>')
ICONO_IG = _svg('<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".8" fill="currentColor"/>')

CSS = """
:root{--bg:#F3F5F8;--card:#fff;--tx:#0F1720;--mu:#56606E;--ln:#E3E7EE;--chip:#E9EDF3;--act:#0F1720;--acttx:#fff;
--ok:#15803D;--up:#15803D;--down:#B42318;--sh:0 1px 2px rgba(15,23,32,.05),0 4px 14px rgba(15,23,32,.06);--fs:16px;--k:1;
--serif:"Source Serif 4",Georgia,"Times New Roman",serif;--sans:"DM Sans",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#0B0F14;--card:#151B23;--tx:#E8EDF3;--mu:#A3ADBA;--ln:#26303B;--chip:#1F2731;
--act:#E8EDF3;--acttx:#0B0F14;--ok:#4ADE80;--up:#4ADE80;--down:#F87171;--sh:none}}
*{box-sizing:border-box}
html{font-size:var(--fs);-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--tx);font:1rem/1.45 var(--sans);overflow-x:hidden;padding-bottom:84px}
a{color:inherit}
button{font:inherit;color:inherit}
[hidden]{display:none!important}
.cab,.tabs,.modo,main{max-width:640px;margin:0 auto}
.cab{display:flex;align-items:flex-end;gap:8px;padding:18px 16px 8px}
.cab-t{flex:1;min-width:0}
.fecha{margin:0;font-size:.7rem;letter-spacing:.08em;color:var(--mu);font-weight:500}
.cab h1{margin:2px 0 0;font:700 1.75rem/1.1 var(--serif);letter-spacing:-.01em}
.cab-b{display:flex;gap:4px}
.ic-b{width:44px;height:44px;border:0;border-radius:50%;background:transparent;display:grid;place-items:center;cursor:pointer}
.ic-b:disabled{opacity:.4;cursor:default}
.escudo{color:var(--ok);background:color-mix(in srgb,var(--ok) 13%,transparent)}
.tabs{position:sticky;top:0;z-index:10;display:flex;gap:8px;overflow-x:auto;padding:8px 16px;background:var(--bg);scrollbar-width:none;-webkit-overflow-scrolling:touch}
.tabs::-webkit-scrollbar{display:none}
.tab{flex:none;height:44px;padding:0 16px;border:0;border-radius:999px;background:var(--card);box-shadow:var(--sh);font-weight:500;font-size:.95rem;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;gap:4px}
.tab.on{background:var(--act);color:var(--acttx)}
.bd:not(:empty){margin-left:4px;min-width:20px;height:20px;padding:0 6px;border-radius:999px;background:#C2410C;color:#fff;font-size:.7rem;font-weight:700;display:inline-grid;place-items:center}
.modo{display:flex;gap:6px;padding:4px 16px 0}
.md{flex:1;min-height:44px;border:1px solid var(--ln);background:transparent;border-radius:12px;font-size:.88rem;cursor:pointer}
.md.on{background:var(--card);border-color:var(--tx);font-weight:700}
main{padding:0 16px}
.ph{margin:14px 0 8px;padding:12px 2px 2px}
.ph h2{margin:0;font:700 1.35rem/1.2 var(--serif)}
.ph.grad{padding:16px 16px 14px;border-radius:18px;color:#fff}
.nuevas{margin:2px 0 0;font-size:.82rem;color:var(--mu)}
.ph.grad .nuevas{color:rgba(255,255,255,.9)}
.subs{display:flex;gap:6px;overflow-x:auto;padding:4px 0 10px;scrollbar-width:none}
.subs::-webkit-scrollbar{display:none}
.sf{flex:none;min-height:44px;padding:0 14px;border:1px solid var(--ln);border-radius:999px;background:var(--card);font-size:.88rem;cursor:pointer;white-space:nowrap}
.sf.on{background:var(--act);color:var(--acttx);border-color:var(--act)}
.card{position:relative;background:var(--card);border-radius:18px;box-shadow:var(--sh);margin-bottom:10px}
.grande{overflow:hidden}
.th16{position:relative;aspect-ratio:16/9;background:var(--chip)}
.th76{position:relative;flex:none;width:76px;height:76px;border-radius:12px;overflow:hidden;background:var(--chip)}
.ilu,.foto{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;display:block}
.play{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:48px;height:48px;border-radius:50%;background:rgba(0,0,0,.6);color:#fff;display:grid;place-items:center;text-decoration:none;z-index:2}
.cu{padding:14px 16px;min-width:0;flex:1}
.comp{display:flex;gap:12px;padding:14px;align-items:flex-start}
.comp .cu{padding:0}
.fila-chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.chip-t{display:inline-block;font-size:.72rem;font-weight:700;letter-spacing:.02em;color:color-mix(in srgb,var(--c) 82%,#000);background:color-mix(in srgb,var(--c) 13%,transparent);border-radius:999px;padding:3px 9px}
@media (prefers-color-scheme:dark){.chip-t{color:color-mix(in srgb,var(--c) 55%,#fff)}}
.ins{font-size:.7rem;font-weight:700;border-radius:6px;padding:2px 7px;background:var(--chip)}
.ins.pat,.ins.sen{background:#FEF3C7;color:#7A4A00}
@media (prefers-color-scheme:dark){.ins.pat,.ins.sen{background:#3D2E00;color:#FCD34D}}
.tit-g{margin:8px 0 0;font:700 calc(21px * var(--k))/1.25 var(--serif)}
.tit-c{margin:6px 0 0;font:600 calc(15px * var(--k))/1.3 var(--serif);overflow-wrap:anywhere}
.lk{text-decoration:none}
.lk:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid #3A5BA8;outline-offset:2px}
.res{margin:6px 0 0;color:var(--mu);font-size:.9rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.pq{margin:8px 0 0;font-size:.88rem;padding:8px 10px;border-radius:10px;background:var(--chip)}
.meta{margin:6px 0 0;font-size:.8rem;color:var(--mu)}
.src{font-weight:500;color:var(--tx)}
.pie{display:flex;align-items:center;justify-content:space-between;gap:6px}
.b-menu.mini{flex:none;width:44px;height:44px;margin:-8px -10px -8px 0;border:0;border-radius:50%;background:transparent;font-size:1.3rem;color:var(--mu);cursor:pointer}
.acc{display:flex;gap:6px;margin-top:10px}
.acc button{flex:1;min-width:0;min-height:44px;border:1px solid var(--ln);border-radius:12px;background:transparent;display:inline-flex;align-items:center;justify-content:center;gap:6px;font-size:.85rem;cursor:pointer}
.acc button.on{background:var(--act);color:var(--acttx);border-color:var(--act)}
.cob{margin-top:6px;font-size:.82rem}
.cob summary{cursor:pointer;min-height:36px;display:inline-flex;align-items:center;font-weight:700;color:#1D5FA3}
@media (prefers-color-scheme:dark){.cob summary{color:#93B4E6}}
.cob ul{margin:4px 0 0;padding-left:18px}.cob li{margin:6px 0}
.leida{opacity:.55}
.mercados{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:4px 0 10px}
.mk{background:var(--card);border-radius:16px;padding:12px;box-shadow:var(--sh);min-width:0}
.mk-n{font-size:.75rem;color:var(--mu)}.mk-v{font-weight:700;font-size:1.05rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mk-v small{font-size:.65rem;color:var(--mu);font-weight:500}.mk-c{font-size:.8rem;font-weight:700}
.mk.up .mk-c,.mk.up .spark{color:var(--up)}.mk.down .mk-c,.mk.down .spark{color:var(--down)}.mk.flat .spark{color:var(--mu)}
.spark{display:block;width:100%;height:30px;margin-top:4px}
.bloque{background:var(--card);border-radius:18px;box-shadow:var(--sh);padding:12px 16px;margin:4px 0 12px}
.bt{margin:12px 0 8px;font:700 1.05rem/1.3 var(--serif)}
.bloque .bt{margin-top:2px}
.lista-s{list-style:none;margin:0;padding:0}
.lista-s li{display:flex;gap:10px;align-items:flex-start;padding:9px 0;border-top:1px solid var(--ln);font-size:.9rem}
.lista-s li.lh{border-top:0;font-size:.72rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--mu);padding-bottom:0}
.hr{flex:none;width:52px;font-weight:700;font-variant-numeric:tabular-nums}
.tx{flex:1;min-width:0;overflow-wrap:anywhere}.tx a{text-decoration:none}
.alma{padding:14px 16px}.alma .txt{margin:8px 0 0;font-size:.95rem;line-height:1.55}
.preg{margin:10px 0 0;font-style:italic;font-size:.92rem}
.video{overflow:hidden}
.vb{display:flex;gap:12px;align-items:center;padding:14px;text-decoration:none;background:linear-gradient(135deg,#7C2A0A,#C25E14);color:#fff;min-height:76px}
.pl{flex:none;width:48px;height:48px;border-radius:50%;background:rgba(255,255,255,.2);display:grid;place-items:center;font-size:1.2rem}
.vt{font:600 calc(15px * var(--k))/1.3 var(--serif);overflow-wrap:anywhere}
.video .pie{padding:4px 14px 8px}
.igs{display:flex;flex-wrap:wrap;gap:8px}
.ig{display:inline-flex;align-items:center;gap:6px;min-height:44px;padding:0 14px;border-radius:999px;color:#fff;text-decoration:none;font-weight:700;font-size:.88rem;background:linear-gradient(45deg,#c2410c,#be185d 55%,#6d28d9)}
.vermas{display:block;width:100%;min-height:48px;margin:8px 0;border:0;border-radius:14px;background:var(--act);color:var(--acttx);font-weight:700;font-size:.95rem;cursor:pointer}
.fila-m{background:var(--card);border-radius:14px;padding:10px 12px;margin-bottom:8px}
.fila-m .tit-c{margin-top:4px}
.aviso{padding:16px;border-radius:16px;background:var(--card);color:var(--mu);font-size:.92rem}
.aldia{text-align:center;color:var(--mu);font-size:.88rem;margin:18px 0 8px}
.nota{font-size:.78rem;color:var(--mu);margin:6px 2px}
body.rapido .vermas,body.rapido .masl,body.rapido .res,body.rapido .bloque{display:none}
body.rapido #p-hoy .lista>.card:nth-child(n+11){display:none}
.barra{position:fixed;left:0;right:0;bottom:0;z-index:20;display:flex;justify-content:center;gap:4px;padding:6px 8px calc(6px + env(safe-area-inset-bottom));background:color-mix(in srgb,var(--bg) 94%,transparent);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-top:1px solid var(--ln)}
.barra button{flex:1;max-width:200px;min-height:56px;border:0;background:transparent;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:.75rem;font-weight:500;cursor:pointer;border-radius:12px}
.barra button.on{color:#C2410C}
@media (prefers-color-scheme:dark){.barra button.on{color:#FB923C}}
dialog{border:0;border-radius:20px;padding:0;width:min(92vw,440px);max-height:86vh;background:var(--card);color:var(--tx);box-shadow:0 20px 60px rgba(0,0,0,.3)}
dialog::backdrop{background:rgba(0,0,0,.45)}
dialog form{padding:16px;display:flex;flex-direction:column;gap:6px}
dialog h2{margin:0 0 4px;font:700 1.3rem var(--serif)}dialog h3{margin:12px 0 2px;font-size:.95rem}
dialog button{min-height:44px;border:1px solid var(--ln);border-radius:12px;background:transparent;text-align:left;padding:0 14px;cursor:pointer}
.dm-t{margin:0 0 6px;font:600 1rem/1.3 var(--serif)}
.dm-p{display:flex;gap:6px}.dm-p input{flex:1;min-width:0;min-height:44px;border:1px solid var(--ln);border-radius:12px;padding:0 12px;background:var(--bg);color:var(--tx);font:inherit}
.cerrar{text-align:center!important;font-weight:700;background:var(--act)!important;color:var(--acttx)}
.aj{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:44px}
.aj div{display:flex;gap:6px}.aj button{text-align:center;min-width:56px}
.aj-l{margin:0;padding-left:18px;font-size:.9rem}.aj-l li{margin:4px 0}.aj-l button{min-height:36px;margin-left:6px;padding:0 10px}
.toast{position:fixed;left:50%;bottom:96px;transform:translateX(-50%);max-width:90vw;background:#0F1720;color:#fff;padding:10px 16px;border-radius:12px;font-size:.88rem;opacity:0;pointer-events:none;transition:opacity .2s;z-index:30}
.toast.on{opacity:1}
body.en-videos{background:#0B0F14;color:#E8EDF3}
body.en-videos .cab,body.en-videos .modo{display:none}
body.en-videos .tabs{background:#0B0F14}
body.en-videos .tab:not(.on){background:#1A212B;color:#E8EDF3;box-shadow:none}
.videos-p .subs{padding-top:2px}.videos-p .sf{background:#1A212B;color:#E8EDF3;border-color:#2A3340}.videos-p .sf.on{background:#E8EDF3;color:#0B0F14}
.vtop{display:flex;align-items:center;justify-content:space-between;gap:8px;margin:0 0 6px}
.vcont{margin:0;font-size:.8rem;color:#A3ADBA}
.vsonido{min-height:40px;border:1px solid #2A3340;border-radius:999px;background:#1A212B;color:#E8EDF3;padding:0 14px;font-size:.85rem;cursor:pointer}
.vfeed{height:calc(100dvh - 228px);min-height:420px;overflow-y:auto;scroll-snap-type:y mandatory;overscroll-behavior:contain;border-radius:18px;background:#0B0F14;scrollbar-width:none}
.vfeed::-webkit-scrollbar{display:none}
.vs{position:relative;height:100%;scroll-snap-align:start;scroll-snap-stop:always;background:#000;border-radius:18px;overflow:hidden;margin-bottom:6px}
.vplayer,.vplayer iframe{position:absolute;inset:0;width:100%;height:100%;border:0}
.vtap{position:absolute;inset:0 76px 150px 0;display:grid;place-items:center;cursor:pointer;z-index:2}
.vpl{width:64px;height:64px;border-radius:50%;background:rgba(0,0,0,.55);color:#fff;display:grid;place-items:center;font-size:1.6rem;opacity:0;transition:opacity .2s}
.vs.pausado .vpl,.vs:not(.cargado) .vpl{opacity:1}
.vinfo{position:absolute;left:0;right:76px;bottom:0;z-index:3;padding:40px 14px 14px;background:linear-gradient(transparent,rgba(0,0,0,.85));color:#fff;pointer-events:none}
.vchip{font-size:.72rem;font-weight:700;border-radius:999px;padding:3px 9px;background:rgba(255,255,255,.16)}.vchip.ok{background:#15803D}
.vtit{margin:8px 0 2px;font:600 1.05rem/1.3 var(--serif);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.vcan{margin:0;font-size:.82rem;color:#D0D6DE}
.vacc{position:absolute;right:6px;bottom:18px;z-index:4;display:flex;flex-direction:column;gap:10px}
.vacc button{width:64px;min-height:64px;border:0;border-radius:16px;background:rgba(20,26,34,.75);color:#fff;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font-size:.66rem;cursor:pointer;padding:6px 2px;line-height:1.1}
.vacc button.on{background:#E8EDF3;color:#0B0F14}
.vfin{display:flex!important;flex-direction:column;align-items:center;justify-content:center;gap:6px;color:#E8EDF3;background:#111821}
.vfin p{font:700 1.2rem var(--serif);margin:0}
.franja{display:flex;gap:8px;overflow-x:auto;padding:2px 0 8px;scrollbar-width:none}.franja::-webkit-scrollbar{display:none}
.res-p{flex:none;min-width:150px;max-width:190px;background:var(--card);border-radius:14px;box-shadow:var(--sh);padding:10px 12px;text-decoration:none;display:flex;flex-direction:column;gap:3px;font-size:.85rem}
.rl{font-size:.7rem;color:var(--mu);font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.re{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.re b{display:inline-block;min-width:18px}
.tabla{background:var(--card);border-radius:14px;box-shadow:var(--sh);margin:0 0 8px;padding:0 12px}
.tabla summary{min-height:44px;display:flex;align-items:center;cursor:pointer;font-weight:700;font-size:.9rem}
.tabla table{width:100%;border-collapse:collapse;font-size:.85rem;margin-bottom:4px}
.tabla th,.tabla td{text-align:left;padding:5px 4px;border-top:1px solid var(--ln)}.tabla td:nth-child(n+3),.tabla th:nth-child(n+3){text-align:right}
"""

JS = r"""
(function(){
var M=JSON.parse(document.getElementById('meta').textContent);
function ld(k,d){try{var v=localStorage.getItem('nd_'+k);return v?JSON.parse(v):d}catch(e){return d}}
function sv(k,v){try{localStorage.setItem('nd_'+k,JSON.stringify(v))}catch(e){}}
var S={leidas:ld('leidas',[]),guardadas:ld('guardadas',{}),ocultas:ld('ocultas',[]),medios:ld('medios',[]),palabras:ld('palabras',[]),letra:ld('letra',1),modo:ld('modo','completo')};
function norm(t){return (t||'').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')}
var toastEl=document.getElementById('toast');
function aviso(m){toastEl.textContent=m;toastEl.classList.add('on');clearTimeout(aviso.t);aviso.t=setTimeout(function(){toastEl.classList.remove('on')},2400)}
function rel(h){if(!h)return'';var s=Math.max(0,Date.now()/1000-h);return s<3600?Math.max(1,Math.floor(s/60))+' min':s<86400?Math.floor(s/3600)+' h':Math.floor(s/86400)+' d'}
function esc(t){return String(t==null?'':t).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function aplicarLetra(){document.documentElement.style.setProperty('--fs',(16*S.letra).toFixed(1)+'px');document.documentElement.style.setProperty('--k',S.letra)}
function aplicarModo(){document.body.classList.toggle('rapido',S.modo==='rapido');document.querySelectorAll('.md').forEach(function(b){var on=b.dataset.modo===S.modo;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on)})}
aplicarLetra();aplicarModo();
document.querySelectorAll('.md').forEach(function(b){b.onclick=function(){S.modo=b.dataset.modo;sv('modo',S.modo);aplicarModo()}});
document.querySelectorAll('[data-letra]').forEach(function(b){b.onclick=function(){S.letra=Math.round(Math.min(1.4,Math.max(.85,S.letra+(+b.dataset.letra)*.1))*100)/100;sv('letra',S.letra);aplicarLetra()}});
function bloqueada(el){var src=norm(el.dataset.src),dom=norm(el.dataset.dom),t=norm(el.dataset.t);
 if(S.ocultas.indexOf(el.dataset.id)>=0)return true;
 for(var i=0;i<S.medios.length;i++){var m=norm(S.medios[i]);if(m&&(m===src||m===dom))return true}
 for(var j=0;j<S.palabras.length;j++){var p=norm(S.palabras[j]).trim();if(p&&t.indexOf(p)>=0)return true}return false}
function refrescar(){
 document.querySelectorAll('.it').forEach(function(el){el.hidden=bloqueada(el);el.classList.toggle('leida',S.leidas.indexOf(el.dataset.id)>=0);
  var g=el.querySelector('.b-guardar');if(g){var on=!!S.guardadas[el.dataset.id];g.classList.toggle('on',on);g.querySelector('span').textContent=on?'Guardada':'Guardar'}});
 document.querySelectorAll('time[data-h]').forEach(function(t){t.textContent=rel(+t.dataset.h)});
 contar();aplicarSub();pintarGuardadas();pintarAjustes()}
function contar(){document.querySelectorAll('.tab').forEach(function(tb){var k=tb.dataset.tab,ids=((M.dest||{})[k]||[]).concat((M.ids||{})[k]||[]),vistos={},n=0;
 ids.forEach(function(id){if(!vistos[id]&&S.leidas.indexOf(id)<0&&S.ocultas.indexOf(id)<0)n++;vistos[id]=1});
 if(k==='guardado')n=0;tb.querySelector('.bd').textContent=n?n:'';
 var p=document.querySelector('#p-'+k+' [data-nuevas]');if(p)p.textContent=n?n+' nuevas':(ids.length?'Todo leído':'')});var ng=Object.keys(S.guardadas).length,pg=document.querySelector('#p-guardado [data-nuevas]');if(pg)pg.textContent=ng===1?'1 guardada':ng+' guardadas'}
function irA(k,arriba){if(k==='ajustes'){abrirAjustes();return}if(k!=='videos')videosSalir();
 document.querySelectorAll('.tab').forEach(function(b){var on=b.dataset.tab===k;b.classList.toggle('on',on);b.setAttribute('aria-selected',on);if(on&&b.scrollIntoView)b.scrollIntoView({inline:'center',block:'nearest'})});
 document.querySelectorAll('.panel').forEach(function(p){p.hidden=p.dataset.tab!==k});
 document.querySelectorAll('.barra button').forEach(function(b){b.classList.toggle('on',b.dataset.ir===k)});
 try{history.replaceState(null,'','#'+k)}catch(e){}if(arriba!==false)window.scrollTo(0,0);if(k==='videos')setTimeout(videosEntrar,50)}
document.querySelectorAll('.tab').forEach(function(b){b.onclick=function(){irA(b.dataset.tab)}});
document.querySelectorAll('.barra button').forEach(function(b){b.onclick=function(){irA(b.dataset.ir)}});
var subs={};
function aplicarSub(){document.querySelectorAll('.panel').forEach(function(p){var s=subs[p.dataset.tab]||'todo';
 p.querySelectorAll('[data-sub]').forEach(function(el){var ok=s==='todo'||(' '+el.dataset.sub+' ').indexOf(' '+s+' ')>=0;el.style.display=ok?'':'none'})})}
document.querySelectorAll('.sf').forEach(function(b){b.onclick=function(){var p=b.closest('.panel');subs[p.dataset.tab]=b.dataset.sf;
 p.querySelectorAll('.sf').forEach(function(x){var on=x===b;x.classList.toggle('on',on);x.setAttribute('aria-pressed',on)});aplicarSub();
 if(p.dataset.tab==='videos'){var f=document.getElementById('vfeed');f.scrollTop=0;var l=vSlides();if(l[0])vActivar(l[0])}}});
document.addEventListener('click',function(ev){var a=ev.target.closest('a.lk');if(!a)return;var it=a.closest('.it');
 if(it&&S.leidas.indexOf(it.dataset.id)<0){S.leidas.push(it.dataset.id);if(S.leidas.length>3000)S.leidas=S.leidas.slice(-3000);sv('leidas',S.leidas);setTimeout(refrescar,300)}});
var dm=document.getElementById('d-menu'),sel=null;
function datos(el){return{id:el.dataset.id,t:el.dataset.t,u:el.dataset.u,f:el.dataset.src,d:el.dataset.dom,h:+el.dataset.h,tm:el.dataset.tm,c:el.dataset.c}}
function guardar(el){var d=datos(el);if(S.guardadas[d.id]){delete S.guardadas[d.id];aviso('Quitada de guardadas')}else{S.guardadas[d.id]=d;aviso('Guardada')}sv('guardadas',S.guardadas);refrescar()}
function compartir(el){var u=el.dataset.u,t=el.dataset.t;if(navigator.share){navigator.share({title:t,url:u}).catch(function(){})}else if(navigator.clipboard){navigator.clipboard.writeText(u).then(function(){aviso('Enlace copiado')})}}
document.addEventListener('click',function(ev){var b=ev.target.closest('.b-guardar,.b-compartir,.b-menu');if(!b)return;var el=b.closest('.it');if(!el)return;
 if(b.classList.contains('b-guardar'))return guardar(el);if(b.classList.contains('b-compartir'))return compartir(el);
 sel=el;document.getElementById('dm-t').textContent=el.dataset.t;document.getElementById('dm-src').textContent=el.dataset.src;
 document.getElementById('dm-g').textContent=S.guardadas[el.dataset.id]?'Quitar de guardadas':'Guardar';document.getElementById('dm-pal').value='';
 if(dm.showModal)dm.showModal()});
dm.addEventListener('click',function(ev){var b=ev.target.closest('[data-acc]');if(!b||!sel)return;var a=b.dataset.acc;
 if(a==='guardar')guardar(sel);else if(a==='compartir')compartir(sel);
 else if(a==='ocultar'){S.ocultas.push(sel.dataset.id);sv('ocultas',S.ocultas);aviso('Noticia oculta')}
 else if(a==='bloquear'){if(S.medios.indexOf(sel.dataset.src)<0)S.medios.push(sel.dataset.src);sv('medios',S.medios);aviso('Medio bloqueado: '+sel.dataset.src)}
 else if(a==='palabra'){var w=document.getElementById('dm-pal').value.trim();if(!w)return;S.palabras.push(w);sv('palabras',S.palabras);aviso('Palabra bloqueada: '+w)}
 dm.close();refrescar()});
var datosMas=null;
function filaMas(x){var sen=x.z?'<span class="ins sen">Posible sensacionalismo</span>':'';
 var cob=x.o?'<details class="cob"><summary>'+x.o.length+' medios cubren esto</summary><ul>'+x.o.map(function(o){return'<li><a href="'+esc(o[1])+'" target="_blank" rel="noopener noreferrer">'+esc(o[0])+'</a></li>'}).join('')+'</ul></details>':'';
 return'<article class="fila-m it" data-id="'+esc(x.id)+'" data-sub="'+esc((x.s||[]).join(' '))+'" data-src="'+esc(x.f)+'" data-dom="'+esc(x.d)+'" data-u="'+esc(x.u)+'" data-t="'+esc(x.t)+'" data-tm="'+esc(x.tm)+'" data-c="'+esc(x.c)+'" data-h="'+(+x.h)+'" style="--c:'+esc(x.c)+'">'
 +'<div class="fila-chips"><span class="chip-t">'+esc(x.tm)+'</span>'+sen+'</div><h3 class="tit-c"><a class="lk" href="'+esc(x.u)+'" target="_blank" rel="noopener noreferrer">'+esc(x.t)+'</a></h3>'
 +'<div class="pie"><p class="meta"><span class="src">'+esc(x.f)+'</span> · <time data-h="'+(+x.h)+'"></time></p><button type="button" class="b-menu mini" aria-label="Opciones">⋯</button></div>'+cob+'</article>'}
document.querySelectorAll('.vermas').forEach(function(b){b.onclick=function(){var k=b.dataset.tab,cont=document.getElementById('mas-'+k);
 function pintar(){cont.innerHTML=(datosMas.pestanas[k]||[]).map(filaMas).join('');b.hidden=true;refrescar()}
 if(datosMas)return pintar();b.textContent='Cargando…';
 fetch(M.mas,{cache:'no-cache'}).then(function(r){return r.json()}).then(function(d){datosMas=d;pintar()}).catch(function(){b.textContent='No se pudo cargar. Toca para reintentar'})}});
function pintarGuardadas(){var c=document.getElementById('lista-guardadas');if(!c)return;var l=Object.keys(S.guardadas).map(function(k){return S.guardadas[k]}).sort(function(a,b){return b.h-a.h});
 c.innerHTML=l.length?l.map(function(x){return'<article class="fila-m it" data-id="'+esc(x.id)+'" data-sub="" data-src="'+esc(x.f)+'" data-dom="'+esc(x.d)+'" data-u="'+esc(x.u)+'" data-t="'+esc(x.t)+'" data-tm="'+esc(x.tm)+'" data-c="'+esc(x.c)+'" data-h="'+(+x.h)+'" style="--c:'+esc(x.c)+'"><div class="fila-chips"><span class="chip-t">'+esc(x.tm)+'</span></div><h3 class="tit-c"><a class="lk" href="'+esc(x.u)+'" target="_blank" rel="noopener noreferrer">'+esc(x.t)+'</a></h3><div class="pie"><p class="meta"><span class="src">'+esc(x.f)+'</span> · '+rel(x.h)+'</p><button type="button" class="b-menu mini" aria-label="Opciones">⋯</button></div></article>'}).join('')
 :'<p class="aviso">Aún no tienes noticias guardadas. Toca 🔖 Guardar en cualquier noticia.</p>';
 c.querySelectorAll('.it').forEach(function(el){el.classList.toggle('leida',S.leidas.indexOf(el.dataset.id)>=0)})}
var da=document.getElementById('d-ajustes');
function pintarAjustes(){function lista(id,arr,clave){var ul=document.getElementById(id);ul.innerHTML=arr.length?arr.map(function(x,i){return'<li>'+esc(x)+'<button type="button" data-quitar="'+clave+'" data-i="'+i+'">Desbloquear</button></li>'}).join(''):'<li>Ninguno</li>'}
 lista('aj-medios',S.medios,'medios');lista('aj-palabras',S.palabras,'palabras');document.getElementById('aj-ocultas').textContent=S.ocultas.length}
function abrirAjustes(){pintarAjustes();if(da.showModal)da.showModal()}
da.addEventListener('click',function(ev){var q=ev.target.closest('[data-quitar]');if(q){S[q.dataset.quitar].splice(+q.dataset.i,1);sv(q.dataset.quitar,S[q.dataset.quitar]);refrescar()}});
document.getElementById('aj-pal-b').onclick=function(){var i=document.getElementById('aj-pal'),w=i.value.trim();if(w){S.palabras.push(w);sv('palabras',S.palabras);i.value='';refrescar()}};
document.getElementById('aj-mostrar').onclick=function(){S.ocultas=[];sv('ocultas',[]);refrescar();aviso('Noticias ocultas visibles de nuevo')};
document.getElementById('aj-leidas').onclick=function(){S.leidas=[];sv('leidas',[]);refrescar();aviso('Historial de leídas borrado')};
document.getElementById('escudo').onclick=function(){aviso('Filtro de contenido activo: medios aprobados, lista de palabras, revisión con IA, imágenes controladas y tus bloqueos.')};
// --- Videos: un video por pantalla, arranca sin sonido, solo se cargan el actual y el siguiente
var V={players:{},cola:null,sonido:ld('sonido',false),actual:null,obs:null};
function cargarAPI(cb){if(window.YT&&YT.Player)return cb();if(!V.cola){V.cola=[];var sc=document.createElement('script');sc.src='https://www.youtube.com/iframe_api';document.head.appendChild(sc);
 window.onYouTubeIframeAPIReady=function(){var c=V.cola;V.cola=[];c.forEach(function(f){f()})}}V.cola.push(cb)}
function vSlides(){return Array.prototype.filter.call(document.querySelectorAll('#vfeed .vs[data-vid]'),function(x){return !x.hidden&&x.style.display!=='none'})}
function vCrear(sl){if(V.players[sl.dataset.id])return;var d=document.createElement('div');sl.querySelector('.vplayer').appendChild(d);
 V.players[sl.dataset.id]=new YT.Player(d,{host:'https://www.youtube-nocookie.com',videoId:sl.dataset.vid,width:'100%',height:'100%',
  playerVars:{autoplay:0,mute:1,playsinline:1,rel:0,controls:0,modestbranding:1,iv_load_policy:3},
  events:{onReady:function(ev){sl.classList.add('cargado');if(V.actual===sl){if(V.sonido)ev.target.unMute();else ev.target.mute();ev.target.playVideo()}},
   onStateChange:function(ev){sl.classList.toggle('pausado',ev.data===2)}}})}
function vDestruir(id){var p=V.players[id];if(p){try{p.destroy()}catch(e){}delete V.players[id];var sl=document.querySelector('#vfeed .vs[data-id="'+id+'"]');if(sl){sl.classList.remove('cargado');sl.querySelector('.vplayer').innerHTML=''}}}
function vActivar(sl){var l=vSlides(),i=l.indexOf(sl);if(i<0)return;V.actual=sl;
 var guardar={};guardar[sl.dataset.id]=1;if(l[i+1])guardar[l[i+1].dataset.id]=1;
 Object.keys(V.players).forEach(function(id){if(!guardar[id])vDestruir(id)});
 cargarAPI(function(){if(V.actual!==sl)return;vCrear(sl);if(l[i+1])vCrear(l[i+1]);
  Object.keys(V.players).forEach(function(id){var p=V.players[id];try{if(id===sl.dataset.id){if(V.sonido)p.unMute();else p.mute();p.playVideo()}else p.pauseVideo()}catch(e){}})});
 var c=document.getElementById('vcont');if(c)c.textContent=(i+1)+' de '+l.length+' · tope por sesión'}
function vObservar(){if(V.obs||!window.IntersectionObserver)return;V.obs=new IntersectionObserver(function(es){es.forEach(function(en){
  if(en.isIntersecting&&en.intersectionRatio>.6&&document.body.classList.contains('en-videos')&&en.target.dataset.vid)vActivar(en.target)})},
  {root:document.getElementById('vfeed'),threshold:[.6,.9]});document.querySelectorAll('#vfeed .vs').forEach(function(x){V.obs.observe(x)})}
function videosEntrar(){if(!document.getElementById('vfeed'))return;document.body.classList.add('en-videos');vObservar();
 var f=document.getElementById('vfeed');f.scrollTop=0;var l=vSlides();if(l[0])vActivar(l[0])}
function videosSalir(){document.body.classList.remove('en-videos');V.actual=null;Object.keys(V.players).forEach(vDestruir)}
document.addEventListener('click',function(ev){var t=ev.target.closest('.vtap');if(!t)return;var sl=t.closest('.vs'),p=V.players[sl.dataset.id];if(!p||!p.getPlayerState)return;
 try{if(p.getPlayerState()===1)p.pauseVideo();else p.playVideo()}catch(e){}});
document.addEventListener('click',function(ev){var b=ev.target.closest('.b-bloquear');if(!b)return;var el=b.closest('.it');if(!el)return;
 if(S.medios.indexOf(el.dataset.src)<0)S.medios.push(el.dataset.src);sv('medios',S.medios);aviso('Canal bloqueado: '+el.dataset.src);refrescar();var l=vSlides();if(l[0])vActivar(l[0])});
var vs=document.getElementById('vsonido');function pintarSonido(){if(vs)vs.textContent=V.sonido?'🔊 Sonido activado':'🔇 Activar sonido'}pintarSonido();
if(vs)vs.onclick=function(){V.sonido=!V.sonido;sv('sonido',V.sonido);pintarSonido();var p=V.actual&&V.players[V.actual.dataset.id];if(p){try{if(V.sonido)p.unMute();else p.mute()}catch(e){}}};
refrescar();function desdeHash(){var h=(location.hash||'').slice(1);if(h&&document.getElementById('p-'+h))irA(h,false);else irA('hoy',false)}desdeHash();window.addEventListener('hashchange',desdeHash);
})();
"""
