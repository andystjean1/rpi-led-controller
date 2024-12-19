
import rpi_ws281x
import colors
import time

import asyncio

stop_flag = False

def set_stop_flag(value: bool):
    global stop_flag
    stop_flag = value

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
                if stop_flag:
                    break

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
            if stop_flag:
                break
            
            condition = (i % 2) == (j % 2)
            color = colors.wheel(i) if condition else colors.OFF
            strip.setPixelColor(j, color)
        strip.show()
        time.sleep(0.5)

def leap_frog(strip, window_size=5, iterations=3):
    num_pixels = strip.numPixels()

    for _ in range(iterations):
        for i in range(num_pixels):
            # Clear the LED just before the current window
            clear_index = (i - 1) % num_pixels
            strip.setPixelColor(clear_index, colors.OFF)

            # Set the current window of lights
            for j in range(window_size):
                pixel_index = (i + j) % num_pixels
                strip.setPixelColor(pixel_index, colors.RED if j % 2 == 0 else colors.PURPLE)

            # Show the updated strip
            strip.show()
            time.sleep(0.2)

def warm_wheel(strip, window_size=5, iterations=3):
    num_pixels = strip.numPixels()

    for _ in range(iterations):
        for i in range(num_pixels):
            # Clear the LED just before the current window
            clear_index = (i - 1) % num_pixels
            strip.setPixelColor(clear_index, colors.OFF)

            # Set the current window of lights
            for j in range(window_size):
                pixel_index = (i + j) % num_pixels
                idx = (i+j) % num_pixels
                color_idx = ((idx * 256 // num_pixels) % 256)
                strip.setPixelColor(pixel_index, colors.warm_wheel(color_idx))

            # Show the updated strip
            strip.show()
            time.sleep(0.1)

def bouncing_window(strip, window_size=5, iterations=10, wait_ms=50):
    num_pixels = strip.numPixels()
    direction = 1  # 1 for forward, -1 for backward
    position = 0

    for _ in range(iterations):
        for _ in range(num_pixels - window_size + 1):
            # Turn off all LEDs
            for i in range(num_pixels):
                strip.setPixelColor(i, colors.OFF)

            # Light up the window
            for j in range(window_size):
                pixel_index = position + j
                if pixel_index < num_pixels:
                    strip.setPixelColor(
                        pixel_index, colors.BLUE if j % 2 == 0 else colors.PURPLE
                    )

            # Show the strip
            strip.show()
            time.sleep(wait_ms / 1000.0)

            # Update position
            position += direction

            # Reverse direction at edges
            if position == 0 or position == num_pixels - window_size:
                direction *= -1


