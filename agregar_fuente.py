"""Agrega, lista o elimina fuentes de noticias en config.yaml.

Ejemplos:
  python agregar_fuente.py "https://www.ejemplo.com" --alcance nacional --filtro estricto
  python agregar_fuente.py "https://www.youtube.com/@canal" --alcance local --filtro flexible
  python agregar_fuente.py "https://www.instagram.com/medio"      (solo se guarda como botón)
  python agregar_fuente.py --listar
  python agregar_fuente.py --eliminar 12          (número que muestra --listar)
  python agregar_fuente.py --eliminar "nombre o parte del link"
  python agregar_fuente.py --eliminar "instagram.com/medio"   (quita un botón de Instagram)
"""
import argparse
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import quote_plus, urljoin, urlparse

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

from noticias.fuentes import leer_rss, leer_sitemap
from noticias.utils import RAIZ, dominio, http_get, normalizar

CONFIG = RAIZ / "config.yaml"
RUTAS_FEED = ["/feed", "/feed/", "/rss", "/rss.xml", "/feeds/all.rss", "/index.xml", "/atom.xml"]


def yaml_rt():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def cargar():
    with open(CONFIG, encoding="utf-8") as f:
        return yaml_rt().load(f)


def guardar(data):
    with open(CONFIG, "w", encoding="utf-8") as f:
        yaml_rt().dump(data, f)


def say(msg=""):
    print(msg, flush=True)


# ------------------------------------------------------------------ detección
def probar_feed(url, tipo="rss"):
    """Devuelve (noticias, título_del_feed) o ([], None)."""
    try:
        r = http_get(url, timeout=15)
        if r.status_code != 200 or not r.content:
            return [], None
        f = {"nombre": "x", "url": url, "tipo": tipo}
        if tipo == "sitemap":
            return leer_sitemap(f, r.content), None
        items = leer_rss(f, r.content)
        m = re.search(rb"<title>(?:<!\[CDATA\[)?\s*([^<\]]{2,80})", r.content)
        titulo = m.group(1).decode("utf-8", "replace").strip() if m else None
        return items, titulo
    except Exception:  # noqa: BLE001
        return [], None


def canal_youtube(link):
    m = re.search(r"youtube\.com/channel/(UC[\w-]{22})", link)
    if m:
        cid = m.group(1)
    else:
        try:
            r = http_get(link, timeout=15, cookies={"CONSENT": "YES+1"})
        except Exception:  # noqa: BLE001
            return None
        m = re.search(r'"externalId":"(UC[\w-]{22})"', r.text) or re.search(r'channel_id=(UC[\w-]{22})', r.text)
        if not m:
            return None
        cid = m.group(1)
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}"


def detectar(link):
    """Devuelve (url_feed, tipo, nota, noticias, titulo) o (None, ..., motivo)."""
    if "youtube.com" in link or "youtu.be" in link:
        feed = canal_youtube(link)
        if not feed:
            return None, None, "No pude encontrar el canal de YouTube en ese link.", [], None
        items, tit = probar_feed(feed)
        return feed, "rss", "Canal de YouTube", items, tit

    # 1) ¿el link ya es un feed?
    items, tit = probar_feed(link)
    if items:
        return link, "rss", "El link ya era un feed", items, tit

    # 2) <link rel="alternate"> en la página
    try:
        r = http_get(link, timeout=15)
        pagina = r.text if r.status_code == 200 else ""
    except Exception:  # noqa: BLE001
        pagina = ""
    for tag in re.findall(r"<link[^>]+>", pagina, re.I):
        if re.search(r'rel=["\']alternate["\']', tag, re.I) and re.search(r"(rss|atom)\+xml", tag, re.I):
            href = re.search(r'href=["\']([^"\']+)["\']', tag)
            if href and "comments" not in href.group(1):
                url = urljoin(link, href.group(1))
                items, tit = probar_feed(url)
                if items:
                    return url, "rss", "Encontrado en la página (link alternate)", items, tit

    # 3) rutas comunes, en la sección y en la raíz del sitio
    p = urlparse(link)
    raiz = f"{p.scheme}://{p.netloc}"
    bases = [link.rstrip("/")] + ([raiz] if p.path.strip("/") else [])
    for base in bases:
        for ruta in RUTAS_FEED:
            url = base + ruta
            items, tit = probar_feed(url)
            if items:
                return url, "rss", f"Encontrado en {ruta}", items, tit

    # 4) sitemap de noticias (enlaces reales; útil para sitios que cargan con script)
    try:
        robots = http_get(raiz + "/robots.txt", timeout=10).text
        for sm in re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots):
            if "news" in sm.lower() or "google" in sm.lower():
                items, _ = probar_feed(sm, "sitemap")
                if items:
                    return sm, "sitemap", "Sitemap de noticias del sitio (enlaces directos)", items, None
    except Exception:  # noqa: BLE001
        pass

    # 5) plan B: Google News filtrado por dominio
    dom = dominio(link)
    url = f"https://news.google.com/rss/search?q={quote_plus('site:' + dom + ' when:7d')}&hl=es-419&gl=CO&ceid=CO:es-419"
    items, _ = probar_feed(url)
    if items:
        return url, "rss", "PLAN B: el sitio no tiene RSS; se usa Google News filtrado por su dominio", items, None
    return None, None, "No encontré ningún feed ni noticias de ese sitio, ni siquiera en Google News.", [], None


