# installPiOLED
Install the Adafruit PiOLED 128x32 Monochrome OLED driver (3527)

Original article on JetsonHacks: https://wp.me/p7ZgI9-33H

The Adafruit PiOLED is a handy little display that connects to the Jetson Nano GPIO header. The display communicates with the Jetson over I2C, and is powered via the GPIO pins.

There are two scripts here, along with an file which displays information on the display. The file is pioled/stats.py. Gernerally you will modify the stats.py file to meet your needs. The default is to show the eth0 address, an updating GPU usage bar graph, memory usage and disk usage.

The first script, installPiOLED.sh will install the Adafruit-SSD1306 library. The SSD1306 is the driver chip for the PiOLED. Note that we use pip3 to install this library. Usage:

<blockquote>$ ./installPiOLED.sh</blockquote>

Once the library is installs, you can then run the example:

<blockquote>$ cd pioled<br>
$ python3 stats.py</blockquote>

If you would like to run the display stats app on system startup, the createService.sh script will install the stats app as a global library in /usr/local/lib/ as pioled, and create a startup service to launch. The startup service is in /etc/systemd/system/pioled_stats.service

To create the service:

<blockquote>$ ./createService.sh</blockquote>

You should consider filling out the setup.py file in the top directory more fully for your application. 
  
<h3>JetPack 6 Docker 지원</h3>

원본 코드는 JetPack 4.x / Jetson Nano 기준으로 작성되어 있습니다. JetPack 6.x 환경에서 Docker 컨테이너로 동작시키기 위해 아래와 같이 수정하였습니다.

<h4>변경 사항</h4>

| 항목 | 기존 (JP4) | 변경 후 (JP6 Docker) |
|---|---|---|
| 베이스 환경 | Jetson Nano 호스트 | `nvcr.io/nvidia/l4t-jetpack:r36.4.0` 컨테이너 |
| OLED 라이브러리 | `Adafruit-SSD1306` (deprecated) | `adafruit-circuitpython-ssd1306` + `adafruit-blinka` |
| I2C 초기화 | `Adafruit_SSD1306.SSD1306_128_32(rst=None, i2c_bus=1, gpio=1)` | `busio.I2C(board.SCL, board.SDA)` |
| 디스플레이 API | `disp.begin()` / `disp.clear()` / `disp.display()` | `disp.fill(0)` / `disp.show()` |
| Pillow 폰트 API | `font.getsize()` (Pillow 10에서 제거됨) | `font.getlength()` |
| 서비스 등록 | systemd (`createService.sh`) | Docker ENTRYPOINT (컨테이너 내 불필요) |
| 네트워크/GPIO 오류 | 예외 처리 없음 | `try/except` 추가 |

추가된 파일:
* `.devcontainer/Dockerfile` — JP6 베이스 이미지 및 의존성 정의
* `.devcontainer/devcontainer.json` — VS Code Dev Container 설정 (I2C/GPIO 접근을 위한 `--privileged`, `/dev`, `/sys` 마운트 포함)

<h4>동작 확인 절차</h4>

**1. 호스트에서 OLED 연결 확인**

OLED가 I2C에 정상 연결되어 있는지 확인합니다. `0x3c` 주소가 나타나면 OK입니다.

Jetson Orin Nano의 경우 40-pin GPIO 헤더 I2C 버스는 bus 7입니다. Quick Write 방식으로는 SSD1306이 응답하지 않으므로 `-r` (Read 방식)을 사용합니다.

<blockquote>$ i2cdetect -y -r 7</blockquote>

버스 번호가 불확실한 경우 먼저 전체 버스를 확인하세요.

<blockquote>$ i2cdetect -l</blockquote>

**2. Docker 이미지 빌드**

<blockquote>$ docker build -f .devcontainer/Dockerfile -t pioled-jp6 .</blockquote>

**3. 컨테이너 실행**

I2C 및 GPIO 접근을 위해 `--privileged`와 `/dev`, `/sys` 마운트가 필수입니다.

<blockquote>$ sudo docker run -it --rm \<br>
&nbsp;&nbsp;--runtime nvidia \<br>
&nbsp;&nbsp;--network host \<br>
&nbsp;&nbsp;--privileged \<br>
&nbsp;&nbsp;-v /dev:/dev \<br>
&nbsp;&nbsp;-v /sys:/sys \<br>
&nbsp;&nbsp;pioled-jp6</blockquote>

**4. VS Code Dev Container로 열기**

VS Code에서 `Reopen in Container`를 선택하면 `.devcontainer/devcontainer.json` 설정이 자동으로 적용됩니다.

**5. 컨테이너 내부에서 직접 실행 (개발/테스트용)**

<blockquote>$ python3 -m pioled.stats</blockquote>

<h3>Notes</h3>

<h4>March, 2026</h4>
JetPack 6 Docker 지원 추가

* JetPack 6.2 (L4T r36.4.0)
* Docker 컨테이너 환경
* adafruit-circuitpython-ssd1306 라이브러리로 교체

<h4>December, 2019</h4>
Initial Release

* Jetson Nano
* L4T 32.2.1/JetPack 4.2.2
