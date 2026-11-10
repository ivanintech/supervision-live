# PROGRESS.md

Registro de sesión, más reciente arriba. Estado verificado, no intenciones.

---

## 2026-11-10 (tarde) — Detección real, tests y repo público

**Qué se hizo**
- **El bloqueo de `core-002` era de la fuente, no del código**: `test_source.py` dibujaba un
  rectángulo abstracto que COCO no reconoce → `detections` siempre 0 y el tracker nunca se
  ejercitaba. Ahora anima imágenes reales de `assets/` desplazándose por el lienzo.
- Pensado para objeto detectable, apareció un bug de anotación: ByteTrack devuelve
  `tracker_id == -1` en detecciones no confirmadas y el stream pintaba **`person #-1`**.
  Extraído a `format_label()` y cubierto con test de regresión.
- `probe_tracking.py` (script suelto que imprimía "FALLO" por un criterio demasiado estricto)
  sustituido por `tests/test_pipeline.py`: 3 tests que corren sin red ni móvil.
- `init.sh` pasa a 4 fases: entorno → sintaxis → **tests** → pipeline.
- `requirements.txt` con versiones exactas (antes `>=`) + `requirements.lock` con las 72
  transitivas. `pytest` como dependencia de desarrollo.
- README reescrito: el *por qué* en la primera línea, badges de salida real, tabla de
  arquitectura y sección "detalles que costaron encontrar".
- **Repo publicado**: https://github.com/ivanintech/supervision-live (público).

**Estado verificado**
- `./init.sh` → **exit 0, 3 de 3 ejecuciones seguidas** con detecciones reales
  (`detections: 4 / 2 / 4`, `counts: {"bus": 1, "person": 3}`).
- `tests/`: **3 passed** (detección, estabilidad de IDs, etiqueta de anotación).
- `init.sh` ya no acepta `source_ok` a secas: exige `detections >= 1`. Antes daba verde con
  0 objetos (la vista instantánea caía entre escenas) — falso positivo.
- Captura `docs-demo.jpg`: cajas con `person #4`, `person #0`, `tie (nuevo)` y HUD
  `122 FPS | OBJ: 3 | person:2 tie:1`.

**Siguiente paso**
- `core-002` cerrada. Candidatos, por orden de valor para el repo:
  1. Exportar trayectorias (líneas de recorrido / conteo por zona con `sv.LineZone`).
  2. Soporte RTSP además de MJPEG (misma interfaz, `cv2.VideoCapture` sirve ambos).
  3. Probar en GPU (RTX 3070 Laptop): `--model yolo11s.pt` y medir FPS reales.

**Riesgos / bloqueos**
- `assets/` (188 KB) va versionado: son las imágenes de prueba de los tests y del generador.
  Si crece, mover a descarga bajo demanda rompería el arranque offline.
- Sin GPU: `yolo11n` a 640 px entre 50 y 150 FPS, pero el generador es más rápido que una
  cámara real — el número con móvil será menor.
- No probado en Windows ni macOS.
