"""Historial en SQLite (data/historial.db): noticias enviadas, historias y mercados."""
import sqlite3
from datetime import date, timedelta

from .utils import RAIZ, jaccard

RUTA = RAIZ / "data" / "historial.db"


class Historial:
    def __init__(self, ruta=RUTA):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(ruta)
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS enviados (url TEXT PRIMARY KEY, titulo TEXT, fecha TEXT, historia INTEGER);
        CREATE TABLE IF NOT EXISTS historias (id INTEGER PRIMARY KEY, tokens TEXT, primera TEXT, ultima TEXT);
        CREATE TABLE IF NOT EXISTS mercados (serie TEXT, fecha TEXT, valor REAL, PRIMARY KEY (serie, fecha));
        CREATE TABLE IF NOT EXISTS ejecuciones (fecha TEXT PRIMARY KEY, modo TEXT, revisados INTEGER, publicados INTEGER);
        """)

    # ---------------------------------------------------------- noticias
    def enviado_antes(self, url, hoy):
        r = self.db.execute("SELECT 1 FROM enviados WHERE url=? AND fecha<?", (url, hoy.isoformat())).fetchone()
        return r is not None

    def buscar_historia(self, tokens, hoy, dias, umbral):
        desde = (hoy - timedelta(days=dias)).isoformat()
        mejor, ms = None, 0.0
        for hid, tk, primera in self.db.execute(
                "SELECT id, tokens, primera FROM historias WHERE ultima>=? AND primera<?", (desde, hoy.isoformat())):
            s = jaccard(tokens, set(tk.split()))
            if s > ms:
                mejor, ms = (hid, date.fromisoformat(primera)), s
        if mejor and ms >= umbral:
            return mejor
        return None

    def registrar(self, noticia, hoy, historia_id=None):
        tk = " ".join(sorted(noticia.tokens))
        if historia_id is None:
            cur = self.db.execute("INSERT INTO historias (tokens, primera, ultima) VALUES (?,?,?)",
                                  (tk, hoy.isoformat(), hoy.isoformat()))
            historia_id = cur.lastrowid
        else:
            self.db.execute("UPDATE historias SET ultima=?, tokens=? WHERE id=?", (hoy.isoformat(), tk, historia_id))
        self.db.execute("INSERT OR REPLACE INTO enviados (url, titulo, fecha, historia) VALUES (?,?,?,?)",
                        (noticia.enlace, noticia.titulo[:200], hoy.isoformat(), historia_id))

    # ---------------------------------------------------------- mercados
    def guardar_serie(self, serie, puntos):
        self.db.executemany("INSERT OR REPLACE INTO mercados (serie, fecha, valor) VALUES (?,?,?)",
                            [(serie, f, v) for f, v in puntos if v is not None])

    def serie(self, serie, n=30):
        filas = self.db.execute("SELECT fecha, valor FROM mercados WHERE serie=? ORDER BY fecha DESC LIMIT ?",
                                (serie, n)).fetchall()
        return list(reversed(filas))

    # ---------------------------------------------------------- general
    def registrar_ejecucion(self, hoy, modo, revisados, publicados):
        self.db.execute("INSERT OR REPLACE INTO ejecuciones VALUES (?,?,?,?)",
                        (hoy.isoformat(), modo, revisados, publicados))

    def limpiar(self, hoy):
        """Mantiene el archivo pequeño."""
        self.db.execute("DELETE FROM enviados WHERE fecha<?", ((hoy - timedelta(days=45)).isoformat(),))
        self.db.execute("DELETE FROM historias WHERE ultima<?", ((hoy - timedelta(days=45)).isoformat(),))
        self.db.execute("DELETE FROM mercados WHERE fecha<?", ((hoy - timedelta(days=120)).isoformat(),))
        self.db.execute("DELETE FROM ejecuciones WHERE fecha<?", ((hoy - timedelta(days=90)).isoformat(),))

    def cerrar(self):
        self.db.commit()
        self.db.execute("VACUUM")
        self.db.close()
