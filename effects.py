from flask import Flask
from rpi_ws281x import PixelStrip, Color
import time

app = Flask(__name__)

# LED strip configuration:
LED_COUNT = 90          # Number of LEDs
LED_PIN = 18            # GPIO pin connected to the pixels (PWM pin)
LED_FREQ_HZ = 800000    # LED signal frequency (800kHz)
LED_DMA = 5             # DMA channel
LED_BRIGHTNESS = 255    # Brightness (0-255)
LED_INVERT = False      # Invert signal
LED_CHANNEL = 0         # PWM channel

# Initialize the LED strip
strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

# Function to generate colors in a wheel
def wheel(pos):
    """Generate a rainbow color based on position (0-255)."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

# Function to run the wheel effect
def color_wheel(strip, wait_ms=20, iterations=1):
    """Perform a color wheel effect over the strip."""
    for _ in range(iterations):
        for j in range(256):  # 0-255 for color wheel
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, wheel((i + j) & 255))
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

@app.route('/off')
def turn_off():
    """Turn all LEDs off."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()
    print("LEDs are off")
    return 'LEDs turned off'

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
