"""Prueba del filtro de contenido sexual con titulares de ejemplo.

Uso:  python pruebas/probar_filtro.py
Sale con error si algún titular que debe bloquearse pasa, o si uno normal se bloquea.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from noticias import filtro_sexual as F  # noqa: E402
from noticias.utils import cargar_config  # noqa: E402

DEBEN_BLOQUEARSE = [
    "Filtran video íntimo de famosa influencer",
    "Así luce en bikini la presentadora",
    "La foto SEXY que incendió las redes",
    "Nuevo escándalo de p0rn0grafía en colegio",
    "Modelo de 0nlyF4ns revela sus ganancias",
    "Video de s.e.x.y modelo se vuelve viral",
    "Actriz posa d3snuda para revista",
    "P O R N O en redes: alerta",
    "Sitio porn hub bloqueado en el país",
    "sexxxy outfit at the gala",
    "Celebrity leaked nudes scandal",
    "NSFW content spreads on social media",
    "La sensualidad de la nueva campaña",
    "Fotos íntimas filtradas de concejal",
    "Pooorno en la red: nueva estafa",
    "Así es el negocio de las modelos webcam en Medellín",
    "Top 10 erotic movies of the year",
    "Video XXX filtrado en redes",
    "x x x en redes: nueva estafa",
]
DEBEN_PASAR = [
    "Corte Constitucional ordena cambio de sexo en registro civil",
    "Canal de Panamá aumenta tarifas",
    "Análisis: la economía del sexto mes",
    "Termina el sexenio en México",
    "Essex police arrest suspects",
    "Universidad de Sussex publica estudio",
    "Anales de historia romana: nuevo hallazgo arqueológico",
    "Cáncer de mama: autoexamen salva vidas",
    "Sexagenario muere en accidente de tránsito",
    "Video viral: perro rescata a niño en el río",
    "Selección Colombia vence 2-1 a Paraguay",
    "Récord de 2026 en exportaciones de café",
    "G7 discute nuevos aranceles",
    "COVID-19 repunta en Europa",
    "Erupción del volcán Nevado del Ruiz: alerta naranja",
    "Corte Suprema condena a exfuncionario por abuso sexual",
    "Ya inició la colaboración Overwatch x Shadow Monarch",
    "Hurricane Isaias Wind Speed Probabilities Number 14",
    "La Hispanidad en la era global, un pasado que quema",
]


def main():
    cfg = cargar_config()
    fallos = 0
    print("== Deben BLOQUEARSE")
    for t in DEBEN_BLOQUEARSE:
        m = F.revisar(cfg, t)
        fallos += not m
        print(f"  {'OK   ' if m else 'FALLA'} {t}  {m}")
    print("== Deben PASAR")
    for t in DEBEN_PASAR:
        m = F.revisar(cfg, t)
        fallos += bool(m)
        print(f"  {'OK   ' if not m else 'FALLA'} {t}  {m}")
    print(f"\n{'Todo correcto' if not fallos else str(fallos) + ' fallos'}")
    sys.exit(1 if fallos else 0)


if __name__ == "__main__":
    main()
