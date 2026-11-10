#!/usr/bin/env python3
"""Generador MJPEG sintético de prueba: rectángulo en movimiento + ruido."""
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import cv2
import numpy as np

FRAME_W, FRAME_H = 640, 360


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/video"):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.end_headers()
            x = 0
            try:
                while True:
                    frame = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
                    cv2.rectangle(frame, (x, 120), (x + 60, 220), (0, 200, 255), -1)
                    cv2.putText(frame, f"TEST SOURCE {time.strftime('%H:%M:%S')}",
                                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    if ok:
                        self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(buf.tobytes())}\r\n\r\n".encode())
                        self.wfile.write(buf.tobytes())
                        self.wfile.write(b"\r\n")
                    x = (x + 4) % (FRAME_W - 60)
                    time.sleep(0.05)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()


class _Server(ThreadingHTTPServer):
    """TCPServer con SO_REUSEADDR: evita que un socket en TIME_WAIT bloquee el arranque."""
    allow_reuse_address = True
    daemon_threads = True


PORT = int(os.environ.get("TEST_SOURCE_PORT", "8095"))
print(f"[test_source] MJPEG sintético en http://127.0.0.1:{PORT}/video", flush=True)
_Server(("127.0.0.1", PORT), Handler).serve_forever()
