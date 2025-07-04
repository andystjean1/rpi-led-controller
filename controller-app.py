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
import wave_effects

# Flask app initialization
app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

led_controller = LEDStripController()
strip = led_controller.strip

# Lock and job management
effect_lock = Lock()
current_effect = None
current_thread = None

# Helper function for color conversion
def hex_to_color(hex_color):
    """Convert hex color to rpi_ws281x Color"""
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return Color(r, g, b)

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
    "clock_timer": lambda: effects.allin(strip),
    # Wave Effects
    "sine_wave": lambda: wave_effects.sine_wave(led_controller),
    "triangle_wave": lambda: wave_effects.triangle_wave(led_controller),
    "pulse_wave": lambda: wave_effects.pulse_wave(led_controller),
    "rainbow_wave": lambda: wave_effects.rainbow_wave(led_controller),
    "dual_wave": lambda: wave_effects.dual_wave(led_controller),
    "ocean_wave": lambda: wave_effects.ocean_wave(led_controller),
    "fire_wave": lambda: wave_effects.fire_wave(led_controller),
    "breathing_wave": lambda: wave_effects.breathing_wave(led_controller),
    "lightning_wave": lambda: wave_effects.lightning_wave(led_controller),
    "custom_wave": lambda wave_config: wave_effects.custom_wave(led_controller, wave_config)
}

def stop_current_job():
    global current_effect, current_thread
    print("stopping the job")
    if current_thread and current_thread.is_alive():
        effects.set_stop_flag(True)  # Signal the job to stop
        clock_effects.set_stop_flag(True)
        wave_effects.set_stop_flag(True)
        current_thread.join()  # Wait for the thread to finish
        effects.set_stop_flag(False)  # Reset the flag
        clock_effects.set_stop_flag(False)
        wave_effects.set_stop_flag(False)

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

@app.route("/waves", methods=["GET"])
def waves():
    return render_template('waves.html')

@app.route("/update-settings", methods=["POST"])
def update_settings():
    global led_controller

    data = request.form
    color1_hex = data.get("color1", "#ffffff")
    color2_hex = data.get("color2", "#ff0000")
    color3_hex = data.get("color3", "#0000ff")
    delay = int(data.get("delay", 20))

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

@app.route("/wave-config", methods=["POST"])
def create_wave_config():
    """Create a custom wave configuration"""
    data = request.json
    
    # Create WaveConfig object
    wave_config = wave_effects.WaveConfig()
    
    # Set configuration parameters
    wave_config.speed = data.get("speed", 0.1)
    wave_config.amplitude = data.get("amplitude", 1.0)
    wave_config.frequency = data.get("frequency", 1.0)
    wave_config.phase_shift = data.get("phase_shift", 0)
    wave_config.wave_length = data.get("wave_length", 20)
    wave_config.color_shift = data.get("color_shift", False)
    wave_config.brightness_modulation = data.get("brightness_modulation", True)
    wave_config.wave_type = data.get("wave_type", "sine")
    wave_config.direction = data.get("direction", 1)
    wave_config.fade_edges = data.get("fade_edges", True)
    
    # Set color palette
    color_palette = data.get("color_palette", ["#FF0000", "#00FF00", "#0000FF"])
    wave_config.color_palette = [hex_to_color(color) for color in color_palette]
    
    # Start the custom wave effect
    effect_runner("custom_wave", wave_config)
    
    return jsonify({"message": "Custom wave configuration started"}), 200

@app.route("/wave-presets", methods=["GET"])
def get_wave_presets():
    """Get available wave presets"""
    presets = {
        "sine_wave": {
            "name": "Sine Wave",
            "description": "Classic smooth sine wave",
            "speed": 0.1,
            "amplitude": 1.0,
            "frequency": 1.0,
            "wave_type": "sine",
            "color_palette": ["#0000FF", "#800080", "#FF0000"]
        },
        "triangle_wave": {
            "name": "Triangle Wave",
            "description": "Sharp triangle wave pattern",
            "speed": 0.1,
            "amplitude": 1.0,
            "frequency": 1.0,
            "wave_type": "triangle",
            "color_palette": ["#00FF00", "#FFFF00", "#FFA500"]
        },
        "pulse_wave": {
            "name": "Pulse Wave",
            "description": "Digital pulse wave",
            "speed": 0.2,
            "amplitude": 1.0,
            "frequency": 1.0,
            "wave_type": "pulse",
            "color_palette": ["#FF0000", "#FFFFFF"]
        },
        "rainbow_wave": {
            "name": "Rainbow Wave",
            "description": "Flowing rainbow colors",
            "speed": 0.1,
            "amplitude": 1.0,
            "frequency": 1.0,
            "wave_type": "sine",
            "color_palette": ["rainbow"]
        },
        "ocean_wave": {
            "name": "Ocean Wave",
            "description": "Realistic ocean wave simulation",
            "speed": 0.08,
            "amplitude": 0.6,
            "frequency": 0.8,
            "wave_type": "sine",
            "color_palette": ["#003264", "#0064C8", "#0096FF", "#32C8FF", "#64FFFF", "#C8FFFF"]
        },
        "fire_wave": {
            "name": "Fire Wave",
            "description": "Flickering fire effect",
            "speed": 0.2,
            "amplitude": 1.0,
            "frequency": 1.5,
            "wave_type": "sine",
            "color_palette": ["#320000", "#C80000", "#FF6400", "#FFC800", "#FFFF64"]
        },
        "breathing_wave": {
            "name": "Breathing Wave",
            "description": "Gentle breathing effect",
            "speed": 0.05,
            "amplitude": 0.8,
            "frequency": 0.5,
            "wave_type": "sine",
            "color_palette": ["rainbow"]
        },
        "lightning_wave": {
            "name": "Lightning Wave",
            "description": "Storm with lightning flashes",
            "speed": 0.03,
            "amplitude": 0.3,
            "frequency": 0.3,
            "wave_type": "sine",
            "color_palette": ["#141414", "#141414", "#3C3C3C", "#FFFFFF"]
        },
        "dual_wave": {
            "name": "Dual Wave",
            "description": "Two interfering waves",
            "speed": 0.1,
            "amplitude": 0.5,
            "frequency": 1.0,
            "wave_type": "sine",
            "color_palette": ["#0000FF", "#800080", "#FF0000", "#FFA500"]
        }
    }
    
    return jsonify(presets), 200

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
