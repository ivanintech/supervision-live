#!/bin/bash
# Arranque + verificación estándar del repo. Sin pasos manuales.
#   ./init.sh        arranca, verifica y deja los servidores corriendo
#   ./init.sh stop   para los servidores de verificación
set -u
cd "$(dirname "$0")"

PY="./.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3 || command -v python)"

SRC_PORT=18095
CAM_PORT=18090

stop_servers() {
  for port in "$SRC_PORT" "$CAM_PORT"; do
    pid=$(ss -ltnp 2>/dev/null | grep ":$port " | grep -oP 'pid=\K[0-9]+' | head -1)
    [ -n "${pid:-}" ] && kill "$pid" 2>/dev/null && echo "parado :$port (pid $pid)"
  done
  return 0
}

if [ "${1:-}" = "stop" ]; then
  stop_servers
  exit 0
fi

echo "=== 1/3 entorno ==="
if [ -x ./.venv/bin/python ]; then
  "$PY" -c "import cv2, numpy, supervision, ultralytics, trackers; print('deps OK')" || exit 1
else
  echo "AVISO: no hay .venv — corre: uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt"
  exit 1
fi

echo "=== 2/3 sintaxis ==="
"$PY" -m compileall -q -x '(^|/)(\.?venv|env|build|dist|__pycache__)(/|$)' . && echo "sintaxis OK" || exit 1

echo "=== 3/3 pipeline (fuente sintética, sin móvil) ==="
# Puertos ocupados de una ejecución anterior: se liberan por PID del puerto,
# nunca con `pkill -f <script>` (el cmdline del shell contiene el mismo texto
# y el script se mataría a sí mismo).
stop_servers >/dev/null

# setsid -f: fork + desprenderse del grupo de procesos. Sin esto, quien invoque
# este script (runner de terminal, CI) mata los servidores al terminar el comando.
TEST_SOURCE_PORT=$SRC_PORT setsid -f "$PY" test_source.py >/tmp/sl_src.log 2>&1

# Comprobar el puerto, NO bajar el stream: /video es multipart infinito, así que
# curl se queda leyendo hasta agotar --max-time y devuelve 28 (parece un fallo y no lo es).
# Un 404 en / confirma que el servidor HTTP está vivo y respondiendo.
src_ready=0
for _ in $(seq 1 10); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 2 "http://127.0.0.1:$SRC_PORT/" 2>/dev/null || true)
  [ "$code" = "404" ] && { src_ready=1; break; }
  sleep 1
done
if [ "$src_ready" = "0" ]; then
  echo "generador sintético no responde"; cat /tmp/sl_src.log; exit 1
fi

setsid -f "$PY" live_cam.py --source "http://127.0.0.1:$SRC_PORT/video" --port $CAM_PORT >/tmp/sl_cam.log 2>&1

OUT=""
for _ in $(seq 1 25); do
  sleep 2
  OUT=$(curl -s --max-time 3 "http://127.0.0.1:$CAM_PORT/stats" 2>/dev/null || true)
  echo "$OUT" | grep -q '"source_ok": true' && break
done

echo "stats: ${OUT:-sin respuesta}"
if echo "$OUT" | grep -q '"source_ok": true'; then
  echo "PIPELINE OK — stream en http://127.0.0.1:$CAM_PORT/video  (para: ./init.sh stop)"
  exit 0
fi
echo "--- log live_cam ---"; tail -20 /tmp/sl_cam.log
echo "PIPELINE FALLO"; exit 1
