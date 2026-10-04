"""Genera la página diaria de noticias.

Uso:  python generar.py            (genera sitio/index.html)
      python generar.py --sin-ia   (fuerza el modo de respaldo)
"""
import argparse
import re
import shutil
import sys
import traceback
from datetime import date, datetime, timedelta

from noticias import agenda, alma, cine, medios, mercados, notificar
from noticias import filtros as FL
from noticias import proceso as P
from noticias.fuentes import descargar_todas, fuentes_activas, filtrar_por_edad
from noticias.gemini import Gemini, GeminiError
from noticias.historial import Historial
from noticias.pagina import Pagina, fecha_larga
from noticias.utils import RAIZ, ahora_utc, cargar_config, zona

SITIO = RAIZ / "sitio"
LOGS = RAIZ / "data" / "logs"


def preparar_portada(cfg, reg):
    pc = cfg.get("portada_imagen", {}) or {}
    origen = RAIZ / pc.get("archivo", "assets/portada.jpg")
    destino = SITIO / "portada.jpg"
    if not pc.get("activo", True) or not origen.exists():
        destino.unlink(missing_ok=True)
        return ""
    if destino.exists() and destino.stat().st_mtime >= origen.stat().st_mtime and destino.stat().st_size < 150_000:
        return "portada.jpg"
    try:
        from PIL import Image
        img = Image.open(origen).convert("RGB")
        img.thumbnail((1200, 800))
        for calidad in (82, 72, 62, 52, 42, 35):
            img.save(destino, "JPEG", quality=calidad, optimize=True, progressive=True)
            if destino.stat().st_size < 150_000:
                break
            if calidad == 52:
                img.thumbnail((900, 600))
        return "portada.jpg"
    except Exception as ex:  # noqa: BLE001
        reg.info(f"Portada: no se pudo procesar ({ex}); se usa el color de respaldo")
        return ""


CORAL = (216, 90, 48)


def _icono(lado, logo=None):
    """Ícono cuadrado: el logo propio o el recuadro coral con una N blanca."""
    from PIL import Image, ImageDraw
    if logo is not None:
        return logo.convert("RGB").resize((lado, lado))
    k = lado / 100
    img = Image.new("RGB", (lado, lado), CORAL)      # lleno: los sistemas recortan sus propias esquinas
    d = ImageDraw.Draw(img)
    d.polygon([(30 * k, 74 * k), (30 * k, 26 * k), (40 * k, 26 * k), (60 * k, 57 * k), (60 * k, 26 * k),
               (70 * k, 26 * k), (70 * k, 74 * k), (60 * k, 74 * k), (40 * k, 43 * k), (40 * k, 74 * k)], fill="white")
    return img


def preparar_logo_e_iconos(cfg, reg):
    """Copia assets/logo.png si es válido y crea íconos y manifest para 'Añadir a pantalla de inicio'.
    Devuelve (usar_logo_png, hay_iconos)."""
    lc = cfg.get("logo", {}) or {}
    origen = RAIZ / lc.get("archivo", "assets/logo.png")
    logo = None
    (SITIO / "logo.png").unlink(missing_ok=True)
    if lc.get("activo", True) and origen.exists():
        try:
            from PIL import Image
            im = Image.open(origen)
            if origen.stat().st_size >= 50_000:
                reg.info("Logo: assets/logo.png pesa 50 KB o más; se usa el logo dibujado")
            elif abs(im.width - im.height) > 2:
                reg.info("Logo: assets/logo.png no es cuadrado; se usa el logo dibujado")
            else:
                logo = im
                shutil.copy2(origen, SITIO / "logo.png")
        except Exception as ex:  # noqa: BLE001
            reg.info(f"Logo: no se pudo leer assets/logo.png ({type(ex).__name__}); se usa el logo dibujado")
    try:
        for lado in (180, 192, 512):
            _icono(lado, logo).save(SITIO / f"icono-{lado}.png", optimize=True)
    except Exception as ex:  # noqa: BLE001
        reg.info(f"Íconos: no se pudieron crear ({type(ex).__name__})")
        return logo is not None, False
    titulo = (cfg.get("pagina", {}) or {}).get("titulo", "Noticias diarias")
    manifest = {"name": titulo, "short_name": "News", "start_url": "./", "scope": "./", "display": "browser",
                "background_color": "#17203A", "theme_color": "#17203A",
                "icons": [{"src": f"icono-{x}.png", "sizes": f"{x}x{x}", "type": "image/png", "purpose": "any"}
                          for x in (192, 512)]}
    import json
    (SITIO / "manifest.webmanifest").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return logo is not None, True


