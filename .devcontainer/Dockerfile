FROM nvcr.io/nvidia/l4t-jetpack:r36.4.0

ENV DEBIAN_FRONTEND=noninteractive

# I2C / GPIO 핵심 시스템 패키지
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    i2c-tools \
    python3-smbus \
    libgpiod-dev \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# JP6 호환 Python 의존성 (구버전 Adafruit_SSD1306 대신 CircuitPython 사용)
RUN pip3 install --no-cache-dir \
    adafruit-circuitpython-ssd1306 \
    adafruit-blinka \
    Jetson.GPIO \
    pillow \
    numpy

WORKDIR /app
COPY . .

CMD ["python3", "-m", "pioled.stats"]