def validar(items):
    reales = [n for n in items if len(n.titulo.split()) >= 4]
    if len(reales) < 3:
        return False, "El feed tiene muy pocos titulares (menos de 3)."
    limite = datetime.now(timezone.utc) - timedelta(days=30)
    if not any(n.fecha and n.fecha > limite for n in reales):
        return False, "El feed no tiene noticias del último mes; parece abandonado."
    return True, ""


# ------------------------------------------------------------------ acciones
def todas_las_fuentes(cfg):
    lista = [("fuentes", i, f) for i, f in enumerate(cfg.get("fuentes") or [])]
    lista += [("local", i, f) for i, f in enumerate((cfg.get("local") or {}).get("fuentes") or [])]
    return lista


def listar():
    cfg = cargar()
    for n, (_, _, f) in enumerate(todas_las_fuentes(cfg), 1):
        estado = "activa " if f.get("activo", True) else "APAGADA"
        say(f"{n:3}. [{estado}] {f.get('alcance', 'local'):13} {f.get('filtro', 'estricto'):9} {f.get('nombre')}  ->  {f.get('url')}")
    ig = (cfg.get("local") or {}).get("instagram") or []
    if ig:
        say("\nBotones de Instagram (máximo 6 visibles; no verificados):")
        for b in ig:
            b = {"url": b, "activo": True} if isinstance(b, str) else b
            estado = "activo " if b.get("activo") and b.get("url") else "APAGADO"
            say(f"   [{estado}] {b.get('nombre', '')}  ->  {b.get('url') or '(pendiente de enlace)'}")


def eliminar(texto, confirmar=True):
    cfg = cargar()
    todas = todas_las_fuentes(cfg)
    if "instagram.com" in texto.lower():
        elegidas = []
    elif texto.isdigit() and 1 <= int(texto) <= len(todas):
        elegidas = [todas[int(texto) - 1]]
    else:
        t = texto.lower()
        elegidas = [x for x in todas if t in str(x[2].get("nombre", "")).lower() or t in str(x[2].get("url", "")).lower()]
    ig = (cfg.get("local") or {}).get("instagram") or []
    ig_match = [b for b in ig if texto.lower().rstrip("/") in str(b if isinstance(b, str) else b.get("url", "")).lower()] \
        if "instagram.com" in texto.lower() else []
    if not elegidas and not ig_match:
        say("No encontré ninguna fuente con ese número o texto. Usa --listar para verlas.")
        return 1
    if len(elegidas) > 1:
        say("Hay varias coincidencias; escribe el número exacto (de --listar):")
        for _, _, f in elegidas:
            say(f"   - {f.get('nombre')}  ->  {f.get('url')}")
        return 1
    if elegidas:
        seccion, i, f = elegidas[0]
        say(f"Se eliminará: {f.get('nombre')}  ->  {f.get('url')}")
    else:
        say(f"Se eliminará el botón de Instagram: {ig_match[0] if isinstance(ig_match[0], str) else ig_match[0].get('url')}")
    if confirmar and input("¿Confirmas? (s/n): ").strip().lower() not in ("s", "si", "sí", "y"):
        say("Cancelado.")
        return 1
    if elegidas:
        (cfg["fuentes"] if seccion == "fuentes" else cfg["local"]["fuentes"]).pop(i)
    else:
        ig.remove(ig_match[0])
    guardar(cfg)
    say("Listo: eliminado de config.yaml.")
    return 0


def _letras(t):
    return re.sub(r"[^a-z0-9]", "", normalizar(t or ""))


