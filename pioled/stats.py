#! /usr/bin/python3
# Copyright (c) 2017 Adafruit Industries
# Author: Tony DiCola & James DeVito
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# Portions copyright (c) NVIDIA 2019
# Portions copyright (c) JetsonHacks 2019
#
# JP6 (JetPack 6.x) Docker 호환 버전
#   - Adafruit_SSD1306 (deprecated) → adafruit-circuitpython-ssd1306 으로 교체
#   - Pillow >= 10.0: font.getsize() 제거 → font.getlength() 사용
#   - I2C 초기화: busio.I2C(board.SCL, board.SDA)

import os
import subprocess
import time

import board
import busio
import adafruit_ssd1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

from pioled.alerts import alert_state


def get_gpu_usage():
    # JP4: /sys/devices/gpu.0/load
    # JP6 (Orin Nano): /sys/devices/platform/bus@0/17000000.gpu/load
    candidates = [
        "/sys/devices/gpu.0/load",
        "/sys/devices/platform/bus@0/17000000.gpu/load",
    ]
    for path in candidates:
        try:
            with open(path, encoding="utf-8") as f:
                return int(f.readline()) / 10
        except (FileNotFoundError, IOError):
            continue
    return 0.0


def get_mem_usage_pct():
    cmd = "free -m | awk 'NR==2{printf \"%.0f\", $3*100/$2}'"
    return int(subprocess.check_output(cmd, shell=True).decode("ascii"))


def get_disk_usage_pct():
    cmd = "df / | awk 'NR==2{gsub(/%/,\"\",$5); print $5}'"
    return int(subprocess.check_output(cmd, shell=True).decode("ascii"))


def _find_tj_zone():
    """Return the thermal_zone path whose type is 'tj-thermal' (Orin junction temp)."""
    base = "/sys/class/thermal"
    try:
        zones = sorted(z for z in os.listdir(base) if z.startswith("thermal_zone"))
    except OSError:
        return None
    for z in zones:
        try:
            with open(os.path.join(base, z, "type"), encoding="utf-8") as f:
                if f.read().strip() == "tj-thermal":
                    return os.path.join(base, z, "temp")
        except (FileNotFoundError, IOError):
            continue
    return None


_TEMP_PATH = _find_tj_zone()


def get_temp_c():
    if _TEMP_PATH is None:
        return None
    try:
        with open(_TEMP_PATH, encoding="utf-8") as f:
            milli = int(f.readline().strip())
        return milli / 1000.0
    except (FileNotFoundError, IOError, ValueError):
        return None


# I2C 초기화 (JP6: busio 사용, 구버전 gpio 핵 불필요)
i2c = busio.I2C(board.SCL, board.SDA)
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Clear display (JP6: fill(0) + show())
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# 128x32 디스플레이를 2x2 그리드로 사용: 좌/우 절반 × 두 줄
# Pillow >= 10.0: size=10 비트맵 폰트 (8px → 10px 키움)
font = ImageFont.load_default(size=10)

# 두 줄을 32px 안에 세로 중심 정렬: y=2 (높이10) / y=18 (높이10), 위/아래 2px 패딩
ROW_Y = (2, 18)
# 좌/우 분할 컬럼 X 좌표 + 가운데 구분자
LEFT_X = 0
DIV_X = width // 2 - 2   # 62
RIGHT_X = width // 2 + 4  # 68

while True:

    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    gpu = get_gpu_usage()
    try:
        mem = get_mem_usage_pct()
    except (subprocess.CalledProcessError, ValueError):
        mem = 0
    try:
        disk = get_disk_usage_pct()
    except (subprocess.CalledProcessError, ValueError):
        disk = 0
    temp = get_temp_c()
    temp_str = "{:.0f}°".format(temp) if temp is not None else "--°"

    if alert_state is not None:
        alert_state.update(temp)

    # Row 1: GPU | MEM
    draw.text((LEFT_X, ROW_Y[0]),  "GPU {:.0f}%".format(gpu),  font=font, fill=255)
    draw.text((DIV_X,  ROW_Y[0]),  "|", font=font, fill=255)
    draw.text((RIGHT_X, ROW_Y[0]), "MEM {}%".format(mem),      font=font, fill=255)

    # Row 2: DISK | TEMP
    draw.text((LEFT_X, ROW_Y[1]),  "DISK {}%".format(disk),    font=font, fill=255)
    draw.text((DIV_X,  ROW_Y[1]),  "|", font=font, fill=255)
    draw.text((RIGHT_X, ROW_Y[1]), "TEMP {}".format(temp_str), font=font, fill=255)

    disp.image(image)
    disp.show()
    time.sleep(1.0 / 4)
