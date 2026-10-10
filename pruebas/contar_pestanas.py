"""Cuenta noticias por pestaña y subfiltro (destacadas y "Ver más").

Uso:  python pruebas/contar_pestanas.py                 (página generada en sitio/)
      python pruebas/contar_pestanas.py --publicada     (página publicada en GitHub Pages)
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from noticias.utils import RAIZ, http_get  # noqa: E402

URL = "https://camilovalencia101921-cmyk.github.io/noticias-diarias/"


def cargar(publicada):
    if publicada:
        return http_get(URL, timeout=30).text, http_get(URL + "mas.json", timeout=30).json()
    return (RAIZ / "sitio" / "index.html").read_text(encoding="utf-8"), \
        json.loads((RAIZ / "sitio" / "mas.json").read_text(encoding="utf-8"))


def contar(html, mas):
    tabla = {}
    orden = re.findall(r'class="tab[^"]*" data-tab="(\w+)"', html)
    for m in re.finditer(r'<section class="panel" id="p-(\w+)"(.*?)(?=<section class="panel" id="p-|</main>)', html, re.S):
        tab, cuerpo = m.group(1), m.group(2)
        dest = Counter()
        n_dest = 0
        for sub in re.findall(r'<article class="(?:card [^"]*|fila-m [^"]*) it"[^>]*data-sub="([^"]*)"', cuerpo):
            n_dest += 1
            for s in sub.split():
                dest[s] += 1
        for sub in re.findall(r'<li data-sub="([^"]*)"', cuerpo):      # filas de la Agenda
            n_dest += 1
            dest[sub] += 1
        widgets = re.findall(r'<div class="[^"]*\bw\b[^"]*" data-sub="(\w+)"', cuerpo)
        vm = Counter()
        for x in mas.get("pestanas", {}).get(tab, []):
            for s in x.get("s", []):
                vm[s] += 1
        tabla[tab] = {"dest": n_dest, "vm": len(mas.get("pestanas", {}).get(tab, [])), "subs_dest": dest,
                      "subs_vm": vm, "widgets": widgets}
    return orden, tabla


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publicada", action="store_true")
    a = ap.parse_args()
    html, mas = cargar(a.publicada)
    orden, tabla = contar(html, mas)
    print(f"Pestañas visibles (en orden): {', '.join(orden)}\n")
    print(f"{'Pestaña':10} {'Destacadas':>10} {'Ver más':>8}   Subfiltros (destacadas / ver más)")
    for tab in orden + [t for t in tabla if t not in orden]:
        t = tabla.get(tab)
        if not t:
            print(f"{tab:10} {'—':>10} {'—':>8}")
            continue
        subs = sorted(set(t["subs_dest"]) | set(t["subs_vm"]))
        detalle = ", ".join(f"{s} {t['subs_dest'][s]}/{t['subs_vm'][s]}" for s in subs)
        extra = f"  [bloques: {', '.join(t['widgets'])}]" if t["widgets"] else ""
        print(f"{tab:10} {t['dest']:>10} {t['vm']:>8}   {detalle}{extra}")


if __name__ == "__main__":
    main()
