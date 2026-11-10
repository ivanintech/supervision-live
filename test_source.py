#!/usr/bin/env python3
"""Generador MJPEG de prueba con contenido detectable por YOLO.

No es un test unitario: es un sustituto del móvil para poder ejercitar el
pipeline completo (detección + tracking) sin cámara.

Anima en bucle las imágenes de `assets/` desplazándolas sobre un lienzo, de
forma que el detector ve objetos reconocibles (personas, autobús) en
posiciones cambiantes → el tracker tiene movimiento real que seguir.

    python test_source.py                  # puerto 8095
    TEST_SOURCE_PORT=18095 python test_source.py
"""
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np

FRAME_W, FRAME_H = 640, 360
ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def load_scenes():
    """Carga las imágenes de assets/ escaladas a la altura del lienzo."""
    scenes = []
    if not os.path.isdir(ASSETS_DIR):
        return scenes
    for name in sorted(os.listdir(ASSETS_DIR)):
        if not name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        img = cv2.imread(os.path.join(ASSETS_DIR, name))
        if img is None:
            continue
        scale = FRAME_H / img.shape[0]
        img = cv2.resize(img, (int(img.shape[1] * scale), FRAME_H))
        scenes.append((name, img))
    return scenes


def compose(scene_img, offset, tick):
    """Coloca la escena sobre el lienzo, desplazándose horizontalmente."""
    frame = np.full((FRAME_H, FRAME_W, 3), 24, dtype=np.uint8)
    w = scene_img.shape[1]
    span = FRAME_W + w
    x = int((offset % span) - w)  # entra por la izquierda y sale por la derecha
    x0, x1 = max(0, x), min(FRAME_W, x + w)
    if x1 > x0:
        frame[:, x0:x1] = scene_img[:, x0 - x:x1 - x]
    cv2.putText(frame, f"TEST SOURCE  tick {tick}", (12, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (212, 175, 55), 2, cv2.LINE_AA)
    return frame


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _stream(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

        scenes = load_scenes()
        if not scenes:
            # Sin assets: degradar a un patrón detectable no depende de ficheros.
            print("[test_source] AVISO: no hay imágenes en assets/ — usando patrón sintético",
                  flush=True)
            scenes = [("synthetic", np.full((FRAME_H, 240, 3), 200, dtype=np.uint8))]

        offset = 0
        tick = 0
        idx = 0
        try:
            while True:
                name, img = scenes[idx % len(scenes)]
                frame = compose(img, offset, tick)
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 88])
                if ok:
                    data = buf.tobytes()
                    self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                    self.wfile.write(f"Content-Length: {len(data)}\r\n\r\n".encode())
                    self.wfile.write(data)
                    self.wfile.write(b"\r\n")
                offset += 6
                tick += 1
                # cambiar de escena cada 120 ticks (~6 s)
                if tick % 120 == 0:
                    idx += 1
                time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        if self.path.startswith("/video"):
            self._stream()
        else:
            self.send_response(404)
            self.end_headers()


class _Server(ThreadingHTTPServer):
    """TCPServer con SO_REUSEADDR: evita que un socket en TIME_WAIT bloquee el arranque."""
    allow_reuse_address = True
    daemon_threads = True


PORT = int(os.environ.get("TEST_SOURCE_PORT", "8095"))
print(f"[test_source] MJPEG de prueba en http://127.0.0.1:{PORT}/video", flush=True)
_Server(("127.0.0.1", PORT), Handler).serve_forever()
