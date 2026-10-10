"""Pestañas y subfiltros de la página (emoji + palabra corta, en este orden).

Una pestaña o un subfiltro sin contenido se oculta automáticamente (ver pagina.py).
"Guardadas" no es pestaña: está en la barra inferior.
"""
import re

from .utils import normalizar

PESTANAS = [("hoy", "📰", "Hoy"), ("mundo", "🌎", "Mundo"), ("local", "📍", "Local"), ("deportes", "⚽", "Deportes"),
            ("ia", "🧠", "IA"), ("ocio", "🎮", "Ocio"), ("agenda", "📅", "Agenda"), ("videos", "🎬", "Videos"),
            ("historia", "🏛️", "Historia"), ("fe", "🙏", "Fe")]

SUBFILTROS = {
    "hoy": [("todo", "✨", "Todo"), ("seguridad", "🚨", "Seguridad"), ("justicia", "⚖️", "Justicia"),
            ("politica", "🏛️", "Política"), ("economia", "💰", "Economía"), ("salud", "🏥", "Salud"),
            ("naturaleza", "🌋", "Naturaleza"), ("deportes", "⚽", "Deportes")],
    "mundo": [("todo", "✨", "Todo"), ("guerras", "⚔️", "Guerras"), ("geopolitica", "🌐", "Geopolítica"),
              ("energia", "⛽", "Energía"), ("diplomacia", "🤝", "Diplomacia")],
    "local": [("todo", "✨", "Todo"), ("seguridad", "🚨", "Seguridad"), ("orden_publico", "✊", "Orden público"),
              ("movilidad_servicios", "🚦", "Movilidad"), ("otros", "📌", "Otros")],
    "deportes": [("todo", "✨", "Todo"), ("colombia", "🇨🇴", "Colombia"), ("premier", "🏴", "Premier League"),
                 ("laliga", "🇪🇸", "LaLiga"), ("seriea", "🇮🇹", "Serie A"), ("bundesliga", "🇩🇪", "Bundesliga"),
                 ("ligue1", "🇫🇷", "Ligue 1"), ("champions", "🏆", "Champions League"),
                 ("conmebol", "🌎", "Libertadores y Sudamericana"), ("nba", "🏀", "NBA y WNBA"),
                 ("otros", "🚴", "Otros deportes")],
    "ia": [("todo", "✨", "Todo"), ("ia", "🤖", "IA"), ("ciberseguridad", "🔐", "Ciberseguridad")],
    "ocio": [("todo", "✨", "Todo"), ("anime", "🎌", "Anime"), ("freestyle", "🎤", "Freestyle"), ("cine", "🎬", "Cine"),
             ("tecnologia", "💻", "Tecnología")],
    "agenda": [("todo", "✨", "Todo"), ("futbol", "⚽", "Fútbol"), ("nba", "🏀", "NBA y WNBA"),
               ("estrenos", "🎬", "Estrenos"), ("eventos", "🎤", "Eventos")],
    "videos": [("todo", "✨", "Todo"), ("ia", "🧠", "IA"), ("historia", "🏛️", "Historia"), ("futbol", "⚽", "Fútbol"),
               ("nba", "🏀", "NBA"), ("anime", "🎮", "Anime y freestyle"), ("humor", "😂", "Humor")],
    "historia": [("todo", "✨", "Todo"), ("hallazgos", "🏺", "Hallazgos"), ("grecoroma", "🏛️", "Grecia y Roma"),
                 ("egipto", "🐫", "Egipto y Oriente"), ("america", "🌎", "América antigua")],
    "fe": [("todo", "✨", "Todo"), ("alma", "🕯️", "Para el alma"), ("noticias", "⛪", "Noticias")],
}

FONDOS = {"mundo": "linear-gradient(135deg,#1E2F5C,#3A5BA8)", "deportes": "linear-gradient(135deg,#14532D,#15803D)"}

