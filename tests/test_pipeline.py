"""Tests de humo del pipeline de detección + tracking.

No levantan servidores ni el móvil: ejercitan YOLO y ByteTrack directamente
sobre una escena con objetos reales desplazándose, que es lo que falla cuando
cambia la API de alguna librería.

    pytest -q
"""
import os

import cv2
import numpy as np
import pytest
import supervision as sv
from trackers import ByteTrackTracker
from ultralytics import YOLO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSET = os.path.join(ROOT, "assets", "bus.jpg")
FRAME_W, FRAME_H = 640, 360


@pytest.fixture(scope="session")
def model():
    # ultralytics descarga yolo11n.pt la primera vez
    return YOLO("yolo11n.pt")


@pytest.fixture(scope="session")
def scene():
    assert os.path.isfile(ASSET), f"falta la imagen de prueba: {ASSET}"
    img = cv2.imread(ASSET)
    assert img is not None
    scale = FRAME_H / img.shape[0]
    return cv2.resize(img, (int(img.shape[1] * scale), FRAME_H))


def make_frame(scene, x):
    """Lienzo con la escena colocada en la coordenada x (puede salirse)."""
    frame = np.full((FRAME_H, FRAME_W, 3), 24, dtype=np.uint8)
    w = scene.shape[1]
    x0, x1 = max(0, x), min(FRAME_W, x + w)
    if x1 > x0:
        frame[:, x0:x1] = scene[:, x0 - x:x1 - x]
    return frame


def test_detecta_objetos_reales(model, scene):
    """El detector tiene que ver objetos en una escena con personas y vehículos."""
    res = model(make_frame(scene, 0), conf=0.3, verbose=False)[0]
    detections = sv.Detections.from_ultralytics(res)
    assert len(detections) > 0, "YOLO no detectó nada: ¿modelo o pesos corruptos?"
    clases = {model.names[int(c)] for c in detections.class_id}
    assert clases & {"person", "bus"}, f"clases inesperadas: {clases}"


def test_tracker_asigna_ids_estables(model, scene):
    """El tracker mantiene el ID del mismo objeto mientras se desplaza.

    Un `tracker_id == -1` significa "detección no confirmada todavía"
    (ByteTrack exige N frames consecutivos). No es inestabilidad: se descarta.
    """
    tracker = ByteTrackTracker(frame_rate=25, track_activation_threshold=0.25)
    vistos = []
    for x in range(0, 200, 20):
        res = model(make_frame(scene, x), conf=0.3, verbose=False)[0]
        det = tracker.update(sv.Detections.from_ultralytics(res))
        if det.tracker_id is not None:
            vistos.extend(int(t) for t in det.tracker_id if int(t) >= 0)

    assert vistos, "el tracker no confirmó ningún ID en 10 frames"
    confirmados = set(vistos)
    comunes = confirmados & set(vistos[-len(confirmados):])
    assert len(comunes) >= 1, f"IDs sin continuidad entre frames: {vistos}"


def test_ids_no_negativos_en_anotacion():
    """La anotación no debe pintar IDs -1 como si fueran válidos.

    Regresión: antes el stream mostraba etiquetas tipo `person #-1`.
    """
    from live_cam import format_label

    det = sv.Detections(
        xyxy=np.array([[10, 10, 50, 50]], dtype=float),
        class_id=np.array([0]),
        tracker_id=np.array([-1]),
    )
    assert format_label(det, 0, {0: "person"}) == "person (nuevo)"

    det.tracker_id = np.array([7])
    assert format_label(det, 0, {0: "person"}) == "person #7"