def imagenes_categoria():
    origen = RAIZ / "assets" / "categorias"
    destino = SITIO / "categorias"
    shutil.rmtree(destino, ignore_errors=True)
    mapa = {}
    if origen.exists():
        for f in sorted(origen.iterdir()):
            if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                destino.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, destino / f.name)
                mapa[f.stem] = f"categorias/{f.name}"
    return mapa


def botones_instagram(loc):
    """Hasta 6 botones activos con URL válida de perfil de Instagram (no se comprueba el perfil)."""
    out = []
    for b in loc.get("instagram") or []:
        if isinstance(b, str):
            b = {"url": b, "activo": True}
        url = str(b.get("url") or "").strip()
        if not b.get("activo", True) or not re.match(r"^https://(www\.)?instagram\.com/[A-Za-z0-9._]{1,30}/?$", url):
            continue
        nombre = b.get("nombre") or "@" + url.rstrip("/").rsplit("/", 1)[-1]
        out.append({"nombre": nombre, "url": url})
    return out[:6]


def guardar_log(hoy, reg, errores):
    LOGS.mkdir(parents=True, exist_ok=True)
    for f in LOGS.glob("*.log"):
        try:
            if date.fromisoformat(f.stem) < hoy - timedelta(days=30):
                f.unlink()
        except ValueError:
            pass
    lineas = [f"# Registro {hoy.isoformat()}", ""] + reg.lineas + ["", "## Fuentes con problemas"]
    lineas += [f"- {k}: {v}" for k, v in sorted(errores.items())] or ["- ninguna"]
    for titulo, es_local in (("## Descartadas (nacional, internacional y ocio)", False), ("## Descartadas LOCALES", True)):
        lineas += ["", titulo]
        for motivo, items in sorted(reg.descartes.items()):
            sel = [t for loc, t in items if loc == es_local]
            if sel:
                lineas.append(f"### {motivo} ({len(sel)})")
                lineas += [f"- {t}" for t in sel[:150]]
                if len(sel) > 150:
                    lineas.append(f"- … y {len(sel) - 150} más")
    (LOGS / f"{hoy.isoformat()}.log").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sin-ia", action="store_true", help="usar solo el modo de respaldo")
    args = ap.parse_args()

    cfg = cargar_config()
    tz = zona(cfg)
    ahora = datetime.now(tz)
    hoy = ahora.date()
    reg = P.Registro()
    hist = Historial()
    ia = Gemini(cfg, log=reg.info)
    if args.sin_ia:
        ia.activo = False
    sel = cfg.get("seleccion", {}) or {}
    reg.info(f"Inicio {ahora:%Y-%m-%d %H:%M} ({tz.key})")

    # 1. descargar
    fuentes = fuentes_activas(cfg)
    crudas, errores = descargar_todas(fuentes)
    reg.info(f"Fuentes: {len(fuentes)} · con errores: {len(errores)} · titulares: {len(crudas)}")
    if not crudas or len(errores) > 0.7 * len(fuentes):
        guardar_log(hoy, reg, errores)
        raise SystemExit("ERROR: casi ninguna fuente respondió; revisa la conexión o las fuentes.")
    recientes, viejas = filtrar_por_edad(crudas, sel.get("horas_maximas", 36))
    revisados = len(recientes)
    reg.info(f"Recientes: {revisados} (más viejas de {sel.get('horas_maximas', 36)} h: {viejas})")

    # 2. filtros y duplicados (sin IA)
    def procesar(items):
        items = P.filtrar(items, cfg, reg)
        items, dups = FL.agrupar_duplicados(items, sel.get("similitud_duplicados", 0.55))
        reg.contador["duplicados"] += dups
        return P.clasificar_reglas(items, cfg, reg)

    candidatos = procesar(recientes)
    # ya publicadas en días anteriores
    seg = (cfg.get("mejoras", {}) or {}).get("seguimiento", {}) or {}
    nuevos = []
    for n in candidatos:
        if hist.enviado_antes(n.enlace, hoy):
            reg.descarte("ya_publicada", n)
            continue
        nuevos.append(n)
    candidatos = nuevos
    reg.info(f"Candidatas tras filtros: {len(candidatos)}")

    # 3. clasificación con IA (lote 1) o respaldo
    modo_respaldo = True
    if ia.activo:
        try:
            candidatos = P.clasificar_ia(candidatos, cfg, ia, reg)
            modo_respaldo = False
            reg.info(f"Gemini lote 1 OK (modelo {ia.modelo})")
        except GeminiError as ex:
            reg.info(f"Gemini no disponible ({ex}); se usa el modo de respaldo")
    else:
        reg.info("Gemini apagado o sin clave: modo de respaldo")

    # 4. selección
    elegidas, sobrantes = P.seleccionar(candidatos, cfg, reg)
    if not any(n.seccion == "local" for n in elegidas):
        extra = P.completar_departamento(cfg, False, reg, procesar)
        extra = [n for n in extra if not hist.enviado_antes(n.enlace, hoy)]
        for n in extra:
            n.seccion, n.alcance = "local", "local"
        extra_elegidas, extra_sobrantes = P.seleccionar(extra, cfg, reg)
        elegidas += [n for n in extra_elegidas if n.seccion == "local"]
        sobrantes += [(n, m) for n, m in extra_sobrantes if n.seccion == "local"]

    # 5. seguimiento de historias
    def es_nueva(n, registrar=True):
        if not seg.get("activo", True):
            return True
        h = hist.buscar_historia(n.tokens, hoy, seg.get("dias_memoria", 14), seg.get("similitud", 0.45))
        if h:
            if n.fecha.astimezone(tz).date() < hoy:
                if registrar:
                    reg.descarte("ya_publicada", n, "sin novedad")
                return False
            n.seguimiento_dia = (hoy - h[1]).days + 1
            n._historia = h[0]
        return True

    elegidas = [n for n in elegidas if es_nueva(n)]
    # "Ver más": siguientes mejores de cada sección (no cuentan para los topes)
    ver_mas = {}
    for n in P.elegir_ver_mas(sobrantes, cfg, reg, aceptar=lambda n: es_nueva(n, registrar=False)):
        ver_mas.setdefault(n.seccion, []).append(n)

    # 6. resúmenes (lote 2) y medios
    ok_resumen = P.resumir(elegidas, cfg, ia, not modo_respaldo, reg)
    respaldo_resumenes = not ok_resumen and not modo_respaldo
    medios.enriquecer(elegidas, cfg)

    # 7. destacada y secciones
    serias = [n for n in elegidas if n.seccion in ("nacional", "internacional")]
    destacada = None
    if serias:
        tope = max(n.puntaje for n in serias)
        destacada = next((n for n in serias if n.puntaje == tope and n.imagen), None) or \
            next(n for n in serias if n.puntaje == tope)
    secciones = {}
    for n in elegidas:
        if n is not destacada:
            secciones.setdefault(n.seccion, []).append(n)
    for lista in secciones.values():
        lista.sort(key=lambda n: -n.puntaje)

    temas_alma, _ = alma.generar(cfg, ia, hoy, reg.info)
    estrenos = cine.construir(cfg, ia, hoy, reg.info)
    tarjetas_mercado = mercados.actualizar(cfg, hist, reg.info)
    items_agenda = agenda.construir(cfg, hoy, tz, reg.info)

    # 8. página y archivo
    SITIO.mkdir(exist_ok=True)
    (SITIO / "archivo").mkdir(exist_ok=True)
    k = reg.contador
    contador = None
    if ((cfg.get("mejoras", {}) or {}).get("contador_descartes", {}) or {}).get("activo", True):
        contador = {"revisados": revisados, "entraron": len(elegidas), "sensacionalismo": k["sensacionalismo"],
                    "publicidad": k["publicidad"], "duplicados": k["duplicados"],
                    "baja_importancia": sum(k[m] for m in ("baja_importancia", "cupo_tema", "cupo_seccion",
                                                           "sin_tema", "fuera_de_interes", "tema_apagado", "ya_publicada"))}
    dias_archivo = int((cfg.get("pagina", {}) or {}).get("dias_archivo", 7))
    anteriores = sorted((f.stem for f in (SITIO / "archivo").glob("*.html") if f.stem != hoy.isoformat()), reverse=True)
    for viejo in anteriores[dias_archivo:]:
        (SITIO / "archivo" / f"{viejo}.html").unlink(missing_ok=True)
    anteriores = anteriores[:dias_archivo]
    colores = {kk: v.get("color") for kk, v in (cfg.get("temas") or {}).items()}
    for kk, v in (((cfg.get("local", {}) or {}).get("categorias", {})) or {}).items():
        colores[f"local_{kk}"] = v.get("color")
    loc = cfg.get("local", {}) or {}
    usar_logo_png, hay_iconos = preparar_logo_e_iconos(cfg, reg)
    ctx = {
        "ahora_utc": ahora_utc(), "fecha_larga": fecha_larga(hoy), "fecha_corta": hoy.strftime("%d/%m/%Y"),
        "actualizado": f"Actualizado hoy {ahora.hour}:{ahora.minute:02d} (hora de Colombia)",
        "destacada": destacada, "secciones": secciones, "mercados": tarjetas_mercado, "agenda": items_agenda,
        "contador": contador, "instagram": botones_instagram(loc) if loc.get("activo", True) else [],
        "ver_mas": ver_mas, "alma": temas_alma, "cine": estrenos,
        "archivo": [(d, fecha_larga(date.fromisoformat(d)).capitalize()) for d in anteriores],
        "modo_respaldo": modo_respaldo, "respaldo_resumenes": respaldo_resumenes, "portada": preparar_portada(cfg, reg),
        "imagenes_categoria": imagenes_categoria(), "colores": colores,
        "logo_png": usar_logo_png, "iconos": hay_iconos,
    }
    pagina = Pagina(cfg, ctx)
    html = pagina.html()
    (SITIO / "index.html").write_text(html, encoding="utf-8")
    (SITIO / "archivo" / f"{hoy.isoformat()}.html").write_text(pagina.html(prefijo="../"), encoding="utf-8")
    (SITIO / "robots.txt").write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")
    reg.info(f"Página: {len(html.encode()) / 1024:.0f} KB · {len(elegidas)} noticias + "
             f"{sum(len(v) for v in ver_mas.values())} en 'Ver más' · "
             f"modo {'respaldo (sin IA)' if modo_respaldo else ('IA (resúmenes sin IA)' if respaldo_resumenes else 'IA')} · llamadas a Gemini: {ia.llamadas}")

    # 9. historial, log y canales opcionales
    for n in elegidas + [x for v in ver_mas.values() for x in v]:
        hist.registrar(n, hoy, getattr(n, "_historia", None))
    hist.registrar_ejecucion(hoy, "respaldo" if modo_respaldo else "ia", revisados, len(elegidas))
    hist.limpiar(hoy)
    hist.cerrar()
    guardar_log(hoy, reg, errores)
    orden = sorted(elegidas, key=lambda n: -n.puntaje)
    notificar.telegram(cfg, orden, fecha_larga(hoy), reg.info)
    notificar.correo(cfg, orden, fecha_larga(hoy), reg.info)
    reg.info("Listo.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
