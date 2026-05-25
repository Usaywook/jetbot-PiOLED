---
name: pioled-autostart-off
description: Jetson 부팅 시 pioled 컨테이너가 자동으로 시작되지 않도록 Docker 재시작 정책을 비활성화합니다. 사용자가 "pioled 자동 실행 꺼", "재부팅시 자동 시작 끄기", "autostart off" 같은 요청을 할 때 사용합니다.
---

# pioled 자동 실행 OFF

Jetson 재부팅 시 `pioled` 컨테이너가 자동으로 올라오지 않도록 Docker `restart` 정책을 `no` 로 되돌립니다. 현재 실행 중인 컨테이너는 건드리지 않습니다 (지금 동작 중인 OLED 표시는 그대로 유지).

## 실행 절차

1. 컨테이너 존재 여부 확인:
   ```bash
   docker ps -a --format '{{.Names}}' | grep -x pioled
   ```
   - 결과가 없으면 이미 자동 실행할 대상이 없다고 안내하고 중단합니다.

2. 재시작 정책을 `no` 로 변경:
   ```bash
   docker update --restart=no pioled
   ```

3. 적용 확인:
   ```bash
   docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' pioled
   ```
   - 결과가 `no` 이면 성공.

## 주의

- 이 명령은 **현재 실행 중인 컨테이너를 중단하지 않습니다.** 자동 재시작만 끕니다.
- 지금 당장 컨테이너도 멈추고 싶으면 별도로 `docker stop pioled` 를 실행하라고 안내하세요 (사용자가 명시적으로 요청한 경우에만).
- 컨테이너를 삭제하려는 의도였다면 이 스킬이 아니라 `docker rm -f pioled` 를 안내해야 합니다 — 사용자에게 의도를 확인합니다.
