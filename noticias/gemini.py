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
        self.lista_registrada = False

    # ------------------------------------------------------------ modelos
    def _modelos_flash(self):
        """Lista de modelos Flash disponibles: primero los estables más recientes, luego los preview."""
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
            estable = 0 if ("preview" in nombre or "latest" in nombre) else 1
            candidatos.append((estable, float(ver.group(1)) if ver else 0, nombre))
        candidatos.sort(reverse=True)
        return [c[2] for c in candidatos]

    # ------------------------------------------------------------ llamada
    def _intentar(self, modelo, cuerpo):
        """Prueba un modelo. Devuelve (json, None) o (None, 'siguiente'|'fatal', motivo)."""
        ultimo = ""
        errores_servidor = 0
        for _ in range(self.reintentos + 1):
            try:
                r = http_post(f"{API}/models/{modelo}:generateContent",
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
                    return _parsear_json(texto), None, ""
                except (KeyError, IndexError, ValueError) as ex:
                    ultimo = f"respuesta no válida: {ex}"
                    continue
            try:
                detalle = r.json().get("error", {}).get("message", "")[:140]
            except ValueError:
                detalle = r.text[:140]
            ultimo = f"HTTP {r.status_code}: {detalle}"
            if r.status_code in (401, 403) or "API key" in r.text:
                return None, "fatal", "clave no válida o sin permiso"
            if r.status_code in (400, 404):
                return None, "siguiente", f"modelo no disponible (HTTP {r.status_code})"
            if r.status_code == 429:
                if "PerDay" in r.text or "per day" in r.text.lower():
                    return None, "siguiente", "cuota diaria agotada para este modelo"
                espera = self.pausa
                m = re.search(r'"retryDelay":\s*"(\d+)', r.text)
                if m:
                    espera = min(int(m.group(1)) + 2, 90)
                self.log(f"Límite de cuota en {modelo}; espero {espera} s")
                time.sleep(espera)
                continue
            if r.status_code in (500, 502, 503, 504):
                errores_servidor += 1
                if errores_servidor >= 2:       # saturado: mejor probar otro modelo
                    break
                time.sleep(min(self.pausa, 20))
                continue
            return None, "fatal", ultimo
        return None, "siguiente", f"sin respuesta útil ({ultimo})"

    def generar_json(self, prompt):
        if not self.activo:
            raise GeminiError("sin clave GEMINI_API_KEY o desactivado")
        cuerpo = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
        }
        probados, alternativos = [], None
        modelo = self.modelo
        while modelo and len(probados) < 5:
            probados.append(modelo)
            datos, accion, motivo = self._intentar(modelo, cuerpo)
            if accion is None:
                self.modelo = modelo        # el segundo lote usa el que funcionó
                return datos
            self.log(f"Gemini {modelo}: {motivo}")
            if accion == "fatal":
                raise GeminiError(motivo)
            if alternativos is None:
                alternativos = self._modelos_flash()
                if not self.lista_registrada:
                    self.log("Modelos Flash disponibles: " + ", ".join(alternativos[:8]))
                    self.lista_registrada = True
            modelo = next((m for m in alternativos if m not in probados), None)
        raise GeminiError("ningún modelo Flash respondió (" + ", ".join(probados) + ")")


def buscar_con_google(ia, prompt, modelos):
    """UNA llamada con la búsqueda de Google integrada (herramienta google_search).

    Solo se pasa a otro modelo si el anterior no existe o no admite la herramienta
    (HTTP 400/404: en ese caso no se hizo ninguna búsqueda). Cualquier otro error
    termina aquí, sin reintentos, para no gastar más de una búsqueda al día.
    Devuelve (texto, metadatos_de_busqueda, modelo) o lanza GeminiError.
    """
    if not ia.activo:
        raise GeminiError("sin clave GEMINI_API_KEY o desactivado")
    cuerpo = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
              "tools": [{"google_search": {}}],
              "generationConfig": {"temperature": 0.1}}
    motivos = []
    for modelo in modelos:
        try:
            r = http_post(f"{API}/models/{modelo}:generateContent", params={"key": ia.clave},
                          json=cuerpo, timeout=120)
        except Exception as ex:  # noqa: BLE001
            raise GeminiError(f"{modelo}: {type(ex).__name__}") from None
        ia.llamadas += 1
        if r.status_code == 200:
            try:
                cand = r.json()["candidates"][0]
                texto = "".join(p.get("text", "") for p in cand["content"]["parts"] if not p.get("thought"))
            except (KeyError, IndexError, ValueError) as ex:
                raise GeminiError(f"{modelo}: respuesta no válida ({ex})") from None
            return texto, cand.get("groundingMetadata") or {}, modelo
        try:
            detalle = r.json().get("error", {}).get("message", "")[:140]
        except ValueError:
            detalle = r.text[:140]
        motivos.append(f"{modelo}: HTTP {r.status_code} {detalle}")
        if r.status_code not in (400, 404) or "API key" in detalle:
            break
    raise GeminiError("; ".join(motivos) or "sin modelos para la búsqueda")


def _parsear_json(texto):
    texto = texto.strip()
    texto = re.sub(r"^```(?:json)?|```$", "", texto, flags=re.M).strip()
    try:
        return json.loads(texto)
    except ValueError:
        m = re.search(r"(\[.*\]|\{.*\})", texto, re.S)
        if not m:
            raise
        return json.loads(m.group(1))


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
