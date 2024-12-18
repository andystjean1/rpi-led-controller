from flask import Flask, render_template
from rpi_ws281x import PixelStrip, Color
import time
import asyncio

#custom mods
import light_race
import colors
import effects
import embeddings

app = Flask(__name__)

# LED strip configuration:
LED_COUNT = 120          # Number of LEDs
LED_PIN = 18            # GPIO pin connected to the pixels (PWM pin)
LED_FREQ_HZ = 800000    # LED signal frequency (800kHz)
LED_DMA = 5             # DMA channel
LED_BRIGHTNESS = 255    # Brightness (0-255)
LED_INVERT = False      # Invert signal
LED_CHANNEL = 0         # PWM channel

# Initialize the LED strip
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/wheel')
def wheel_route():
    """Trigger the wheel effect."""
    print("Starting color wheel effect")
    effects.color_wheel(strip, wait_ms=20, iterations=1)  # Perform one full wheel rotation
    return 'Color Wheel Effect Completed'

@app.route('/lime-green')
def lime_green():
    effects.fill_strip(strip, colors.LIME_GREEN)
    print("lime green")
    return 'lime green'

@app.route('/start-race')
def start_race():
    await asyncio.run(light_race.race(strip))
    return 'race ran'

@app.route('/text_effect', methods=['POST'])
def text_effect():
    """Endpoint to trigger the text-to-LED effect."""
    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "Text input is required"}), 400

    try:
        embeddings.display_text_as_lights(text)
        return jsonify({"status": "Effect displayed for text", "text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/off')
def turn_off():
    """Turn all LEDs off."""
    effects.fill_strip(strip, colors.OFF)
    print("LEDs are off")
    return 'LEDs turned off'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
