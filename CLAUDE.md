# CLAUDE.md

이 파일은 Claude Code가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 프로젝트 개요

Adafruit PiOLED (128x32 모노 OLED, SSD1306) 위에 Jetson 시스템 상태(IP/GPU/메모리/디스크)를 표시하는 작은 파이썬 앱입니다.

원본은 JetsonHacksNano/installPiOLED (JetPack 4.x / Jetson Nano, `Adafruit-SSD1306` 기반)이며, 이 포크는 **JetPack 6.x / Jetson Orin Nano + Docker 컨테이너**에서 동작하도록 다시 작성되었습니다. 업스트림은 `upstream` 리모트로 보존되어 있고 (`JetsonHacksNano/installPiOLED`), 작업 푸시 대상은 `origin` (`Usaywook/jetbot-PiOLED`) 입니다.

## 실행 환경

- 하드웨어: Jetson Orin Nano (Jetpack 6.2, L4T r36.4.0)
- I2C 버스: **bus 7** (40-pin GPIO 헤더). SSD1306은 quick-write에 응답하지 않으므로 `i2cdetect`는 반드시 `-r` 로 검사: `i2cdetect -y -r 7`
- 컨테이너 베이스 이미지: `nvcr.io/nvidia/l4t-jetpack:r36.4.0`
- OLED 주소: `0x3c`

JP4 시절의 `createService.sh` / systemd 경로는 컨테이너 환경에서 사용하지 않습니다. 호스트에 직접 깔고 싶을 때만 참조용으로 남아 있습니다.

## 코드 구조

- `pioled/stats.py` — 메인 루프. 4 FPS로 2×2 그리드를 그립니다: 1행 `GPU% | MEM%`, 2행 `DISK% | TEMP°`. 수정 대상은 보통 이 파일 하나.
- `pioled/alerts.py` — Slack webhook 온도 알림. import 시점에 env 를 읽어 모듈 레벨 `alert_state` 싱글톤(`AlertState` 또는 `None`)을 노출. `stats.py` 는 매 tick `alert_state.update(temp)` 만 호출.
- `pioled/__init__.py` — 패키지 표식 (비어있음).
- `.devcontainer/Dockerfile` — JP6 베이스 + CircuitPython 의존성. `CMD ["python3", "-m", "pioled.stats"]`.
- `.devcontainer/devcontainer.json` — VS Code Dev Container. I2C/GPIO 접근을 위해 `--privileged` + `/dev`, `/sys` 바인드 마운트 포함.
- `run.sh` — 컨테이너를 `-d --name pioled` 로 띄움. `--rm` 없음 → 재시작은 `docker restart pioled`. `.env` 가 있으면 자동으로 `--env-file .env` 로 주입.
- `.env.example` — Slack 알림 설정 템플릿. `.env` 로 복사 후 채워서 사용 (`.env` 는 gitignore).
- `setup.py` / `installPiOLED.sh` / `createService.sh` / `utils/create_stats_service.py` — JP4 시절 호스트 설치/systemd 경로. **JP6 Docker 흐름에서는 사용하지 않음.** 의존성도 `Adafruit-SSD1306` 으로 옛것이라 그대로 두면 동작 안 함.

## JP6 마이그레이션에서 바뀐 부분 (수정 시 깨지지 않도록 주의)

| 항목 | JP4 (원본) | JP6 (현재) |
|---|---|---|
| OLED 라이브러리 | `Adafruit_SSD1306` (deprecated) | `adafruit-circuitpython-ssd1306` + `adafruit-blinka` |
| I2C 초기화 | `SSD1306_128_32(rst=None, i2c_bus=1, gpio=1)` | `busio.I2C(board.SCL, board.SDA)` → `SSD1306_I2C(128, 32, i2c)` |
| 디스플레이 호출 | `disp.begin()` / `disp.clear()` / `disp.display()` | `disp.fill(0)` / `disp.show()` |
| 폰트 폭 측정 | `font.getsize()` (Pillow 10에서 제거) | `font.getlength()` |
| GPU load 경로 | `/sys/devices/gpu.0/load` | `/sys/devices/platform/bus@0/17000000.gpu/load` (`stats.py` 의 `get_gpu_usage()` 가 두 경로를 fallback) |
| 표시 항목 | IP / GPU 막대 / Mem / Disk (4줄, 8px 폰트) | GPU% / MEM% / DISK% / TEMP° — 2×2 그리드 (10px 폰트) |
| 온도 소스 | 없음 | `/sys/class/thermal/thermal_zone*` 중 `type==tj-thermal` 자동 탐색 → m°C/1000 |

`stats.py` 의 그리기 좌표는 10px 폰트 + 128×32 디스플레이의 2×2 분할(`ROW_Y=(2,18)`, `LEFT_X=0` / `DIV_X≈62` / `RIGHT_X≈68`)을 가정합니다. 폰트 크기나 라벨 길이를 바꾸면 우측 컬럼이 잘릴 수 있습니다.

## Slack 온도 알림 (옵션)

`stats.py` 는 junction 온도가 임계값을 넘으면 Slack incoming webhook 으로 알림을 보냅니다. 4 FPS 루프와 무관하게 daemon 스레드에서 POST 하므로 OLED 갱신이 막히지 않습니다. **히스테리시스 + sustain 타이머** 적용 — 짧은 스파이크는 무시하고, 양방향 모두 일정 시간 지속됐을 때만 메시지를 보냅니다.

활성화:
```
cp .env.example .env
# .env 에 SLACK_WEBHOOK_URL 등 채움
docker rm -f pioled && ./run.sh   # 새 env-file 반영하려면 컨테이너 재생성 필요
```

환경변수:

| 변수 | 의미 | 비고 |
|---|---|---|
| `SLACK_WEBHOOK_URL` | Slack incoming webhook | 비어있거나 미설정 → 알림 기능 OFF (OLED 표시는 정상) |
| `TEMP_ALERT_C` | 임계 온도 (°C) | Orin Nano throttle 시작점 ~80°C |
| `TEMP_ALERT_SUSTAIN_S` | 임계 이상 지속 시간 | 이 시간 이상 유지되면 `[ALERT]` 발송 |
| `TEMP_CLEAR_SUSTAIN_S` | 임계 미만 지속 시간 | 이 시간 이상 유지되면 `[OK]` 발송 |

값이 잘못되었거나 비어있으면 코드 내 기본값(80°C / 30s / 60s) 적용 + stderr 로 경고. Webhook 호출 실패는 stderr 로만 로그하고 루프는 계속 돕니다.

## 자주 쓰는 명령

I2C 확인:
```
i2cdetect -l            # 버스 목록
i2cdetect -y -r 7       # bus 7 에서 0x3c 확인 (반드시 -r)
```

빌드 & 실행:
```
docker build -f .devcontainer/Dockerfile -t pioled-jp6 .
./run.sh                # 백그라운드(-d)로 띄움. 재시작은 docker restart pioled
```

원샷 실행 (개발/디버깅용 — 컨테이너 자동 삭제):
```
sudo docker run -it --rm \
  --runtime nvidia --network host --privileged \
  -v /dev:/dev -v /sys:/sys \
  pioled-jp6
```

컨테이너 내부에서 직접:
```
python3 -m pioled.stats
```

## Git 리모트

- `origin` → `https://github.com/Usaywook/jetbot-PiOLED.git` (이 포크, 푸시 대상)
- `upstream` → `https://github.com/JetsonHacksNano/installPiOLED.git` (원본, fetch only)
