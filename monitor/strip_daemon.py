"""Root daemon that drives the 5x60 WS281x grid: effects and laptop-monitor modes.

Reads STATE_FILE (written by display.py on every poll) and CONTROL_FILE (written by the phone page)
and draws the chosen mode from effects.py onto a canvas, which `flush` maps onto the wiring.
Monitor modes (monitor, rack, heartbeat, vitals) show each laptop's health; the show-off effects can
be interrupted by a red alert overlay when a laptop is bad or down (control "alerts", default on).
If the state file is older than STALE_S (poller dead) the monitor modes pulse blue.
Needs root on a Pi 3 (PWM via /dev/vcio), so it runs as a system service: see install_strip.sh.
    python3 strip_daemon.py [--test]     # --test cycles red/green/blue and exits
"""
import argparse
import json
import os
import signal
import sys
import time

from rpi_ws281x import Color, PixelStrip

import effects

STATE_FILE = os.environ.get("STRIP_STATE", "/home/bananaman/hp-monitor/strip_state.json")
ROWS, COLS = 5, 60   # five 60-pixel strips wired end to end in one line
LED_COUNT = ROWS * COLS
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = int(os.environ.get("STRIP_BRIGHTNESS", "80"))  # 0-255; keeps the supply happy
STALE_S = 120
FRAME_S = 0.05


def load():
    try:
        with open(STATE_FILE) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if time.time() - data.get("written", 0) > STALE_S:
        return None
    return data.get("laptops", {})


# Phone control (written by web.py's /api/strip). mode "monitor" shows laptop health; the rest
# override it. A missing or bad file means monitor mode.
CONTROL_FILE = os.environ.get("STRIP_CONTROL", "/home/bananaman/hp-monitor/strip_control.json")
MAX_BRIGHTNESS = 120  # 300 pixels at full white can pull ~18 A; this keeps a modest supply safe


def grid_index(row, col, layout):
    """Grid cell (row 0 = top of the grid, col 0 = left) -> position along the data line.

    layout (set from the phone's calibration screen):
      flip_rows   row 0 is the strip nearest the end of the line instead of the start
      serpentine  every other strip runs backwards (strips joined in a zigzag)
      reverse     the whole line starts at the far end
    """
    r = ROWS - 1 - row if layout.get("flip_rows") else row
    c = COLS - 1 - col if layout.get("serpentine") and r % 2 else col
    i = r * COLS + c
    return LED_COUNT - 1 - i if layout.get("reverse") else i


def load_control():
    try:
        with open(CONTROL_FILE) as f:
            c = json.load(f)
        return c if isinstance(c, dict) else {}
    except (OSError, ValueError):
        return {}


def flush(strip, cv, layout):
    """Copy the finished canvas onto the strip through the wiring map."""
    for r in range(ROWS):
        row = cv[r]
        for c in range(COLS):
            red, green, blue = row[c]
            strip.setPixelColor(grid_index(r, c, layout), Color(min(255, int(red)), min(255, int(green)),
                                                                min(255, int(blue))))


def render(strip, ctl, laptops, t, dt, state):
    """Draw one frame for the phone's chosen mode (unknown modes fall back to monitor)."""
    mode = ctl.get("mode", "monitor")
    layout = ctl.get("layout", {})
    cv = effects.new()
    if mode == "calibrate":
        for cell in ctl.get("cal", [])[:LED_COUNT]:
            try:
                row, col = int(cell[0]), int(cell[1])
            except (TypeError, ValueError, IndexError):
                continue
            if 0 <= row < ROWS and 0 <= col < COLS:
                cv[row][col] = (255, 255, 255)
    elif mode != "off":
        try:
            rgb = tuple(max(0, min(255, int(v))) for v in ctl.get("color", [255, 255, 255]))[:3]
            speed = max(1, min(10, int(ctl.get("speed", 5))))
        except (TypeError, ValueError):
            rgb, speed = (255, 255, 255), 5
        ctx = {"t": t, "dt": dt, "rgb": rgb, "speed": speed, "laptops": laptops, "state": state}
        effects.MODES.get(mode, effects.monitor)(cv, ctx)
        if mode in effects.EFFECTS and ctl.get("alerts", True):
            effects.alert_overlay(cv, ctx)  # the monitor modes show problems themselves
    flush(strip, cv, layout)


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
    last_frame, fx_state = time.time(), {}
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
        render(strip, ctl, laptops, now, min(0.25, now - last_frame), fx_state)
        last_frame = now
        strip.show()
        time.sleep(FRAME_S)


if __name__ == "__main__":
    main()
