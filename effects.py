import time
from datetime import datetime as dt
import asyncio

import pytz
import rpi_ws281x
import colors
import clock_effects

stop_flag = False

def set_stop_flag(value: bool):
    global stop_flag
    stop_flag = value

def fill_strip(strip, color):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

    # Function to run the wheel effect

def color_wheel(controller):
    """Perform a color wheel effect over the strip."""
    while not stop_flag:
        for j in range(256):  # 0-255 for color wheel
            if stop_flag:
                break
            for i in range(controller.numPixels):
                if stop_flag:
                    break

                controller.set_pixel(i, colors.wheel((i + j) & 255))
            controller.show()
            time.sleep(controller.delay)

def flash(controller):
    i = 0
    while not stop_flag:
        i+=1
        for j in range(controller.numPixels):
            if stop_flag:
                break
            condition = (i % 2) == (j % 2)
            color = controller.color_list[0] if condition else controller.color_list[1]
            controller.set_pixel(j, color)
        controller.show()
        time.sleep(controller.delay)

def leap_frog(controller):
    num_pixels = controller.numPixels
    window_size = 5

    while not stop_flag:
        for i in range(num_pixels):
            if stop_flag:
                break
            # Clear the LED just before the current window
            clear_index = (i - 1) % num_pixels
            controller.set_pixel(clear_index, colors.OFF)

            # Set the current window of lights
            for j in range(window_size):
                pixel_index = (i + j) % num_pixels
                controller.set_pixel_color_list(pixel_index)

            # Show the updated strip
            controller.show()
            time.sleep(controller.delay)

def display_bits(strip, bits):
    for i in range(len(bits)):
        color = colors.OFF
        if(bits[i] > 0):
            color = colors.GREEN
        if(bits[i] < 0):
            color = colors.RED

        strip.setPixelColor(i, color)
    strip.show()

def roll_out(controller):
    num_pixels = controller.num_pixels

    for i in range(1, num_pixels):
        if stop_flag:
            break

        #light up the strip
        for j in (range(i-1)):
            controller.set_pixel(j, controller.color_list[0])

        print("rolling out")
        #loop through and rollout
        for j in (range(1, i)):
            if stop_flag:
                break

            controller.set_pixel(j, colors.OFF)
            controller.set_pixel(j - 1, controller.color_list[0])
            controller.show()
            time.sleep(controller.delay)
        print("rolled out")

def warm_wheel(controller):
    num_pixels = controller.numPixels
    window_size = 5

    while not stop_flag:
        for i in range(num_pixels):
            # Clear the LED just before the current window
            clear_index = (i - 1) % num_pixels
            controller.set_pixel(clear_index, colors.OFF)

            # Set the current window of lights
            for j in range(window_size):
                pixel_index = (i + j) % num_pixels
                idx = (i+j) % num_pixels
                color_idx = ((idx * 256 // num_pixels) % 256)
                controller.set_pixel(pixel_index, colors.warm_wheel(color_idx))

            # Show the updated strip
            controller.show()
            time.sleep(controller.delay)

def bouncing_window(controller):
    num_pixels = controller.numPixels
    direction = 1  # 1 for forward, -1 for backward
    position = 0
    window_size = 5
    print(num_pixels)
    while not stop_flag:
        for _ in range(num_pixels - window_size + 1):
            if stop_flag:
                break
            # Turn off all LEDs
            for i in range(num_pixels):
                controller.set_pixel(i, colors.OFF)

            # Light up the window
            for j in range(window_size):
                pixel_index = position + j
                if pixel_index < num_pixels:
                    controller.set_pixel_color_list(pixel_index)

            # Show the strip
            controller.show()
            time.sleep(controller.delay)

            # Update position
            position += direction

            # Reverse direction at edges
            if position == 0 or position == num_pixels - window_size:
                direction *= -1

def allin(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.red_hue(i))
    strip.show()


def clock_timer(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.blue_hue(i*2))

def clock(strip):
    return clock_effects.clock(strip)


def clock2(strip):
    return clock_effects.clock2(strip)


def clock3(strip):
    return clock_effects.clock3(strip)


def clock4(strip):
    return clock_effects.clock4(strip)


def clock5(strip):
    return clock_effects.clock5(strip)


def clock6(strip):
    return clock_effects.clock6(strip)