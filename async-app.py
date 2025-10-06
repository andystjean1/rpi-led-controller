import asyncio
import inspect
import logging
from threading import Lock, Thread

from flask import Flask, jsonify, render_template, request
from rpi_ws281x import Color
from rpi_ws281x import PixelStrip

import clock_effects
import colors
import effects
import light_race

# Flask app initialization
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# LED strip configuration
LED_COUNT = 120
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 5
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

logging.basicConfig(level=logging.INFO)


class StripControllerAdapter:
    """Adapter exposing controller-style helpers while sharing the PixelStrip instance."""

    def __init__(self, pixel_strip: PixelStrip):
        self.strip = pixel_strip
        self.numPixels = self.strip.numPixels()
        self.num_pixels = self.numPixels
        self.color_list = [colors.RED, colors.GREEN, colors.BLUE]
        self.delay = 0.5  # seconds

    def set_colors(self, color_list):
        self.color_list = list(color_list)

    def get_colors(self):
        return list(self.color_list)

    def set_delay(self, delay_ms: float):
        self.delay = delay_ms / 1000.0

    def get_delay(self):
        return self.delay * 1000.0

    def set_pixel(self, index, color):
        if 0 <= index < self.numPixels:
            self.strip.setPixelColor(index, color)

    def set_pixel_color_list(self, index):
        if not self.color_list:
            return
        if 0 <= index < self.numPixels:
            color_idx = index % len(self.color_list)
            self.strip.setPixelColor(index, self.color_list[color_idx])

    def off(self):
        for i in range(self.numPixels):
            self.strip.setPixelColor(i, colors.OFF)
        self.strip.show()

    def show(self):
        self.strip.show()


# Initialize the LED strip
strip = PixelStrip(
    LED_COUNT,
    LED_PIN,
    LED_FREQ_HZ,
    LED_DMA,
    LED_INVERT,
    LED_BRIGHTNESS,
    LED_CHANNEL,
)
strip.begin()
controller = StripControllerAdapter(strip)
current_settings = {
    "colors": [colors.RED, colors.GREEN, colors.BLUE],
    "delay": 500,
}

# Lock and job management
effect_lock = Lock()
current_effect = None
current_thread = None

# Effect runner
jobs = {
    "wheel": lambda: effects.color_wheel(controller),
    "warm_wheel": lambda: effects.warm_wheel(controller),
    "lime_green": lambda: effects.fill_strip(strip, colors.LIME_GREEN),
    "flash": lambda: effects.flash(controller),
    "leapfrog": lambda: effects.leap_frog(controller),
    "bounce": lambda: effects.bouncing_window(controller),
    "off": lambda: effects.fill_strip(strip, colors.OFF),
    "race": lambda: light_race.race(strip),
    "clock": lambda: clock_effects.clock(strip),
    "clock2": lambda: clock_effects.clock2(strip),
    "clock3": lambda: clock_effects.clock3(strip),
    "clock4": lambda: clock_effects.clock4(strip),
    "clock5": lambda: clock_effects.clock5(strip),
    "clock6": lambda: clock_effects.clock6(strip),
    "rollout": lambda: effects.roll_out(controller),
    "allin": lambda: effects.allin(strip),
}


def apply_settings():
    controller.set_colors(current_settings["colors"])
    controller.set_delay(current_settings["delay"])


apply_settings()


def reset_stop_flags():
    effects.set_stop_flag(False)
    clock_effects.set_stop_flag(False)
    light_race.winner_event.clear()


def stop_all_effects():
    effects.set_stop_flag(True)
    clock_effects.set_stop_flag(True)
    light_race.winner_event.set()

def stop_current_job():
    global current_effect, current_thread
    logging.info("Stopping active job")
    if current_thread and current_thread.is_alive():
        stop_all_effects()
        current_thread.join()

    reset_stop_flags()

    with effect_lock:
        current_effect = None
        current_thread = None

def effect_runner(job_name, *args):
    global current_effect, current_thread

    def run_job():
        global current_effect, current_thread
        logging.info("Running job %s", job_name)
        try:
            job_callable = jobs[job_name]
            result = job_callable(*args)
            if inspect.isawaitable(result):
                asyncio.run(result)
        except Exception:  # pragma: no cover - logged for debugging
            logging.exception("Job %s failed", job_name)
        finally:
            with effect_lock:
                current_effect = None
                current_thread = None
            reset_stop_flags()

    stop_current_job()
    reset_stop_flags()

    with effect_lock:
        current_effect = job_name
        current_thread = Thread(target=run_job)
        current_thread.start()
    

@app.route("/", methods=["GET"])
def index():
    return render_template('async.html')

@app.route("/clocks", methods=["GET"])
def clocks_page():
    return render_template('clocks.html')

@app.route("/poker-voice-control", methods=["GET"])
def voice_control():
    return render_template('voice-control.html')

@app.route("/settings", methods=["GET"])
def settings_page():
    return render_template('settings.html')

@app.route("/update-settings", methods=["POST"])
def update_settings():
    global current_settings

    data = request.form
    color_hex_values = [
        data.get("color1", "#ffffff"),
        data.get("color2", "#ff0000"),
        data.get("color3", "#0000ff"),
    ]
    delay_ms = int(data.get("delay", 500))

    def hex_to_color(value: str):
        value = value.lstrip('#')
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
        return Color(r, g, b)

    current_settings = {
        "colors": [hex_to_color(value) for value in color_hex_values],
        "delay": delay_ms,
    }

    apply_settings()

    return jsonify({"message": "Settings saved"}), 200

@app.route("/get-settings", methods=["GET"])
def get_settings():
    def color_to_hex(color_value):
        r = (color_value >> 16) & 0xFF
        g = (color_value >> 8) & 0xFF
        b = color_value & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"

    response = {
        "colors": [color_to_hex(value) for value in current_settings["colors"]],
        "delay": current_settings["delay"],
    }
    return jsonify(response), 200

@app.route("/start", methods=["POST"])
def start_effect():
    global current_effect, current_thread

    data = request.json
    job_name = data.get("effect")
    if job_name not in jobs:
        return jsonify({"error": f"Effect '{job_name}' does not exist"}), 404

    args = data.get("args", [])
    effect_runner(job_name, *args)
    print(f"started {job_name}")
    return jsonify({"message": f"Effect '{job_name}' started"}), 200

@app.route("/stop", methods=["POST"])
def stop_effect():
    global current_effect, current_thread

    if not current_thread or not current_thread.is_alive():
        logging.warning("Stop requested with no active job")
        return jsonify({"error": "No effect is currently running"}), 400

    stop_current_job()
    return jsonify({"message": "Effect stopped"}), 200

@app.route("/status", methods=["GET"])
def status():
    if not current_thread or not current_thread.is_alive():
        return jsonify({"status": "idle"}), 200

    return jsonify({"status": "running", "effect": current_effect}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
