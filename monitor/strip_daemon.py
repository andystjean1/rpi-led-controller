"""Root daemon that drives the 5x60 WS281x grid: effects and laptop-monitor modes.

Reads STATE_FILE (written by display.py on every poll) and CONTROL_FILE (written by the phone page)
and draws the chosen mode from effects.py onto a canvas, which `flush` maps onto the wiring.
Monitor modes (monitor, rack, vitals) show each laptop's health; the show-off effects can be
interrupted by a red alert overlay when a laptop is bad or down, and any mode by an amber one while a
Claude session waits on the user (control "alerts", default on). The claude_* modes draw Claude Code
activity that Agent Town pushes to web.py (CLAUDE_FILE).
If the state file is older than STALE_S (poller dead) the monitor modes pulse blue.
Needs root on a Pi 3 (PWM via /dev/vcio), so it runs as a system service: see install_strip.sh.
    python3 strip_daemon.py [--test]     # --test cycles red/green/blue and exits
"""
import argparse
import importlib
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


CLAUDE_FILE = os.environ.get("STRIP_CLAUDE", "/home/bananaman/hp-monitor/claude_state.json")
CLAUDE_STALE_S = 20  # Agent Town pushes at least every 4 s; silence this long means it is off


class ClaudeFeed:
    """Reads CLAUDE_FILE (written by web.py when Agent Town pushes) and hands out each tool-call
    event once. History already in the file when the daemon starts is skipped."""

    def __init__(self, path=CLAUDE_FILE):
        self.path = path
        self.last_seq = None
        self.sessions = None  # None = Agent Town quiet

    def poll(self):
        """Returns (claude or None, events that are new since the last poll)."""
        try:
            with open(self.path) as f:
                data = json.load(f)
        except (OSError, ValueError):
            data = None
        if not isinstance(data, dict) or time.time() - data.get("written", 0) > CLAUDE_STALE_S:
            self.sessions = None
            return None, []
        events = [e for e in data.get("events", []) if isinstance(e, dict)]
        if self.last_seq is None:
            self.last_seq = data.get("seq", 0)
            new = []
        else:
            new = [e for e in events if e.get("seq", 0) > self.last_seq]
            if new:
                self.last_seq = max(e["seq"] for e in new)
        self.sessions = [s for s in data.get("sessions", []) if isinstance(s, dict) and s.get("id")]
        pc = data.get("pc") if isinstance(data.get("pc"), dict) else None
        return {"sessions": self.sessions, "pc": pc, "written": data.get("written")}, new


def pi_vitals():
    """The Pi's own CPU temperature (C) and 1-minute load, for the homelab map."""
    out = {}
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            out["temp"] = int(f.read().strip()) / 1000
    except (OSError, ValueError):
        pass
    try:
        out["load"] = os.getloadavg()[0]
    except (OSError, AttributeError):
        pass
    return out


# The live preview on the phone page reads this (web.py /api/frame). tmpfs, so no SD card wear.
FRAME_FILE = os.environ.get("STRIP_FRAME", "/dev/shm/strip_frame.bin")
FRAME_EVERY_S = 0.2


def dump_frame(cv):
    try:
        body = bytes(max(0, min(255, int(v))) for row in cv for px in row for v in px)
        tmp = FRAME_FILE + ".tmp"
        with open(tmp, "wb") as f:
            f.write(body)
        os.chmod(tmp, 0o644)
        os.replace(tmp, FRAME_FILE)
    except OSError:
        pass


class EffectsReloader:
    """Re-imports effects.py when the file changes, so a new or tuned effect goes live without
    restarting this root service. A broken edit is logged and the old code keeps running."""

    def __init__(self):
        self.mtime = self._mtime()
        self.checked = 0.0

    @staticmethod
    def _mtime():
        try:
            return os.path.getmtime(effects.__file__)
        except OSError:
            return None

    def poll(self, now):
        """True when the effects were reloaded (the caller then resets their saved state)."""
        global effects
        if now - self.checked < 2:
            return False
        self.checked = now
        m = self._mtime()
        if m is None or m == self.mtime:
            return False
        self.mtime = m
        try:
            effects = importlib.reload(effects)
        except Exception as exc:  # noqa: BLE001 - keep drawing with the code we have
            print("effects.py reload failed: %r" % (exc,), file=sys.stderr, flush=True)
            return False
        print("effects.py reloaded", file=sys.stderr, flush=True)
        return True


def effective_mode(ctl):
    """The control file's mode, except that a timed banner which has run out gives the wall back
    to the mode it interrupted (web.py also writes that change back to the file when it next reads)."""
    mode = ctl.get("mode", "monitor")
    until = ctl.get("text_until")
    if mode == "text" and isinstance(until, (int, float)) and until and time.time() > until:
        prev = ctl.get("prev_mode")
        return prev if isinstance(prev, str) and prev != "text" else "monitor"
    return mode


def render(strip, ctl, laptops, t, dt, state, claude=None, events=(), pi=None):
    """Draw one frame for the phone's chosen mode (unknown modes fall back to monitor). Returns
    the canvas."""
    mode = effective_mode(ctl)
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
        ctx = {"t": t, "dt": dt, "rgb": rgb, "speed": speed, "laptops": laptops, "state": state,
               "claude": claude, "events": list(events), "text": ctl.get("text", ""), "say": ctl.get("say"),
               "text_style": ctl.get("text_style"), "text_static": ctl.get("text_static"), "pi": pi or {}}
        effects.MODES.get(mode, effects.monitor)(cv, ctx)
        if ctl.get("alerts", True):
            if mode in effects.EFFECTS:
                effects.alert_overlay(cv, ctx)  # the monitor modes show laptop problems themselves
            if mode not in ("claude_lanes", "claude_drones", "homelab"):
                effects.waiting_overlay(cv, ctx)  # those already show a waiting session
        effects.say_overlay(cv, ctx)  # a sent message scrolls over everything, once
    flush(strip, cv, layout)
    return cv


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
    feed, claude, events, last_claude = ClaudeFeed(), None, [], 0.0
    reloader, pi, last_pi, last_dump = EffectsReloader(), {}, 0.0, 0.0
    while True:
        now = time.time()
        if reloader.poll(now):
            fx_state = {}
        if now - last_pi > 5:
            pi, last_pi = pi_vitals(), now
        if now - last_claude > 0.1:  # Claude events are read faster so pulses start promptly
            claude, fresh = feed.poll()
            events.extend(fresh)
            last_claude = now
        if now - last_load > 0.3:  # re-read the files ~3x a second, animate at 20 fps
            laptops, ctl, last_load = load(), load_control(), now
            try:
                want = max(1, min(MAX_BRIGHTNESS, int(ctl.get("brightness", LED_BRIGHTNESS))))
            except (TypeError, ValueError):
                want = LED_BRIGHTNESS
            if want != bright:
                strip.setBrightness(want)
                bright = want
        try:
            cv = render(strip, ctl, laptops, now, min(0.25, now - last_frame), fx_state, claude, events, pi)
        except Exception as exc:  # noqa: BLE001 - a bug in a freshly reloaded effect must not kill the wall
            print("render failed: %r" % (exc,), file=sys.stderr, flush=True)
            fx_state, cv = {}, None
            time.sleep(1)
        if cv is not None and now - last_dump > FRAME_EVERY_S:
            dump_frame(cv)
            last_dump = now
        events = []
        last_frame = now
        strip.show()
        time.sleep(FRAME_S)


if __name__ == "__main__":
    main()
