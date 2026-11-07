#!/usr/bin/env python3
"""Kami Lego — локальный сервер.

Запуск:  python server.py  (или двойной щелчок по start.bat)
Сайт:    http://localhost:8766/

Каждое изменение на сайте сохраняется в kami-lego-data.json
и встраивается в KamiLego.html (блок id="kamiSeed").
"""
import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.abspath(__file__))
SITE_NAME = "index.html"
SITE = os.path.join(BASE, SITE_NAME)
DATA = os.path.join(BASE, "index.json")
PORT = 8766


def read_data():
    try:
        with open(DATA, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def embed_into_html(data):
    """Встраивает данные в сам index.html, чтобы файл был самодостаточным."""
    try:
        with open(SITE, encoding="utf-8") as fh:
            html = fh.read()
    except OSError:
        return
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    tag = '<script type="application/json" id="kamiSeed">' + payload + "</script>"
    pattern = re.compile(r'<script[^>]*id="kamiSeed"[^>]*>.*?</script>', re.S)
    html = pattern.sub("", html)
    if "<body>" in html:
        html = html.replace("<body>", "<body>\n" + tag, 1)
    else:
        html += tag
    with open(SITE, "w", encoding="utf-8") as fh:
        fh.write(html)


def write_data(data):
    tmp = DATA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA)
    embed_into_html(data)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/state":
            self.send_json(200, read_data())
            return
        if self.path in ("/", ""):
            if not os.path.exists(SITE):
                self.send_text(200, "Положите файл " + SITE_NAME + " рядом с server.py")
                return
            self.path = "/" + SITE_NAME
        super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] != "/api/state":
            self.send_json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("products"), list):
                raise ValueError("bad payload")
            write_data(data)
        except Exception as exc:
            self.send_json(400, {"error": str(exc)})
            return
        self.send_json(200, {"ok": True})

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, status, text):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    data_on_start = read_data(); embed_into_html(data_on_start) if data_on_start else None; server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print("Сервер запущен: http://localhost:%d/" % PORT)
    print("Откройте этот адрес в браузере. Окно не закрывайте, Ctrl+C — остановить.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
