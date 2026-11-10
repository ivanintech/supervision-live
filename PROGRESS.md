# PROGRESS.md

Registro de sesión, más reciente arriba. Estado verificado, no intenciones.

---

## 2026-11-10 — Harness mínimo + venv propio

**Qué se hizo**
- Añadido harness mínimo al repo: `AGENTS.md`, `feature_list.json`, `PROGRESS.md`, `init.sh`,
  `requirements.txt`, `.gitignore`.
- **Corregido el setup roto**: el README apuntaba a `~/.agent-reach-venv`, que no tiene
  `supervision`, `cv2`, `numpy` ni `torch`. Ahora el proyecto usa su propio `.venv` (Python 3.12)
  creado con `uv`.
- README reescrito: instalación real, flags que faltaban (`--rotate`, `--flip`), uso con fuente
  sintética para quien no tenga el móvil a mano.

**Estado verificado**
- (a registrar tras ejecutar `./init.sh` en verde)

**Siguiente paso**
- `core-002` (detección + tracker): hace falta una fuente sintética con objetos que COCO detecte;
  el rectángulo de `test_source.py` no es detectable, así que `detections` será 0 siempre.
  Candidato: renderizar una silueta/figura tipo persona o usar un vídeo de muestra en bucle.

**Riesgos / bloqueos**
- `yolo11n.pt` (5,6 MB) está en el repo; se puede versionar o ignorar, decidido no ignorar.
- Sin GPU: `yolo11n` a 640 px ronda 20 FPS en CPU.
