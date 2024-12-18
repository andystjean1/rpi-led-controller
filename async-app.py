from flask import Flask, render_template, request, jsonify
from rpi_ws281x import PixelStrip, Color
import threading
import time
import asyncio

# custom mods
import light_race
import colors
import effects
import embeddings

app = Flask(__name__)

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

# Global variables for effect management
current_effect = None
effect_thread = None
effect_lock = threading.Lock()
running = False

def effect_runner(effect_function, *args, **kwargs):
    """Runs the given effect in a loop until stopped."""
    global running
    running = True
    while running:
        effect_function(*args, **kwargs)

def start_effect(effect_function, *args, **kwargs):
    """Starts a new effect, stopping the current one if necessary."""
    global current_effect, effect_thread, running

    with effect_lock:
        # Stop any currently running effect
        if effect_thread and effect_thread.is_alive():
            running = False
            effect_thread.join()

        # Start the new effect in a separate thread
        current_effect = effect_function
        effect_thread = threading.Thread(target=effect_runner, args=(effect_function,) + args, kwargs=kwargs)
        effect_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/wheel')
def wheel_route():
    """Trigger the wheel effect."""
    start_effect(effects.color_wheel, strip, wait_ms=20, iterations=None)  # Continuous loop
    return 'Color Wheel Effect Started'

@app.route('/lime-green')
def lime_green():
    start_effect(effects.fill_strip, strip, colors.LIME_GREEN)
    return 'Lime Green Effect Started'

@app.route('/start-race')
def start_race():
    start_effect(light_race.race, strip)
    return 'Race Effect Started'

@app.route('/off')
def turn_off():
    """Turn off all effects."""
    global running
    with effect_lock:
        running = False
        if effect_thread and effect_thread.is_alive():
            effect_thread.join()
        effects.fill_strip(strip, colors.OFF)
    return 'LEDs Turned Off'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
