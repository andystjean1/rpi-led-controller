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
import matrix_effects

# Flask app initialization
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# strip 1 is arranged in a straight line

# strip 2 is arranged as a 4 x 60 matrix, the matrix can be oriented horizontally or vertically
# the complete led strip snakes so indexes of the pixels on the matrix go like this
# 0-59 
# 119-60
# 120-179
# 239-180

# LED strip configuration
LED_COUNT_STRIP1 = 120
LED_PIN_STRIP1 = 18
LED_COUNT_STRIP2 = 240
LED_PIN_STRIP2 = 19
LED_FREQ_HZ = 800000
LED_DMA = 5
LED_BRIGHTNESS = 255
LED_INVERT = False

logging.basicConfig(level=logging.INFO)


class StripControllerAdapter:
    """Adapter exposing controller-style helpers while sharing the PixelStrip instance."""

    def __init__(self, pixel_strip: PixelStrip, strip_id="strip1"):
        self.strip = pixel_strip
        self.strip_id = strip_id
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


# Initialize LED strips
strip1 = PixelStrip(
    LED_COUNT_STRIP1,
    LED_PIN_STRIP1,
    LED_FREQ_HZ,
    LED_DMA,
    LED_INVERT,
    LED_BRIGHTNESS,
    0,  # Channel 0
)
strip1.begin()

strip2 = PixelStrip(
    LED_COUNT_STRIP2,
    LED_PIN_STRIP2,
    LED_FREQ_HZ,
    LED_DMA,
    LED_INVERT,
    LED_BRIGHTNESS,
    1,  # Channel 1
)
strip2.begin()

controller1 = StripControllerAdapter(strip1, "strip1")
controller2 = StripControllerAdapter(strip2, "strip2")

strips = {
    "strip1": {"strip": strip1, "controller": controller1},
    "strip2": {"strip": strip2, "controller": controller2}
}

current_settings = {
    "strip1": {
        "colors": [colors.RED, colors.GREEN, colors.BLUE],
        "delay": 500,
    },
    "strip2": {
        "colors": [colors.RED, colors.GREEN, colors.BLUE],
        "delay": 500,
    }
}

# Lock and job management per strip
effect_locks = {
    "strip1": Lock(),
    "strip2": Lock()
}
current_effects = {
    "strip1": None,
    "strip2": None
}
current_threads = {
    "strip1": None,
    "strip2": None
}

# Effect runners per strip
def get_jobs(strip_id):
    """Get job dictionary for a specific strip"""
    strip_obj = strips[strip_id]["strip"]
    controller = strips[strip_id]["controller"]

    jobs = {
        "wheel": lambda: effects.color_wheel(controller),
        "warm_wheel": lambda: effects.warm_wheel(controller),
        "lime_green": lambda: effects.fill_strip(strip_obj, colors.LIME_GREEN),
        "flash": lambda: effects.flash(controller),
        "leapfrog": lambda: effects.leap_frog(controller),
        "bounce": lambda: effects.bouncing_window(controller),
        "off": lambda: effects.fill_strip(strip_obj, colors.OFF),
        "race": lambda: light_race.race(strip_obj),
        "clock": lambda: clock_effects.clock(strip_obj, strip_id),
        "clock2": lambda: clock_effects.clock2(strip_obj, strip_id),
        "clock3": lambda: clock_effects.clock3(strip_obj, strip_id),
        "clock4": lambda: clock_effects.clock4(strip_obj, strip_id),
        "clock5": lambda: clock_effects.clock5(strip_obj, strip_id),
        "clock6": lambda: clock_effects.clock6(strip_obj, strip_id),
        "rollout": lambda: effects.roll_out(controller),
        "allin": lambda: effects.allin(strip_obj),
    }

    # Add matrix effects only for strip2 (240 LED matrix)
    if strip_id == "strip2":
        jobs.update({
            # Text Scroller
            "text_scroll": lambda text="HELLO", color=None: matrix_effects.text_scroller(strip_obj, text, color, strip_id),

            # Matrix Patterns
            "spiral": lambda: matrix_effects.spiral_pattern(strip_obj, strip_id),
            "checkerboard": lambda: matrix_effects.checkerboard_pattern(strip_obj, strip_id),
            "wave": lambda: matrix_effects.wave_pattern(strip_obj, strip_id),
            "expanding_circles": lambda: matrix_effects.expanding_circles(strip_obj, strip_id),

            # 2D Animations
            "bouncing_ball": lambda: matrix_effects.bouncing_ball(strip_obj, strip_id),
            "game_of_life": lambda: matrix_effects.game_of_life(strip_obj, strip_id),
            "snake": lambda: matrix_effects.snake_game(strip_obj, strip_id),
            "tetris": lambda: matrix_effects.tetris_blocks(strip_obj, strip_id),
            "matrix_race": lambda: matrix_effects.matrix_race(strip_obj, strip_id),

            # Visualizations
            "bar_graph": lambda: matrix_effects.bar_graph(strip_obj, strip_id),
            "spectrum": lambda: matrix_effects.spectrum_analyzer(strip_obj, strip_id),
            "heat_map": lambda: matrix_effects.heat_map(strip_obj, strip_id),
        })

    return jobs