TEMAS_IA = {"inteligencia_artificial": "ia", "ciberseguridad": "ciberseguridad"}
TEMAS_OCIO = {"anime", "freestyle", "cine", "tecnologia"}
TEMAS_DEPORTES = {"futbol", "baloncesto", "otros_deportes"}
SUB_HOY = {"seguridad": "seguridad", "orden_publico": "seguridad", "justicia": "justicia", "politica": "politica",
           "contratacion": "politica", "economia": "economia", "mercados": "economia", "energia": "economia",
           "salud": "salud", "fenomenos_naturales": "naturaleza"}
DIPLOMACIA = re.compile(r"\b(diplomac|cancill|embajad|cumbre|onu|naciones unidas|negociac|acuerdo de paz|tratado|"
                        r"bilateral|relaciones exteriores|diplomat|summit)")
HISTORIA = [("grecoroma", re.compile(r"\b(roma|roman|grecia|grieg|greek|atenas|esparta|pompeya|pompeii|etrusc|bizanti)")),
            ("egipto", re.compile(r"\b(egipt|egypt|faraon|pharaoh|mesopotam|babilon|persa|persia|cartag|fenici|sumer|asiri|hitit)")),
            ("america", re.compile(r"\b(maya|azteca|aztec|inca|mexica|olmeca|precolomb|teotihuac|tiwanaku|muisca|zenu)")),
            ("hallazgos", re.compile(r"\b(hallazgo|descubr|excavac|arqueolog|unearth|discover|archaeolog|yacimiento|tumba|tomb)"))]
LIGAS = [
    ("colombia", re.compile(r"\b(liga betplay|betplay|dimayor|copa colombia|seleccion colombia|seleccion de colombia|tricolor|"
                            r"atletico nacional|millonarios|america de cali|junior|santa fe|independiente medellin|dim\b|"
                            r"deportes tolima|once caldas|deportivo cali|jaguares|deportivo pereira|bucaramanga|deportivo pasto|"
                            r"envigado|llaneros|fortaleza ceif|aguilas doradas|boyaca chico|alianza fc|union magdalena|"
                            r"nestor lorenzo|luis diaz|james rodriguez)")),
    ("premier", re.compile(r"\b(premier league|manchester city|manchester united|man city|man united|liverpool|arsenal|chelsea|"
                           r"tottenham|newcastle|aston villa|everton|west ham|brighton|nottingham|crystal palace)")),
    ("laliga", re.compile(r"\b(laliga|la liga|real madrid|barcelona|barca|atletico de madrid|sevilla|villarreal|"
                          r"real sociedad|athletic club|real betis|valencia cf|girona)")),
    ("seriea", re.compile(r"\b(serie a|juventus|inter de milan|inter milan|ac milan|napoli|lazio|atalanta|as roma|fiorentina)")),
    ("bundesliga", re.compile(r"\b(bundesliga|bayern|dortmund|leverkusen|leipzig|stuttgart|eintracht)")),
    ("ligue1", re.compile(r"\b(ligue 1|psg|paris saint germain|marsella|marseille|olympique|lyon|monaco|lille)")),
    ("champions", re.compile(r"\b(champions league|liga de campeones|uefa champions)")),
    ("conmebol", re.compile(r"\b(libertadores|sudamericana|conmebol|boca juniors|river plate|flamengo|palmeiras)")),
]


def pestana_de(n):
    if n.tema in TEMAS_DEPORTES:
        return "deportes"
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
    elif pestana == "deportes":
        if n.tema == "baloncesto":
            subs.append("nba")
        elif n.tema == "otros_deportes":
            subs.append("otros")
        else:
            subs += [k for k, r in LIGAS if r.search(texto)]
            if n.pista_sub and n.pista_sub not in subs and len(subs) < 2:
                subs.append(n.pista_sub)
    elif pestana == "ia":
        subs.append(TEMAS_IA.get(n.tema, "ia"))
    elif pestana == "ocio":
        subs.append(n.tema)
    elif pestana == "historia":
        subs += [k for k, r in HISTORIA if r.search(texto)]
    elif pestana == "fe":
        subs.append("noticias")
    return subs


def es_favorito(n, equipos):
    texto = normalizar(n.titulo + " " + n.descripcion[:200])
    return any(e and re.search(r"\b" + re.escape(normalizar(e)) + r"\b", texto) for e in equipos)
