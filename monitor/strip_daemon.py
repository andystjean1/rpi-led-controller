"""Root daemon that shows the laptop monitor's state on the WS281x strip.

Reads STATE_FILE (written by display.py on every poll) and animates:
  the strip is split into one equal segment per laptop, in name order;
  ok    steady dim green        warn  steady amber
  bad   steady red, with the pixels for failing services blinking white at the segment's start
  down  slow red pulse          (laptop unreachable)
If the state file is older than STALE_S (poller dead) the whole strip pulses blue.
Needs root on a Pi 3 (PWM via /dev/vcio), so it runs as a system service: see install_strip.sh.
    python3 strip_daemon.py [--test]     # --test cycles red/green/blue and exits
"""
import argparse
import json
import math
import os
import signal
import sys
import time

from rpi_ws281x import Color, PixelStrip

STATE_FILE = os.environ.get("STRIP_STATE", "/home/bananaman/hp-monitor/strip_state.json")
LED_COUNT = 120
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = int(os.environ.get("STRIP_BRIGHTNESS", "80"))  # 0-255; keeps the supply happy
STALE_S = 120
FRAME_S = 0.05

BASE = {"ok": (0, 90, 0), "warn": (200, 110, 0), "bad": (220, 0, 0), "down": (220, 0, 0)}


def load():
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if time.time() - data.get("written", 0) > STALE_S:
        return None
    return data.get("laptops", {})


def scaled(rgb, k):
    return Color(*(int(c * k) for c in rgb))


# Phone control (written by web.py's /api/strip). mode "monitor" shows laptop health; the rest
# override it. A missing or bad file means monitor mode.
CONTROL_FILE = os.environ.get("STRIP_CONTROL", "/home/bananaman/hp-monitor/strip_control.json")
MAX_BRIGHTNESS = 200


def load_control():
    try:
        with open(CONTROL_FILE) as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError):
        return {}


def wheel(pos):
    pos %= 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)


def control_frame(strip, ctl, t):
    """Draw a phone-chosen mode. Returns False for monitor mode (caller draws that)."""
    mode = ctl.get("mode", "monitor")
    n = strip.numPixels()
    try:
        rgb = tuple(max(0, min(255, int(v))) for v in ctl.get("color", [255, 255, 255]))[:3]
        speed = max(1, min(10, int(ctl.get("speed", 5))))
    except (TypeError, ValueError):
        rgb, speed = (255, 255, 255), 5
    if mode == "off":
        for i in range(n):
            strip.setPixelColor(i, Color(0, 0, 0))
    elif mode == "solid":
        for i in range(n):
            strip.setPixelColor(i, Color(*rgb))
    elif mode == "rainbow":
        shift = t * speed * 20
        for i in range(n):
            strip.setPixelColor(i, Color(*wheel(int(i * 256 / n + shift))))
    elif mode == "chase":
        head = int(t * speed * 8) % n
        for i in range(n):
            d = (head - i) % n
            strip.setPixelColor(i, scaled(rgb, max(0.0, 1 - d / 15)))
    elif mode == "breathe":
        k = 0.5 + 0.5 * math.sin(t * speed * 0.6)
        for i in range(n):
            strip.setPixelColor(i, scaled(rgb, k))
    else:
        return False
    return True


def frame(strip, laptops, t):
    n = strip.numPixels()
    if laptops is None:  # no fresh data: say so
        k = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(t * 2.0))
        for i in range(n):
            strip.setPixelColor(i, scaled((0, 40, 220), k))
        return
    labels = sorted(laptops)
    if not labels:
        labels = []
    seg = n // max(len(labels), 1)
    blink = int(t * 2) % 2 == 0
    for idx, label in enumerate(labels):
        info = laptops[label]
        state = info.get("overall", "down")
        rgb = BASE.get(state, BASE["down"])
        k = 0.2 + 0.8 * (0.5 + 0.5 * math.sin(t * 1.5)) if state == "down" else 1.0
        start = idx * seg
        end = n if idx == len(labels) - 1 else start + seg
        for i in range(start, end):
            strip.setPixelColor(i, scaled(rgb, k))
        if state in ("warn", "bad"):
            for j in range(min(len(info.get("bad", [])), 8)):
                strip.setPixelColor(start + j, Color(255, 255, 255) if blink else Color(0, 0, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    args = ap.parse_args()

    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, False, LED_BRIGHTNESS, 0)
    strip.begin()

    def clear(*_):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()
        sys.exit(0)

    signal.signal(signal.SIGTERM, clear)
    signal.signal(signal.SIGINT, clear)

    if args.test:
        for rgb in ((255, 0, 0), (0, 255, 0), (0, 0, 255)):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, Color(*rgb))
            strip.show()
            time.sleep(1.2)
        clear()

    last_load, laptops, ctl, bright = 0.0, None, {}, LED_BRIGHTNESS
    while True:
        now = time.time()
        if now - last_load > 0.3:  # re-read the files ~3x a second, animate at 20 fps
            laptops, ctl, last_load = load(), load_control(), now
            try:
                want = max(1, min(MAX_BRIGHTNESS, int(ctl.get("brightness", LED_BRIGHTNESS))))
            except (TypeError, ValueError):
                want = LED_BRIGHTNESS
            if want != bright:
                strip.setBrightness(want)
                bright = want
        if not control_frame(strip, ctl, now):
            frame(strip, laptops, now)
        strip.show()
        time.sleep(FRAME_S)


if __name__ == "__main__":
    main()
