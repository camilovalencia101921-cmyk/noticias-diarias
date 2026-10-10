"""Pestañas y subfiltros de la página (emoji + palabra corta, en este orden)."""
import re

from .utils import normalizar

PESTANAS = [("hoy", "📰", "Hoy"), ("local", "📍", "Local"), ("mundo", "🌎", "Mundo"), ("ia", "🧠", "IA"),
            ("ocio", "🎮", "Ocio"), ("humor", "😂", "Humor"), ("historia", "🏛️", "Historia"),
            ("fe", "🙏", "Fe"), ("guardado", "🔖", "Guardado")]

SUBFILTROS = {
    "hoy": [("todo", "✨", "Todo"), ("seguridad", "🚨", "Seguridad"), ("justicia", "⚖️", "Justicia"),
            ("politica", "🏛️", "Política"), ("economia", "💰", "Economía"), ("salud", "🏥", "Salud"),
            ("naturaleza", "🌋", "Naturaleza")],
    "local": [("todo", "✨", "Todo"), ("seguridad", "🚨", "Seguridad"), ("orden_publico", "✊", "Orden público"),
              ("movilidad_servicios", "🚦", "Movilidad"), ("otros", "📌", "Otros")],
    "mundo": [("todo", "✨", "Todo"), ("guerras", "⚔️", "Guerras"), ("geopolitica", "🌐", "Geopolítica"),
              ("energia", "⛽", "Energía"), ("diplomacia", "🤝", "Diplomacia")],
    "ia": [("todo", "✨", "Todo"), ("ia", "🤖", "IA"), ("tecnologia", "💻", "Tecnología"),
           ("ciberseguridad", "🔐", "Ciberseguridad")],
    "ocio": [("todo", "✨", "Todo"), ("futbol", "⚽", "Fútbol"), ("baloncesto", "🏀", "NBA"), ("anime", "🎌", "Anime"),
             ("freestyle", "🎤", "Freestyle"), ("cine", "🎬", "Cine"), ("agenda", "📅", "Agenda")],
    "humor": [("todo", "✨", "Todo"), ("virales", "🔥", "Virales"), ("animales", "🐶", "Animales"),
              ("standup", "🎤", "Stand-up"), ("fails", "🤣", "Fails")],
    "historia": [("todo", "✨", "Todo"), ("hallazgos", "🏺", "Hallazgos"), ("grecoroma", "🏛️", "Grecia y Roma"),
                 ("egipto", "🐫", "Egipto y Oriente"), ("america", "🌎", "América antigua")],
    "fe": [("todo", "✨", "Todo"), ("alma", "🕯️", "Para el alma"), ("noticias", "⛪", "Noticias")],
}

TEMAS_IA = {"inteligencia_artificial": "ia", "tecnologia": "tecnologia", "ciberseguridad": "ciberseguridad"}
TEMAS_OCIO = {"anime", "futbol", "baloncesto", "freestyle", "cine"}
SUB_HOY = {"seguridad": "seguridad", "orden_publico": "seguridad", "justicia": "justicia", "politica": "politica",
           "contratacion": "politica", "economia": "economia", "mercados": "economia", "energia": "economia",
           "salud": "salud", "fenomenos_naturales": "naturaleza"}
DIPLOMACIA = re.compile(r"\b(diplomac|cancill|embajad|cumbre|onu|naciones unidas|negociac|acuerdo de paz|tratado|"
                        r"bilateral|relaciones exteriores|diplomat|summit)")
HISTORIA = [("grecoroma", re.compile(r"\b(roma|roman|grecia|grieg|greek|atenas|esparta|pompeya|pompeii|etrusc|bizanti)")),
            ("egipto", re.compile(r"\b(egipt|egypt|faraon|pharaoh|mesopotam|babilon|persa|persia|cartag|fenici|sumer|asiri|hitit)")),
            ("america", re.compile(r"\b(maya|azteca|aztec|inca|mexica|olmeca|precolomb|teotihuac|tiwanaku|muisca|zenu)")),
            ("hallazgos", re.compile(r"\b(hallazgo|descubr|excavac|arqueolog|unearth|discover|archaeolog|yacimiento|tumba|tomb)"))]


def pestana_de(n):
    if n.seccion == "local":
        return "local"
    if n.tema in TEMAS_IA:
        return "ia"
    if n.tema == "historia_antigua":
        return "historia"
    if n.tema == "espiritualidad":
        return "fe"
    if n.tema in TEMAS_OCIO:
        return "ocio"
    if n.seccion == "internacional":
        return "mundo"
    return "hoy"


def subfiltros_de(n, pestana):
    texto = normalizar(n.titulo + " " + n.descripcion[:200])
    subs = []
    if pestana == "hoy":
        if n.tema in SUB_HOY:
            subs.append(SUB_HOY[n.tema])
    elif pestana == "local":
        subs.append(n.categoria_local or "otros")
    elif pestana == "mundo":
        if n.tema in ("guerras", "geopolitica", "energia"):
            subs.append(n.tema)
        if DIPLOMACIA.search(texto):
            subs.append("diplomacia")
    elif pestana == "ia":
        subs.append(TEMAS_IA.get(n.tema, "tecnologia"))
    elif pestana == "ocio":
        subs.append(n.tema)
    elif pestana == "historia":
        subs += [k for k, r in HISTORIA if r.search(texto)]
    elif pestana == "fe":
        subs.append("noticias")
    return subs
