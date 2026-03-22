#!/bin/bash
# Run the PiOLED stats container
# --rm 없이 실행하므로 컨테이너가 유지되어 'docker restart pioled' 사용 가능

sudo docker run -d \
  --name pioled \
  --runtime nvidia \
  --network host \
  --privileged \
  -v /dev:/dev \
  -v /sys:/sys \
  pioled-jp6
