# Supervision Live

Pipeline de computer vision en tiempo real: **cámara del teléfono (IP Webcam) → YOLO → ByteTrack → stream MJPEG local**.

Detector + tracker sobre vídeo en directo, con stream anotado servido por HTTP y métricas en JSON. Sin GPU, sin nube: todo corre en local.

## Requisitos

> Los pesos `yolo11n.pt` (5,4 MB) **no se versionan**: ultralytics los descarga solo la primera vez que ejecutes con el `--model` por defecto.

- Python **3.12**
- App **IP Webcam** en el móvil (Play Store, gratis) — expone la cámara como MJPEG en `http://<IP-móvil>:8080/video`

## Instalación

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
```

> El proyecto usa su **propio** `.venv`. Antes se apuntaba a `~/.agent-reach-venv`, que **no** tiene `supervision`, `cv2`, `numpy` ni `torch` — fallaba al arrancar.

## Uso

```bash
# 1. En el móvil: abre IP Webcam → botón rojo "Iniciar servidor"
# 2. En el PC:
.venv/bin/python live_cam.py \
  --source http://192.168.1.15:8080/video \
  --port 8090 --conf 0.35
```

Sin móvil a mano, el pipeline se puede validar contra el generador sintético:

```bash
.venv/bin/python test_source.py --port 8081 &     # generador MJPEG de prueba
.venv/bin/python live_cam.py --source http://localhost:8081/video
```

| Flag | Defecto | Qué hace |
|------|---------|----------|
| `--source` | `http://192.168.1.15:8080/video` | Fuente MJPEG/RTSP |
| `--model` | `yolo11n.pt` | Modelo (CPU-friendly; `yolo11s.pt` si sobra) |
| `--conf` | `0.35` | Umbral de confianza |
| `--classes` | todas | IDs COCO separados por coma: `0`=person, `2`=car, `5`=bus |
| `--port` | `8090` | Puerto del stream local |
| `--width` | `640` | Ancho de procesado (menor = más FPS en CPU) |
| `--rotate` | `0` | `90`/`180`/`270` — IP Webcam entrega el sensor en landscape |
| `--flip` | `none` | `h`/`v`/`both` — cámara frontal sale invertida → `h` |

## Endpoints

- `http://localhost:8090/video` → MJPEG anotado (boxes + ID de tracking + HUD FPS/conteos)
- `http://localhost:8090/stats` → JSON `{fps, detections, counts, source_ok, error}`
- `http://localhost:8090/health` → estado de la fuente

## Notas

- Reconexión automática: si el móvil pierde el stream, vuelve a conectar solo (15 frames fallidos → reconecta).
- CPU por defecto. Con `yolo11n` + 640 px: ~20 FPS.
- `test_source.py` → generador MJPEG sintético para validar el pipeline sin móvil (no es un test unitario).
