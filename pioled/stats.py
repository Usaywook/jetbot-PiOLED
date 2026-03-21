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

import time

import board
import busio
import adafruit_ssd1306

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import os
import subprocess


def get_network_interface_state(interface):
    return subprocess.check_output('cat /sys/class/net/%s/operstate' % interface, shell=True).decode('ascii')[:-1]


def get_ip_address(interface):
    try:
        if get_network_interface_state(interface) == 'down':
            return None
        cmd = "ifconfig %s | grep -Eo 'inet (addr:)?([0-9]*\\.){3}[0-9]*' | grep -Eo '([0-9]*\\.){3}[0-9]*' | grep -v '127.0.0.1'" % interface
        return subprocess.check_output(cmd, shell=True).decode('ascii')[:-1]
    except subprocess.CalledProcessError:
        return None


def get_active_interface():
    """eth0 고정 대신 첫 번째 up 상태의 유선/무선 인터페이스를 반환"""
    skip = {'lo', 'docker0', 'l4tbr0'}
    try:
        ifaces = os.listdir('/sys/class/net')
    except OSError:
        return None
    for iface in sorted(ifaces):
        if iface in skip or iface.startswith('veth'):
            continue
        try:
            state = get_network_interface_state(iface)
            if state == 'up':
                return iface
        except subprocess.CalledProcessError:
            continue
    return None

# Return a string representing the percentage of CPU in use


def get_cpu_usage():
    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
    CPU = subprocess.check_output(cmd, shell=True)
    return CPU

# Return a float representing the percentage of GPU in use.
# On the Jetson, the GPU is GPU0


def get_gpu_usage():
    GPU = 0.0
    try:
        with open("/sys/devices/gpu.0/load", encoding="utf-8") as gpu_file:
            GPU = gpu_file.readline()
            GPU = int(GPU) / 10
    except (FileNotFoundError, IOError):
        pass
    return GPU


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

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0

# Load default font.
font = ImageFont.load_default()

while True:

    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Shell scripts for system monitoring from here : https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "free -m | awk 'NR==2{printf \"Mem:  %.0f%% %s/%s M\", $3*100/$2, $3,$2 }'"
    MemUsage = subprocess.check_output(cmd, shell=True)
    cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
    Disk = subprocess.check_output(cmd, shell=True)

    # Print the IP address (인터페이스 이름 자동 감지: eth0 고정 제거)
    iface = get_active_interface() or 'N/A'
    ip = str(get_ip_address(iface)) if iface != 'N/A' else 'N/A'
    draw.text((x, top), iface + ": " + ip, font=font, fill=255)

    # Alternate solution: Draw the GPU usage as text
    # draw.text((x, top+8),     "GPU:  " +"{:3.1f}".format(GPU)+" %", font=font, fill=255)
    # We draw the GPU usage as a bar graph
    # Pillow >= 10.0: getsize() 제거됨 → getlength() 사용
    string_width = int(font.getlength("GPU:  "))
    # Figure out the width of the bar
    full_bar_width = width - (x + string_width) - 1
    gpu_usage = get_gpu_usage()
    # Avoid divide by zero ...
    if gpu_usage == 0.0:
        gpu_usage = 0.001
    draw_bar_width = int(full_bar_width * (gpu_usage / 100))
    draw.text((x, top + 8),     "GPU:  ", font=font, fill=255)
    draw.rectangle((x + string_width, top + 12, x + string_width +
                    draw_bar_width, top + 14), outline=1, fill=1)

    # Show the memory Usage
    draw.text((x, top + 16), str(MemUsage.decode('utf-8')), font=font, fill=255)
    # Show the amount of disk being used
    draw.text((x, top + 25), str(Disk.decode('utf-8')), font=font, fill=255)

    # Display image.
    # Set the SSD1306 image to the PIL image we have made, then display
    disp.image(image)
    disp.show()
    # 1.0 = 1 second; The divisor is the desired updates (frames) per second
    time.sleep(1.0 / 4)