def agregar_instagram(cfg, link, nombre=None):
    """Guarda el perfil como botón. Si ya existe (por URL o por nombre pendiente), lo reactiva."""
    m = re.match(r"^https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{1,30})/?(?:[?#].*)?$", link.strip())
    if not m or m.group(1).lower() in ("p", "reel", "reels", "stories", "explore", "accounts"):
        say("No se guardó nada. Motivo: el link no es de un perfil de Instagram (debe ser instagram.com/usuario).")
        return 1
    usuario = m.group(1)
    url = f"https://www.instagram.com/{usuario}"
    loc = cfg.setdefault("local", CommentedMap())
    ig = loc.setdefault("instagram", [])
    for i, b in enumerate(ig):                     # formato antiguo: solo la URL
        if isinstance(b, str):
            nueva = CommentedMap(nombre="@" + b.rstrip("/").rsplit("/", 1)[-1], url=b, activo=True)
            nueva.fa.set_flow_style()
            ig[i] = nueva
    existente = next((b for b in ig if str(b.get("url", "")).rstrip("/").lower() == url.lower()), None)
    if existente is None:                          # entrada "pendiente de enlace" con el mismo nombre
        existente = next((b for b in ig if not b.get("url") and _letras(b.get("nombre")) == _letras(usuario)), None)
        if existente is None and nombre:
            existente = next((b for b in ig if not b.get("url") and _letras(b.get("nombre")) == _letras(nombre)), None)
    if existente is not None:
        ya = existente.get("activo") and existente.get("url")
        existente["url"] = url
        existente["activo"] = True
        if nombre:
            existente["nombre"] = nombre
        accion = "ya estaba activo" if ya else "quedó reactivado"
        say(f"El botón '{existente.get('nombre')}' {accion}.")
    else:
        nueva = CommentedMap(nombre=nombre or "@" + usuario, url=url, activo=True)
        nueva.fa.set_flow_style()
        ig.append(nueva)
        say(f"Se agregó el botón '{nueva['nombre']}'.")
    activos = sum(1 for b in ig if b.get("activo") and b.get("url"))
    guardar(cfg)
    say("Instagram no se puede leer automáticamente (exige iniciar sesión): NO se agregó como fuente de noticias")
    say("y el perfil no fue comprobado. Solo se muestra como botón en 'Tus medios locales en Instagram'.")
    if activos > 6:
        say(f"Atención: hay {activos} botones activos y la página muestra solo los primeros 6.")
    return 0


def agregar(link, alcance, filtro, nombre=None):
    link = link.strip()
    if not re.match(r"^https?://", link):
        link = "https://" + link
    cfg = cargar()

    if "instagram.com" in link:
        return agregar_instagram(cfg, link, nombre)

    say(f"Revisando {link} ...")
    url, tipo, nota, items, titulo = detectar(link)
    if not url:
        say(f"No se guardó nada. Motivo: {nota}")
        return 1
    ok, motivo = validar(items)
    if not ok:
        say(f"No se guardó nada. Motivo: {motivo}")
        return 1
    say(f"✔ {nota}")
    say(f"  Feed: {url}")
    say("  Últimos 3 titulares:")
    for n in sorted(items, key=lambda n: n.fecha or datetime.min.replace(tzinfo=timezone.utc), reverse=True)[:3]:
        say(f"   • {n.titulo}")

    for _, _, f in todas_las_fuentes(cfg):
        if str(f.get("url", "")).rstrip("/") == url.rstrip("/"):
            say(f"Esa fuente ya existe en config.yaml como '{f.get('nombre')}'. No se duplicó.")
            return 0

    if not nombre:
        nombre = titulo if titulo and len(titulo) < 50 and "google" not in titulo.lower() else dominio(link)
        if "PLAN B" in nota:
            nombre = f"{dominio(link)} (Google News)"
    nueva = CommentedMap()
    nueva["nombre"] = nombre
    nueva["url"] = url
    if tipo == "sitemap":
        nueva["tipo"] = "sitemap"
    nueva["alcance"] = alcance
    nueva["filtro"] = filtro
    nueva["activo"] = True
    nueva.fa.set_flow_style()
    if alcance == "local":
        cfg.setdefault("local", CommentedMap()).setdefault("fuentes", []).append(nueva)
    else:
        cfg.setdefault("fuentes", []).append(nueva)
    guardar(cfg)
    say(f"Listo: '{nombre}' quedó guardada en config.yaml ({'dentro de local' if alcance == 'local' else alcance}, filtro {filtro}).")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Agregar, listar o eliminar fuentes de noticias.")
    ap.add_argument("link", nargs="?", help="link del medio, feed, canal de YouTube o perfil de Instagram")
    ap.add_argument("--alcance", choices=["local", "nacional", "internacional"])
    ap.add_argument("--filtro", choices=["estricto", "flexible"])
    ap.add_argument("--nombre", help="nombre a mostrar (opcional)")
    ap.add_argument("--listar", action="store_true", help="muestra todas las fuentes")
    ap.add_argument("--eliminar", metavar="NUMERO_O_TEXTO", help="elimina una fuente")
    ap.add_argument("--si", action="store_true", help="no pedir confirmación al eliminar")
    a = ap.parse_args()

    if a.listar:
        listar()
        return 0
    if a.eliminar:
        return eliminar(a.eliminar, confirmar=not a.si)
    if not a.link:
        ap.print_help()
        return 1
    alcance = a.alcance
    if not alcance and "instagram.com" not in a.link:
        while alcance not in ("local", "nacional", "internacional"):
            alcance = input("¿Alcance de esta fuente? (local / nacional / internacional): ").strip().lower()
    filtro = a.filtro or ("flexible" if alcance == "local" else "estricto")
    if "instagram.com" in a.link:
        return agregar_instagram(cargar(), a.link, a.nombre)
    return agregar(a.link, alcance, filtro, a.nombre)


if __name__ == "__main__":
    sys.exit(main())
