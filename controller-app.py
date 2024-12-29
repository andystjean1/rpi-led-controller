from flask import Flask, jsonify, request, render_template
from threading import Lock, Thread
from rpi_ws281x import PixelStrip, Color
import time
import asyncio

from ledstrip import LEDStripController

import effects
import clock_effects
import colors
import light_race
import embeddings

# Flask app initialization
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

led_controller = LEDStripController()
strip = led_controller.strip

# Lock and job management
effect_lock = Lock()
current_effect = None
current_thread = None

# Effect runner
jobs = {
    "wheel": lambda: effects.color_wheel(led_controller),
    "warm_wheel": lambda: effects.warm_wheel(led_controller),
    "lime_green": lambda: led_controller.fill_color(colors.LIME_GREEN),
    "flash": lambda: effects.flash(led_controller),
    "leapfrog": lambda: effects.leap_frog(led_controller),
    "bounce": lambda: effects.bouncing_window(led_controller),
    "off": lambda: led_controller.off(),
    "text_effect": lambda text: embeddings.display_text_as_lights(text),
    "race": lambda: light_race.race(strip),
    "clock": lambda: clock_effects.clock(strip),
    "clock2": lambda: clock_effects.clock2(strip),
    "clock3": lambda: clock_effects.clock3(strip),
    "clock4": lambda: clock_effects.clock4(strip),
    "clock5": lambda: clock_effects.clock5(strip),
    "clock6": lambda: clock_effects.clock6(strip),
    "rollout": lambda: effects.roll_out(led_controller),
    "allin": lambda: effects.allin(strip),
    "clock_timer": lambda: effects.allin(strip)
}

def stop_current_job():
    global current_effect, current_thread
    print("stopping the job")
    if current_thread and current_thread.is_alive():
        effects.set_stop_flag(True)  # Signal the job to stop
        clock_effects.set_stop_flag(True)
        current_thread.join()  # Wait for the thread to finish
        effects.set_stop_flag(False)  # Reset the flag
        clock_effects.set_stop_flag(False)

        with effect_lock:
            current_effect = None
            current_thread = None

def effect_runner(job_name, *args):
    global current_effect, current_thread

    def run_job():
        asyncio.run(jobs[job_name](*args))

    stop_current_job()

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
def settings():
    return render_template('settings.html')

@app.route("/update-settings", methods=["POST"])
def update_settings():
    global led_controller

    data = request.form
    color1_hex = data.get("color1", "#ffffff")
    color2_hex = data.get("color2", "#ff0000")
    color3_hex = data.get("color3", "#0000ff")
    delay = int(data.get("delay", 20))

    # Convert hex colors to rpi_ws281x Colors
    def hex_to_color(hex_color):
        r = int(hex_color[1:3], 16)
        g = int(hex_color[3:5], 16)
        b = int(hex_color[5:7], 16)
        return Color(r, g, b)

    new_colors = [
        hex_to_color(color1_hex),
        hex_to_color(color2_hex),
        hex_to_color(color3_hex)
    ]

    # Update LEDStripController settings
    led_controller.set_colors(new_colors)
    led_controller.set_delay(delay)

    return jsonify({"success"}), 200

@app.route("/get-settings", methods=["GET"])
def get_settings():
    global led_controller
    # Convert colors to hex format
    def color_to_hex(color):
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"

    colors = [color_to_hex(color) for color in led_controller.get_colors()]
    delay = led_controller.get_delay()
    return jsonify({
        "colors": colors,
        "delay": delay
    })


# start an effect
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

    if not effect_lock.locked():
        print("no effect running")
        return jsonify({"error": "No effect is currently running"}), 400

    stop_current_job()
    return jsonify({"message": "Effect stopped"}), 200

@app.route("/status", methods=["GET"])
def status():
    if not effect_lock.locked():
        return jsonify({"status": "idle"}), 200

    return jsonify({"status": "running", "effect": current_effect}), 200

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
