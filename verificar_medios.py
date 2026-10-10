"""Revisa config/medios_aprobados.json: busca el RSS de cada medio y anota cuáles no tienen.

Uso:  python verificar_medios.py           (revisa solo los que no tienen "rss" ni "sin_rss")
      python verificar_medios.py --todos   (vuelve a revisar todos)
"""
import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor

from agregar_fuente import RUTAS_FEED, probar_feed, validar
from noticias.aprobados import ARCHIVO
from noticias.utils import http_get


def buscar_rss(dominio):
    base = f"https://{dominio}"
    try:
        pagina = http_get(base, timeout=15).text
    except Exception:  # noqa: BLE001
        pagina = ""
    candidatos = []
    for tag in re.findall(r"<link[^>]+>", pagina, re.I):
        if re.search(r'rel=["\']alternate["\']', tag, re.I) and re.search(r"(rss|atom)\+xml", tag, re.I):
            h = re.search(r'href=["\']([^"\']+)["\']', tag)
            if h and "comment" not in h.group(1):
                u = h.group(1)
                candidatos.append(u if u.startswith("http") else base + "/" + u.lstrip("/"))
    candidatos += [base + r for r in RUTAS_FEED]
    for u in candidatos[:8]:
        items, _ = probar_feed(u)
        if items and validar(items)[0]:
            return u
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--todos", action="store_true")
    a = ap.parse_args()
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8"))
    pendientes = [m for m in datos["medios"] if m.get("dominio") and (a.todos or ("rss" not in m and "sin_rss" not in m))]

    def revisar(m):
        return m, buscar_rss(m["dominio"])

    with ThreadPoolExecutor(10) as ex:
        for m, rss in ex.map(revisar, pendientes):
            if rss:
                m["rss"] = rss
                m.pop("sin_rss", None)
            else:
                m.pop("rss", None)
                m["sin_rss"] = True
            print(f"{'RSS  ' if rss else 'SIN  '} {m['nombre']}: {rss or '(se leerá por Google News)'}")
    ARCHIVO.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
