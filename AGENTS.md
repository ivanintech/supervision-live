# AGENTS.md

Instrucciones para agentes de codificación que trabajen en este repo. El objetivo no es
maximizar código: es dejar el repositorio en un estado donde la próxima sesión continúe sin adivinar.

## Overview

**qué es este sistema:** pipeline de computer vision en tiempo real. Cámara del móvil (IP Webcam,
MJPEG sobre HTTP) → detección YOLO11 (ultralytics) → tracking ByteTrack (supervision) → stream MJPEG
anotado servido por HTTP con métricas en `/stats`.

Piezas: `live_cam.py` (bucle de inferencia + servidor HTTP), `test_source.py` (generador MJPEG
sintético para probar sin móvil), `yolo11n.pt` (pesos COCO), `requirements.txt`.

## Arranque de sesión

1. `pwd` → directorio correcto.
2. Lee `PROGRESS.md` (estado verificado + siguiente paso).
3. Lee `feature_list.json` y elige **una** característica de mayor prioridad no terminada.
4. Revisa `git log --oneline -5`.
5. Ejecuta `./init.sh`.
6. Si la verificación de referencia ya falla, arréglala antes de añadir trabajo nuevo.

## Reglas

- Una característica a la vez.
- No marcar algo como hecho solo porque hay código: exige evidencia de verificación.
- No cambiar las reglas de verificación a mitad de la implementación.
- Preferir artefactos del repo a resúmenes de chat.
- No añadir dependencias pesadas (torch/tensorflow) a los tests; el pipeline debe poder
  importarse sin GPU.

## Artefactos

- `feature_list.json` — fuente de verdad del estado de las features.
- `PROGRESS.md` — registro de sesión y estado verificado (append-only, más reciente arriba).
- `init.sh` — ruta estándar de arranque y verificación.
- `session-handoff.md` — entrega compacta para sesiones largas (opcional).

## Definición de terminado

Una feature está hecha solo si: (a) el comportamiento objetivo existe, (b) la verificación se
ejecutó de verdad, (c) la evidencia quedó en `feature_list.json` o `PROGRESS.md`, y (d) el repo
arranca de cero con `./init.sh`.

## Fin de sesión

1. Actualiza `PROGRESS.md`.
2. Actualiza `feature_list.json`.
3. Anota riesgos y bloqueos abiertos.
4. Commit descriptivo si el estado es seguro.
5. Deja el repo listo para ejecutar `./init.sh` sin pasos manuales.
