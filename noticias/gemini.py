"""Cliente mínimo de la API gratuita de Gemini (Google AI Studio).

Solo envía titulares y descripciones públicas. Máximo 2 llamadas al día:
  lote 1: clasificar y puntuar candidatos
  lote 2: resumen y "por qué importa" de las seleccionadas
Si algo falla, lanza GeminiError y el programa sigue en modo de respaldo.
"""
import json
import os
import re
import time

from .utils import http_get, http_post

API = "https://generativelanguage.googleapis.com/v1beta"


class GeminiError(Exception):
    pass


class Gemini:
    def __init__(self, cfg, log=print):
        g = cfg.get("gemini", {}) or {}
        self.clave = os.environ.get("GEMINI_API_KEY", "").strip()
        self.modelo = g.get("modelo", "gemini-2.5-flash")
        self.reintentos = int(g.get("reintentos", 3))
        self.pausa = int(g.get("pausa_segundos", 30))
        self.activo = bool(g.get("activo", True)) and bool(self.clave)
        self.log = log
        self.llamadas = 0

    # ------------------------------------------------------------ modelos
    def _modelo_flash_disponible(self):
        """Consulta el listado de modelos y elige el Flash más reciente."""
        r = http_get(f"{API}/models", params={"key": self.clave, "pageSize": 200}, timeout=20)
        if r.status_code != 200:
            raise GeminiError(f"no se pudo listar modelos (HTTP {r.status_code})")
        candidatos = []
        for m in r.json().get("models", []):
            nombre = m.get("name", "").replace("models/", "")
            if ("flash" not in nombre or "generateContent" not in m.get("supportedGenerationMethods", [])):
                continue
            if any(x in nombre for x in ("lite", "image", "tts", "audio", "live", "thinking", "exp", "8b")):
                continue
            ver = re.search(r"gemini-(\d+(?:\.\d+)?)", nombre)
            estable = 0 if "preview" in nombre else 1
            latest = 1 if nombre.endswith("latest") else 0
            candidatos.append((float(ver.group(1)) if ver else 0, estable, -latest, nombre))
        if not candidatos:
            raise GeminiError("no hay modelos Flash disponibles")
        candidatos.sort(reverse=True)
        return candidatos[0][3]

    # ------------------------------------------------------------ llamada
    def generar_json(self, prompt):
        if not self.activo:
            raise GeminiError("sin clave GEMINI_API_KEY o desactivado")
        cuerpo = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        cambio_modelo = False
        ultimo = ""
        for intento in range(self.reintentos + 1):
            try:
                r = http_post(f"{API}/models/{self.modelo}:generateContent",
                              params={"key": self.clave}, json=cuerpo, timeout=180)
            except Exception as ex:  # noqa: BLE001
                ultimo = f"{type(ex).__name__}"
                time.sleep(5)
                continue
            self.llamadas += 1
            if r.status_code == 200:
                try:
                    partes = r.json()["candidates"][0]["content"]["parts"]
                    texto = "".join(p.get("text", "") for p in partes if not p.get("thought"))
                    return _parsear_json(texto)
                except (KeyError, IndexError, ValueError) as ex:
                    ultimo = f"respuesta no válida: {ex}"
                    continue
            ultimo = f"HTTP {r.status_code}: {r.text[:200]}"
            if r.status_code in (400, 404) and not cambio_modelo and "API key" not in r.text:
                nuevo = self._modelo_flash_disponible()
                self.log(f"Modelo {self.modelo} no disponible; se usa {nuevo}")
                self.modelo, cambio_modelo = nuevo, True
                continue
            if r.status_code == 429:
                espera = self.pausa
                m = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                if m:
                    espera = min(int(m.group(1)) + 2, 90)
                if "PerDay" in r.text or "per day" in r.text.lower():
                    raise GeminiError("cuota diaria agotada")
                self.log(f"Límite de cuota; espero {espera} s")
                time.sleep(espera)
                continue
            if r.status_code in (500, 502, 503, 504):
                time.sleep(min(self.pausa, 15) * (intento + 1))
                continue
            raise GeminiError(ultimo)
        raise GeminiError(ultimo or "sin respuesta")


def _parsear_json(texto):
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.M).strip()
    return json.loads(texto)


# ---------------------------------------------------------------- prompts
def prompt_clasificar(items, temas, locales):
    lista_temas = "\n".join(f'- {k}: {v.get("descripcion", v.get("nombre", k))}' for k, v in temas.items())
    datos = [{"id": n.id, "t": n.titulo[:200], "d": n.descripcion[:220], "f": n.fuente, "a": n.alcance,
              "nf": len(n.fuentes_cluster or {n.fuente}), "of": int(n.oficial)} for n in items]
    return f"""Eres editor de un resumen diario de noticias para Colombia. Clasifica cada noticia y evalúa su importancia.

TEMAS permitidos (usa la clave exacta; "ninguno" si no encaja en ninguno):
{lista_temas}

Reglas de temas: "tecnologia" solo si NO es inteligencia artificial ni ciberseguridad. "baloncesto" solo NBA/WNBA.
"futbol" solo Liga BetPlay, Selección Colombia o Champions League. "historia_antigua" excluye pseudociencia.
Para noticias con a="local" el tema puede ser "ninguno": igual evalúalas.

Criterios, cada uno de 0 a 2:
 alc = alcance (cuánta gente afecta), con = consecuencias reales, nov = novedad (hecho nuevo, no repetición ni opinión),
 conf = confirmación (fuente oficial of=1 o varias fuentes nf>1), prof = profundidad (información concreta, no rumor).
Sé exigente: entretenimiento, farándula, opinión, rumores, guías de compra, horóscopos y notas de servicio valen poco.

Noticias (id, t=titular, d=descripción, f=fuente, a=alcance, nf=n.º de fuentes, of=oficial):
{json.dumps(datos, ensure_ascii=False)}

Responde SOLO un JSON: lista de objetos {{"id": "...", "tema": "clave", "c": [alc, con, nov, conf, prof]}} para todas las noticias."""


def prompt_resumir(items, perfil, con_por_que=True):
    datos = [{"id": n.id, "t": n.titulo[:220], "d": n.descripcion[:500], "tema": n.tema or n.categoria_local or ""}
             for n in items]
    extra = (f'"pq": una sola línea (máx. 22 palabras) con el impacto concreto para {perfil}. '
             "No menciones contratación estatal.") if con_por_que else '"pq": ""'
    return f"""Para cada noticia escribe en español:
"r": resumen de máximo 2 líneas (máx. 35 palabras) solo con hechos verificables del titular y la descripción, sin adjetivos emocionales ni opiniones, sin inventar datos.
{extra}

Noticias: {json.dumps(datos, ensure_ascii=False)}

Responde SOLO un JSON: lista de objetos {{"id": "...", "r": "...", "pq": "..."}}."""
