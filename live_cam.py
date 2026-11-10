#!/usr/bin/env python3
"""
SUPERVISION LIVE — cámara del teléfono (IP Webcam MJPEG) + YOLO + ByteTrack,
servido como stream MJPEG local para verlo en el navegador.

Uso:
  python live_cam.py [--source http://IP:8080/video] [--model yolo11n.pt]
                     [--conf 0.35] [--classes 0,2] [--port 8090] [--width 640]

Endpoints:
  /video   → MJPEG anotado (abre en navegador)
  /stats   → JSON {fps, detections, counts_por_clase}
  /health  → estado de la fuente
"""
import argparse
import json
import threading
import time
from collections import Counter, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
import supervision as sv
from trackers import ByteTrackTracker
from ultralytics import YOLO

GOLD = "#D4AF37"; CYAN = "#26A69A"; ORANGE = "#E65100"

# ── Estado compartido (inferencia → HTTP) ──────────────────────────────
state = {
    "frame": None,          # JPEG anotado listo para servir
    "lock": threading.Lock(),
    "fps": 0.0,
    "detections": 0,
    "counts": {},
    "source_ok": False,
    "last_error": "",
}

class MJPEGHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send_json(self, obj):
        body = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith("/stats"):
            with state["lock"]:
                self._send_json({
                    "fps": round(state["fps"], 1),
                    "detections": state["detections"],
                    "counts": state["counts"],
                    "source_ok": state["source_ok"],
                    "error": state["last_error"],
                })
        elif self.path.startswith("/health"):
            with state["lock"]:
                self._send_json({"ok": state["source_ok"], "error": state["last_error"]})
        elif self.path.startswith("/video"):
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                while True:
                    with state["lock"]:
                        jpg = state["frame"]
                    if jpg is not None:
                        self.wfile.write(b"--frame\r\n")
                        self.wfile.write(b"Content-Type: image/jpeg\r\n")
                        self.wfile.write(f"Content-Length: {len(jpg)}\r\n\r\n".encode())
                        self.wfile.write(jpg)
                        self.wfile.write(b"\r\n")
                    time.sleep(0.04)  # ~25 fps máx
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self.send_response(404)
            self.end_headers()

def open_source(url: str, width: int):
    """Abre la fuente MJPEG con reconexión automática. Devuelve captura o None."""
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        cap.release()
        return None
    return cap

def main():
    ap = argparse.ArgumentParser(description="Supervision live — cámara del teléfono")
    ap.add_argument("--source", default="http://192.168.1.15:8080/video",
                    help="URL MJPEG/RTSP de la cámara (IP Webcam: http://IP:8080/video)")
    ap.add_argument("--model", default="yolo11n.pt")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--classes", default="",
                    help="IDs COCO separados por coma (0=person, 2=car...). Vacío = todas")
    ap.add_argument("--port", type=int, default=8090)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--rotate", type=int, default=0, choices=[0, 90, 180, 270],
                    help="Rotar el frame (IP Webcam suele entregar el sensor en landscape → 90 o 270)")
    ap.add_argument("--flip", default="none", choices=["none", "v", "h", "both"],
                    help="Espejar el frame (cámara frontal sale invertida → h)")
    args = ap.parse_args()

    class_ids = [int(x) for x in args.classes.split(",") if x.strip()] if args.classes else None

    print(f"[*] Cargando modelo {args.model} (CPU)...")
    model = YOLO(args.model)
    names = model.names if hasattr(model, "names") else {}

    # supervision >=0.31 extrajo el tracker al paquete `trackers`:
    # antes sv.ByteTrack(...).update_with_detections(d) -> ahora ByteTrackTracker().update(d)
    tracker = ByteTrackTracker(frame_rate=25, track_activation_threshold=0.25)
    box_annotator = sv.BoxAnnotator(color=sv.ColorPalette.from_hex([GOLD, CYAN, ORANGE]),
                                    thickness=2)
    label_annotator = sv.LabelAnnotator(text_scale=0.55, text_thickness=2,
                                        text_color=sv.Color.WHITE, text_padding=6)

    httpd = ThreadingHTTPServer(("0.0.0.0", args.port), MJPEGHandler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"[*] Stream: http://localhost:{args.port}/video  |  Stats: http://localhost:{args.port}/stats")

    cap = None
    fps_window = deque(maxlen=30)
    consecutive_failures = 0

    while True:
        # Reconexión si no hay fuente
        if cap is None:
            state["source_ok"] = False
            state["last_error"] = f"sin fuente: {args.source} (abre IP Webcam en el móvil)"
            cap = open_source(args.source, args.width)
            if cap is None:
                time.sleep(3)
                continue
            state["last_error"] = ""
            print(f"[+] Fuente conectada: {args.source}")

        ok, frame = cap.read()
        if not ok:
            consecutive_failures += 1
            if consecutive_failures > 15:
                cap.release()
                cap = None
                consecutive_failures = 0
                print("[!] Fuente perdida, reconectando...")
            continue
        consecutive_failures = 0

        t0 = time.perf_counter()

        # Corregir orientación del sensor (IP Webcam entrega landscape nativo)
        if args.rotate == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif args.rotate == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif args.rotate == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if args.flip == "v":
            frame = cv2.flip(frame, 0)
        elif args.flip == "h":
            frame = cv2.flip(frame, 1)
        elif args.flip == "both":
            frame = cv2.flip(frame, -1)

        # Escalar a ancho fijo (CPU-friendly)
        h, w = frame.shape[:2]
        if w > args.width:
            scale = args.width / w
            frame = cv2.resize(frame, (args.width, int(h * scale)))

        results = model(frame, conf=args.conf, iou=0.6, verbose=False)[0]
        detections = sv.Detections.from_ultralytics(results)

        if class_ids is not None:
            mask = np.isin(detections.class_id, class_ids)
            detections = detections[mask]

        detections = tracker.update(detections)

        labels = []
        for i in range(len(detections)):
            cls = names.get(int(detections.class_id[i]), "?")
            # tracker_id == -1 => detección aún sin confirmar por el tracker
            # (minimum_consecutive_frames). No es un ID válido: se etiqueta aparte.
            tid = None
            if detections.tracker_id is not None:
                raw = int(detections.tracker_id[i])
                tid = raw if raw >= 0 else None
            labels.append(f"{cls} #{tid}" if tid is not None else f"{cls} (nuevo)")

        annotated = frame.copy()
        annotated = box_annotator.annotate(scene=annotated, detections=detections)
        annotated = label_annotator.annotate(scene=annotated, detections=detections,
                                             labels=labels)

        # HUD
        fps_window.append(1.0 / max(time.perf_counter() - t0, 1e-6))
        fps = sum(fps_window) / len(fps_window)
        counts = Counter(names.get(int(c), "?") for c in detections.class_id)
        hud = f"SUPERVISION LIVE  |  {fps:.0f} FPS  |  OBJ: {len(detections)}"
        if counts:
            top = "  ".join(f"{k}:{v}" for k, v in counts.most_common(5))
            hud += f"  |  {top}"
        cv2.putText(annotated, hud, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                    (212, 175, 55), 2, cv2.LINE_AA)

        ok_jpg, buf = cv2.imencode(".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 82])
        if ok_jpg:
            with state["lock"]:
                state["frame"] = buf.tobytes()
                state["fps"] = fps
                state["detections"] = len(detections)
                state["counts"] = dict(counts)
                state["source_ok"] = True

if __name__ == "__main__":
    main()
