"""Slack temperature alerting for the PiOLED stats loop.

On import, reads env vars once and exposes a module-level ``alert_state``:
- ``AlertState`` instance if ``SLACK_WEBHOOK_URL`` is set (alerts enabled)
- ``None`` if not set (alerts disabled — caller should skip ``.update()``)

Env vars (see ``.env.example``):
- ``SLACK_WEBHOOK_URL``      empty/unset → alerts off
- ``TEMP_ALERT_C``           threshold in °C (default 80)
- ``TEMP_ALERT_SUSTAIN_S``   seconds above threshold before [ALERT] (default 30)
- ``TEMP_CLEAR_SUSTAIN_S``   seconds below threshold before [OK]    (default 60)
"""

import json
import os
import socket
import sys
import threading
import time
import urllib.request


def _env_float(key, default):
    v = os.environ.get(key, "").strip()
    if not v:
        return default
    try:
        return float(v)
    except ValueError:
        print("[WARN] invalid {}={!r}, using {}".format(key, v, default),
              file=sys.stderr)
        return default


def post_slack(webhook_url, text):
    """Fire-and-forget webhook POST in a daemon thread so the caller's loop
    is never blocked by Slack latency or network errors."""
    if not webhook_url:
        return

    def _send():
        try:
            data = json.dumps({"text": text}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception as e:  # noqa: BLE001 — never let alerting kill the loop
            print("[WARN] Slack post failed: {}".format(e), file=sys.stderr)

    threading.Thread(target=_send, daemon=True).start()


class AlertState:
    """Hysteresis state machine: only alerts after sustained crossing in each
    direction, so brief spikes near the threshold don't spam the channel."""

    def __init__(self, webhook_url, threshold, sustain_s, clear_s, hostname):
        self.webhook_url = webhook_url
        self.threshold = threshold
        self.sustain_s = sustain_s
        self.clear_s = clear_s
        self.hostname = hostname
        self.alerting = False
        self.crossed_up_at = None
        self.crossed_down_at = None

    def update(self, temp):
        if temp is None:
            return
        now = time.monotonic()
        if not self.alerting:
            if temp >= self.threshold:
                if self.crossed_up_at is None:
                    self.crossed_up_at = now
                elif now - self.crossed_up_at >= self.sustain_s:
                    self.alerting = True
                    self.crossed_up_at = None
                    post_slack(
                        self.webhook_url,
                        "[ALERT] {host}: temp {t:.1f}°C >= threshold {thr:.0f}°C "
                        "(sustained {s:.0f}s)".format(
                            host=self.hostname, t=temp,
                            thr=self.threshold, s=self.sustain_s,
                        ),
                    )
            else:
                self.crossed_up_at = None
        else:
            if temp < self.threshold:
                if self.crossed_down_at is None:
                    self.crossed_down_at = now
                elif now - self.crossed_down_at >= self.clear_s:
                    self.alerting = False
                    self.crossed_down_at = None
                    post_slack(
                        self.webhook_url,
                        "[OK] {host}: temp {t:.1f}°C < threshold {thr:.0f}°C "
                        "(sustained {s:.0f}s)".format(
                            host=self.hostname, t=temp,
                            thr=self.threshold, s=self.clear_s,
                        ),
                    )
            else:
                self.crossed_down_at = None


def _build_from_env():
    webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
    if not webhook:
        print("[INFO] SLACK_WEBHOOK_URL not set — temperature alerts disabled",
              file=sys.stderr)
        return None
    threshold = _env_float("TEMP_ALERT_C", 80.0)
    sustain_s = _env_float("TEMP_ALERT_SUSTAIN_S", 30.0)
    clear_s = _env_float("TEMP_CLEAR_SUSTAIN_S", 60.0)
    print("[INFO] Slack alerts ON — threshold {:.0f}°C, sustain {:.0f}s, "
          "clear {:.0f}s".format(threshold, sustain_s, clear_s),
          file=sys.stderr)
    return AlertState(webhook, threshold, sustain_s, clear_s, socket.gethostname())


alert_state = _build_from_env()
