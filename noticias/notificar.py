"""Canales opcionales (apagados por defecto): Telegram y correo (SMTP de Gmail).

Si están apagados o faltan los secretos, no hacen nada y no producen errores.
Secretos (GitHub Secrets):
  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  GMAIL_USUARIO, GMAIL_CLAVE_APP, CORREO_DESTINO
"""
import os
import smtplib
from email.mime.text import MIMEText
from html import escape

from .utils import http_post


def _texto(elegidas, url, fecha):
    lineas = [f"Noticias diarias · {fecha}"]
    for n in elegidas[:12]:
        lineas.append(f"• {n.titulo} ({n.fuente})\n  {n.enlace}")
    if url:
        lineas.append(f"\nPágina completa: {url}")
    return "\n".join(lineas)


def telegram(cfg, elegidas, fecha, log=print):
    c = (cfg.get("canales", {}) or {}).get("telegram", {}) or {}
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not c.get("activo") or not token or not chat:
        return
    try:
        url = (cfg.get("pagina", {}) or {}).get("url_publica", "")
        r = http_post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": _texto(elegidas, url, fecha)[:4000],
                            "disable_web_page_preview": True}, timeout=20)
        log(f"Telegram: {'enviado' if r.ok else 'falló (' + str(r.status_code) + ')'}")
    except Exception as ex:  # noqa: BLE001
        log(f"Telegram: no se pudo enviar ({type(ex).__name__})")


def correo(cfg, elegidas, fecha, log=print):
    c = (cfg.get("canales", {}) or {}).get("correo", {}) or {}
    usuario, clave = os.environ.get("GMAIL_USUARIO"), os.environ.get("GMAIL_CLAVE_APP")
    destino = os.environ.get("CORREO_DESTINO") or usuario
    if not c.get("activo") or not usuario or not clave:
        return
    try:
        url = (cfg.get("pagina", {}) or {}).get("url_publica", "")
        items = "".join(f'<li><a href="{escape(n.enlace)}">{escape(n.titulo)}</a> <small>({escape(n.fuente)})</small></li>'
                        for n in elegidas[:15])
        cuerpo = f"<h2>Noticias diarias · {escape(fecha)}</h2><ul>{items}</ul>"
        if url:
            cuerpo += f'<p><a href="{escape(url)}">Ver la página completa</a></p>'
        msg = MIMEText(cuerpo, "html", "utf-8")
        msg["Subject"] = f"Noticias diarias · {fecha}"
        msg["From"], msg["To"] = usuario, destino
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as s:
            s.login(usuario, clave)
            s.send_message(msg)
        log("Correo: enviado")
    except Exception as ex:  # noqa: BLE001
        log(f"Correo: no se pudo enviar ({type(ex).__name__})")
