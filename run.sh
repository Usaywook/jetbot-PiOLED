#!/bin/bash
# Run the PiOLED stats container
# --rm 없이 실행하므로 컨테이너가 유지되어 'docker restart pioled' 사용 가능

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_ARGS=()
if [ -f "$SCRIPT_DIR/.env" ]; then
  ENV_ARGS=(--env-file "$SCRIPT_DIR/.env")
fi

sudo docker run -d \
  --name pioled \
  --runtime nvidia \
  --network host \
  --privileged \
  "${ENV_ARGS[@]}" \
  -v /dev:/dev \
  -v /sys:/sys \
  pioled-jp6
