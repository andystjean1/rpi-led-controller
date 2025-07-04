import time
from datetime import datetime as dt
import asyncio
import random
import math

import pytz
import rpi_ws281x
import colors

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

def pulse(controller):
    """Breathing/pulsing effect using brightness modulation."""
    num_pixels = controller.numPixels
    pulse_speed = 0.05
    
    while not stop_flag:
        for brightness_step in range(256):
            if stop_flag:
                break
            
            # Calculate brightness using sine wave for smooth pulse
            brightness = int((math.sin(brightness_step * pulse_speed) + 1) * 127.5)
            
            for i in range(num_pixels):
                color = controller.color_list[i % len(controller.color_list)]
                # Scale color by brightness
                r = ((color >> 16) & 0xFF) * brightness // 255
                g = ((color >> 8) & 0xFF) * brightness // 255
                b = (color & 0xFF) * brightness // 255
                dimmed_color = rpi_ws281x.Color(r, g, b)
                controller.set_pixel(i, dimmed_color)
            
            controller.show()
            time.sleep(controller.delay)

def wave(controller):
    """Wave effect that moves across the strip."""
    num_pixels = controller.numPixels
    wave_length = 20  # Length of one complete wave
    
    while not stop_flag:
        for offset in range(wave_length):
            if stop_flag:
                break
            
            for i in range(num_pixels):
                # Calculate wave position
                wave_pos = (i + offset) % wave_length
                intensity = int((math.sin(2 * math.pi * wave_pos / wave_length) + 1) * 127.5)
                
                # Use primary color with wave intensity
                color = controller.color_list[0]
                r = ((color >> 16) & 0xFF) * intensity // 255
                g = ((color >> 8) & 0xFF) * intensity // 255
                b = (color & 0xFF) * intensity // 255
                wave_color = rpi_ws281x.Color(r, g, b)
                
                controller.set_pixel(i, wave_color)
            
            controller.show()
            time.sleep(controller.delay)

def sparkle(controller):
    """Random twinkling sparkle effect."""
    num_pixels = controller.numPixels
    sparkle_density = 0.1  # Probability of a pixel sparkling
    
    while not stop_flag:
        # Clear the strip
        for i in range(num_pixels):
            controller.set_pixel(i, colors.OFF)
        
        # Add random sparkles
        num_sparkles = int(num_pixels * sparkle_density)
        for _ in range(num_sparkles):
            if stop_flag:
                break
            pixel = random.randint(0, num_pixels - 1)
            color = controller.color_list[random.randint(0, len(controller.color_list) - 1)]
            controller.set_pixel(pixel, color)
        
        controller.show()
        time.sleep(controller.delay * 2)  # Slower for sparkle effect

def chase(controller):
    """Multiple dots chasing each other around the strip."""
    num_pixels = controller.numPixels
    num_chasers = 3
    chase_spacing = num_pixels // num_chasers
    
    position = 0
    while not stop_flag:
        # Clear the strip
        for i in range(num_pixels):
            controller.set_pixel(i, colors.OFF)
        
        # Draw chasers
        for chaser in range(num_chasers):
            if stop_flag:
                break
            chaser_pos = (position + chaser * chase_spacing) % num_pixels
            color = controller.color_list[chaser % len(controller.color_list)]
            
            # Draw chaser with tail
            for tail in range(5):
                tail_pos = (chaser_pos - tail) % num_pixels
                # Fade the tail
                brightness = max(0, 255 - tail * 51)  # Fade over 5 pixels
                r = ((color >> 16) & 0xFF) * brightness // 255
                g = ((color >> 8) & 0xFF) * brightness // 255
                b = (color & 0xFF) * brightness // 255
                tail_color = rpi_ws281x.Color(r, g, b)
                controller.set_pixel(tail_pos, tail_color)
        
        controller.show()
        time.sleep(controller.delay)
        position = (position + 1) % num_pixels

def gradient_fade(controller):
    """Smooth color transitions across the entire strip."""
    num_pixels = controller.numPixels
    fade_steps = 256
    
    color_index = 0
    while not stop_flag:
        current_color = controller.color_list[color_index % len(controller.color_list)]
        next_color = controller.color_list[(color_index + 1) % len(controller.color_list)]
        
        # Fade between current and next color
        for step in range(fade_steps):
            if stop_flag:
                break
            
            # Calculate interpolated color
            factor = step / fade_steps
            r1, g1, b1 = (current_color >> 16) & 0xFF, (current_color >> 8) & 0xFF, current_color & 0xFF
            r2, g2, b2 = (next_color >> 16) & 0xFF, (next_color >> 8) & 0xFF, next_color & 0xFF
            
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            
            interpolated_color = rpi_ws281x.Color(r, g, b)
            
            # Apply to all pixels
            for i in range(num_pixels):
                controller.set_pixel(i, interpolated_color)
            
            controller.show()
            time.sleep(controller.delay / 2)  # Slower fade
        
        color_index += 1