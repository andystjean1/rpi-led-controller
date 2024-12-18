from flask import Flask
from rpi_ws281x import PixelStrip, Color
import time
import asyncio

#custom mods
import light_race
import colors

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

# Function to run the wheel effect
def color_wheel(strip, wait_ms=20, iterations=1):
    """Perform a color wheel effect over the strip."""
    for _ in range(iterations):
        for j in range(256):  # 0-255 for color wheel
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, colors.wheel((i + j) & 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)

@app.route('/')
def index():
    return 'Hello World'

@app.route('/wheel')
def wheel_route():
    """Trigger the wheel effect."""
    print("Starting color wheel effect")
    color_wheel(strip, wait_ms=20, iterations=1)  # Perform one full wheel rotation
    return 'Color Wheel Effect Completed'

@app.route('/lime-green')
def lime_green():
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.LIME_GREEN)
    strip.show()
    print("lime green")
    return 'lime green'

@app.route('/start-race')
def start_race():
    asyncio.run(light_race.race(strip))
    return 'race started'


@app.route('/off')
def turn_off():
    """Turn all LEDs off."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.OFF)
    strip.show()
    print("LEDs are off")
    return 'LEDs turned off'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
