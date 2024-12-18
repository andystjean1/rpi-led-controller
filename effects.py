
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
    while True:
        for j in range(256):  # 0-255 for color wheel
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, colors.wheel((i + j) & 255))
            strip.show()
            time.sleep(wait_ms / 1000.0)

def display_bits(strip, bits):
    for i in range(len(bits)):
        color = colors.OFF
        if(bits[i] > 0):
            color = colors.GREEN
        if(bits[i] < 0):
            color = colors.RED

        strip.setPixelColor(i, color)
    strip.show()

def flash(strip):
    iterations = 20
    for i in range(iterations):
        for j in range(strip.numPixels()):
            condition = (i % 2) == (j % 2)
            color = colors.wheel(i) if condition else colors.OFF
            strip.setPixelColor(j, color)
        strip.show()
        time.sleep(0.5)

def leap_frog(strip):
    for i in range(1, strip.numPixels() - 1):
        strip.setPixelColor(i, colors.RED if i % 2 else colors.PURPLE)
        strip.setPixelColor(i+1, colors.PURPLE if i %2 else colors.RED)
        strip.setPixelColor(i-1, colors.OFF)
        strip.show()
        time.sleep(0.2)