def apply_settings(strip_id):
    """Apply settings to a specific strip"""
    controller = strips[strip_id]["controller"]
    controller.set_colors(current_settings[strip_id]["colors"])
    controller.set_delay(current_settings[strip_id]["delay"])


# Apply initial settings to both strips
for strip_id in strips.keys():
    apply_settings(strip_id)


def reset_stop_flags(strip_id):
    """Reset stop flags for a specific strip"""
    effects.set_stop_flag(False, strip_id)
    clock_effects.set_stop_flag(False, strip_id)
    matrix_effects.set_stop_flag(False, strip_id)
    if strip_id == "strip1":  # Only clear race event for strip1
        light_race.winner_event.clear()


def stop_all_effects(strip_id):
    """Stop all effects for a specific strip"""
    effects.set_stop_flag(True, strip_id)
    clock_effects.set_stop_flag(True, strip_id)
    matrix_effects.set_stop_flag(True, strip_id)
    if strip_id == "strip1":  # Only set race event for strip1
        light_race.winner_event.set()

def stop_current_job(strip_id):
    """Stop the current job for a specific strip"""
    logging.info("Stopping active job for %s", strip_id)
    if current_threads[strip_id] and current_threads[strip_id].is_alive():
        stop_all_effects(strip_id)
        current_threads[strip_id].join()

    reset_stop_flags(strip_id)

    with effect_locks[strip_id]:
        current_effects[strip_id] = None
        current_threads[strip_id] = None

def effect_runner(strip_id, job_name, *args):
    """Run an effect on a specific strip"""
    def run_job():
        logging.info("Running job %s on %s", job_name, strip_id)
        try:
            jobs = get_jobs(strip_id)
            job_callable = jobs[job_name]
            result = job_callable(*args)
            if inspect.isawaitable(result):
                asyncio.run(result)
        except Exception:  # pragma: no cover - logged for debugging
            logging.exception("Job %s failed on %s", job_name, strip_id)
        finally:
            with effect_locks[strip_id]:
                current_effects[strip_id] = None
                current_threads[strip_id] = None
            reset_stop_flags(strip_id)

    stop_current_job(strip_id)
    reset_stop_flags(strip_id)

    with effect_locks[strip_id]:
        current_effects[strip_id] = job_name
        current_threads[strip_id] = Thread(target=run_job)
        current_threads[strip_id].start()
    

@app.route("/", methods=["GET"])
def index():
    return render_template('async.html')

@app.route("/clocks", methods=["GET"])
def clocks_page():
    return render_template('clocks.html')

@app.route("/matrix", methods=["GET"])
def matrix_page():
    return render_template('matrix.html')

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
    strip_id = data.get("strip_id", "strip1")

    if strip_id not in strips:
        return jsonify({"error": f"Invalid strip_id: {strip_id}"}), 400

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

    current_settings[strip_id] = {
        "colors": [hex_to_color(value) for value in color_hex_values],
        "delay": delay_ms,
    }

    apply_settings(strip_id)

    return jsonify({"message": f"Settings saved for {strip_id}"}), 200

@app.route("/get-settings", methods=["GET"])
def get_settings_route():
    strip_id = request.args.get("strip_id", "strip1")

    if strip_id not in strips:
        return jsonify({"error": f"Invalid strip_id: {strip_id}"}), 400

    def color_to_hex(color_value):
        r = (color_value >> 16) & 0xFF
        g = (color_value >> 8) & 0xFF
        b = color_value & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"

    response = {
        "strip_id": strip_id,
        "colors": [color_to_hex(value) for value in current_settings[strip_id]["colors"]],
        "delay": current_settings[strip_id]["delay"],
    }
    return jsonify(response), 200

@app.route("/start", methods=["POST"])
def start_effect():
    data = request.json
    strip_id = data.get("strip_id", "strip1")
    job_name = data.get("effect")

    if strip_id not in strips:
        return jsonify({"error": f"Invalid strip_id: {strip_id}"}), 400

    jobs = get_jobs(strip_id)
    if job_name not in jobs:
        return jsonify({"error": f"Effect '{job_name}' does not exist"}), 404

    args = data.get("args", [])
    effect_runner(strip_id, job_name, *args)
    logging.info(f"Started {job_name} on {strip_id}")
    return jsonify({"message": f"Effect '{job_name}' started on {strip_id}"}), 200

@app.route("/stop", methods=["POST"])
def stop_effect():
    data = request.json
    strip_id = data.get("strip_id", "strip1")

    if strip_id not in strips:
        return jsonify({"error": f"Invalid strip_id: {strip_id}"}), 400

    if not current_threads[strip_id] or not current_threads[strip_id].is_alive():
        logging.warning(f"Stop requested with no active job on {strip_id}")
        return jsonify({"error": f"No effect is currently running on {strip_id}"}), 400

    stop_current_job(strip_id)
    return jsonify({"message": f"Effect stopped on {strip_id}"}), 200

@app.route("/status", methods=["GET"])
def status():
    strip_id = request.args.get("strip_id", "strip1")

    if strip_id not in strips:
        return jsonify({"error": f"Invalid strip_id: {strip_id}"}), 400

    if not current_threads[strip_id] or not current_threads[strip_id].is_alive():
        return jsonify({"strip_id": strip_id, "status": "idle"}), 200

    return jsonify({"strip_id": strip_id, "status": "running", "effect": current_effects[strip_id]}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
