from flask import Flask, jsonify, request, render_template
from threading import Lock, Thread
from rpi_ws281x import PixelStrip, Color
import time
import asyncio



import effects
import colors
import light_race
import embeddings

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

# Initialize the LED strip
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Lock and job management
effect_lock = Lock()
current_effect = None
current_thread = None

# Effect runner
jobs = {
    "wheel": lambda: effects.color_wheel(strip, wait_ms=20, iterations=1),
    "warm_wheel": lambda: effects.warm_wheel(strip),
    "lime_green": lambda: effects.fill_strip(strip, colors.LIME_GREEN),
    "flash": lambda: effects.flash(strip),
    "leapfrog": lambda: effects.leap_frog(strip),
    "bounce": lambda: effects.bouncing_window(strip),
    "off": lambda: effects.fill_strip(strip, colors.OFF),
    "text_effect": lambda text: embeddings.display_text_as_lights(text),
    "race": lambda: light_race.race(strip),
    "clock": lambda: effects.clock(strip),
    "clock2": lambda: effects.clock2(strip),
    "clock3": lambda: effects.clock3(strip)
}

def stop_current_job():
    global current_effect, current_thread
    print("stopping the job")
    if current_thread and current_thread.is_alive():
        effects.set_stop_flag(True)  # Signal the job to stop
        current_thread.join()  # Wait for the thread to finish
        effects.set_stop_flag(False)  # Reset the flag

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
