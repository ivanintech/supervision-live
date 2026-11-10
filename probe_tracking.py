"""Verificación de tracking: los IDs deben mantenerse estables con movimiento real."""
import cv2
import numpy as np
import supervision as sv
from trackers import ByteTrackTracker
from ultralytics import YOLO

model = YOLO("yolo11n.pt")
tracker = ByteTrackTracker(frame_rate=25, track_activation_threshold=0.25)

img = cv2.resize(cv2.imread("assets/bus.jpg"), (640, 360))
W = img.shape[1]

ids_per_frame = []
for f in range(14):
    frame = np.full((360, 640, 3), 24, dtype=np.uint8)
    x = -W + 40 + f * 40          # desplazamiento horizontal progresivo
    x0, x1 = max(0, x), min(640, x + W)
    if x1 > x0:
        frame[:, x0:x1] = img[:, x0 - x:x1 - x]
    res = model(frame, conf=0.3, verbose=False)[0]
    det = tracker.update(sv.Detections.from_ultralytics(res))
    ids = sorted(int(t) for t in det.tracker_id) if det.tracker_id is not None else []
    ids_per_frame.append(ids)

print("tracker_id por frame:")
for i, ids in enumerate(ids_per_frame):
    print(f"  f{i:02d}: {ids}")

with_ids = [f for f in ids_per_frame if f]
if not with_ids:
    print("RESULTADO: FALLO — ningún frame con tracker_id")
    raise SystemExit(1)

estables = with_ids[-1] and set(with_ids[-1]) <= set(with_ids[2] if len(with_ids) > 2 else with_ids[0])
print(f"frames con IDs: {len(with_ids)}/{len(ids_per_frame)}")
print(f"último frame: {with_ids[-1]}")
print("RESULTADO:", "OK — IDs estables" if estables else "FALLO — IDs no estables")
