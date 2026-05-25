---
name: pioled-autostart-on
description: Jetson 부팅 시 pioled 컨테이너가 자동으로 시작되도록 Docker 재시작 정책을 활성화합니다. 사용자가 "pioled 자동 실행 켜", "재부팅시 자동 시작", "autostart on" 같은 요청을 할 때 사용합니다.
---

# pioled 자동 실행 ON

Jetson 재부팅 시 `pioled` 컨테이너가 자동으로 다시 올라오도록 Docker `restart` 정책을 `unless-stopped` 로 설정합니다.

## 전제 조건

- `pioled` 컨테이너가 존재해야 합니다 (`docker ps -a` 에 보여야 함).
- Docker daemon 이 호스트 부팅 시 자동 실행되어야 합니다 (Jetson 기본값: `systemctl is-enabled docker` → `enabled`).

## 실행 절차

1. 컨테이너 존재 여부 확인:
   ```bash
   docker ps -a --format '{{.Names}}' | grep -x pioled
   ```
   - 결과가 없으면 먼저 `./run.sh` 로 컨테이너를 생성하라고 안내하고 중단합니다.

2. 재시작 정책을 `unless-stopped` 로 변경:
   ```bash
   docker update --restart=unless-stopped pioled
   ```

3. 적용 확인:
   ```bash
   docker inspect -f '{{.HostConfig.RestartPolicy.Name}}' pioled
   ```
   - 결과가 `unless-stopped` 이면 성공.

4. (선택) Docker daemon 자체가 부팅 시 켜져 있는지 확인:
   ```bash
   systemctl is-enabled docker
   ```
   - `disabled` 면 사용자에게 `sudo systemctl enable docker` 를 안내합니다 (직접 실행하지 않음).

## 주의

- `--restart=always` 대신 `unless-stopped` 를 쓰는 이유: 사용자가 `docker stop pioled` 로 명시적으로 멈췄을 때는 재부팅 후에도 멈춰 있는 게 의도에 가깝습니다.
- 정책 변경은 컨테이너를 재시작하지 않습니다. 지금 멈춰 있는 컨테이너를 바로 띄우고 싶다면 `docker start pioled` 를 따로 실행하세요.
- 이 스킬은 컨테이너를 새로 만들지 않습니다. `run.sh` 를 수정하지도 않습니다 (run.sh 는 최초 생성 시에만 사용).
