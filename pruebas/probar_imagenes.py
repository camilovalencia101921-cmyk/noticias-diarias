"""Prueba de la capa 4: una fuente NO aprobada nunca muestra imagen (solo el ícono del tema).

Uso:  python pruebas/probar_imagenes.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from noticias import aprobados  # noqa: E402
from noticias.fuentes import Noticia  # noqa: E402
from noticias.pagina import Pagina  # noqa: E402
from noticias.utils import ahora_utc, cargar_config  # noqa: E402


def main():
    cfg = cargar_config()
    dominios = aprobados.dominios()
    pag = Pagina(cfg, {"imagenes_categoria": {}, "ahora_utc": ahora_utc()})
    casos = [("https://www.eltiempo.com/justicia/nota-123", True), ("https://sitio-desconocido-xyz.com/nota", False),
             ("https://elmeridiano.co/cordoba/judicial/nota", True), ("https://www.revista-de-chismes.example/foto", False)]
    fallos = 0
    for url, debe_mostrar in casos:
        n = Noticia(titulo="Titular de prueba", enlace=url, fuente="Prueba", fecha=ahora_utc(),
                    imagen="https://ejemplo.com/foto.jpg", tema="justicia", seccion="nacional")
        n.dominio_medio = url.split("/")[2]
        n.aprobado = aprobados.es_aprobado(n.dominio_medio, dominios)
        html = pag.miniatura(n, "", "th76")
        muestra = 'class="foto"' in html
        ok = muestra == debe_mostrar
        fallos += not ok
        print(f"  {'OK   ' if ok else 'FALLA'} {n.dominio_medio:32} aprobado={n.aprobado!s:5} imagen={'sí' if muestra else 'no (ícono del tema)'}")
    print(f"\n{'Todo correcto' if not fallos else str(fallos) + ' fallos'}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
