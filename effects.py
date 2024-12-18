
import rpi_ws281x
import colors
import time

def fill_strip(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

    # Function to run the wheel effect
def color_wheel(strip, wait_ms=20, iterations=1):
    """Perform a color wheel effect over the strip."""
    for _ in range(iterations):
        for j in range(256):  # 0-255 for color wheel
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, colors.wheel((i + j) & 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)

def display_bits(strip, bits):
    for i in range(len(bits) - 1):
        color = colors.GREEN if x else colors.RED
        strip.setPixelColor(i, color)
    strip.show()
