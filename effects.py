
import rpi_ws281x
import colors
import time
from datetime import datetime as dt
import pytz

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
    while True and not stop_flag:
        for j in range(256):  # 0-255 for color wheel
            if stop_flag:
                break
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
        if stop_flag:
            break
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
        if stop_flag:
            break
        for i in range(num_pixels):
            if stop_flag:
                break
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
        if stop_flag:
            break
        for i in range(num_pixels):
            if stop_flag:
                break
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

def bouncing_window(strip, window_size=5, iterations=10, wait_ms=10):
    num_pixels = strip.numPixels()
    direction = 1  # 1 for forward, -1 for backward
    position = 0

    for _ in range(iterations):
        if stop_flag:
            break
        for _ in range(num_pixels - window_size + 1):
            if stop_flag:
                break
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

def clock(strip):
    """clock 1 : theres some sections and offsets every 2 seconds, seconds updates"""
    num_pixels = strip.numPixels()
    timezone = pytz.timezone('America/New_York')
    
    offset = 2
    hour_offset = 12
    minute_offset = 60
    second_offset = 30

    while True and not stop_flag:
        start_idx = 6

        ct = dt.now(timezone).time()
        hour = ct.hour
        minute = ct.minute
        second = ct.second

        print("first", hour, minute, second, sep=":")
        
        hour_limit = hour % 12
        second_limit = second // 2

        print("second", hour_limit, minute, second_limit, sep=":")

        # blue for PM, red for AM
        hour_color = colors.BLUE if hour > 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE

        #clear board
        for i in range(num_pixels):
                strip.setPixelColor(i, colors.OFF)

        #set hour pixels
        for i in range(hour_limit):
            strip.setPixelColor(start_idx + i, hour_color)
        
        start_idx += (offset + hour_offset)
        print(start_idx)

        #set minute pixels
        for i in range(minute):
            strip.setPixelColor(start_idx + i, minute_color)

        #set second pixels
        start_idx += (minute_offset + offset)
        print(start_idx)
        for i in range(second_limit):
            strip.setPixelColor(start_idx + i, second_color)

        strip.show()
        time.sleep(1)

def clock2(strip):
    """utilizes the whole strip"""
    num_pixels = strip.numPixels()
    timezone = pytz.timezone('America/New_York')

    while True and not stop_flag:

        ct = dt.now(timezone).time()
        hour = ct.hour
        minute = ct.minute
        second = ct.second

        print("first", hour, minute, second, sep=":")

        hour_start = hour * 10
        min_start = minute * 2
        sec_start = second * 2

        # blue for PM, red for AM
        hour_color = colors.BLUE if hour > 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE

        #clear board
        for i in range(num_pixels):
                strip.setPixelColor(i, colors.OFF)

        #set the hour pixels
        for i in range(hour_start - 10, hour_start):
            strip.setPixelColor(i, hour_color)

        #set the minutes
        strip.setPixelColor(min_start, minute_color)
        strip.setPixelColor(min_start + 1, minute_color)

        # set the seconds
        strip.setPixelColor(sec_start, second_color)
        strip.setPixelColor(sec_start + 1, second_color)
        
        strip.show()
        time.sleep(1)

def clock3(strip):
    "clock2 with fill"
    num_pixels = strip.numPixels()
    timezone = pytz.timezone('America/New_York')

    while True and not stop_flag:

        ct = dt.now(timezone).time()
        hour = ct.hour
        minute = ct.minute
        second = ct.second

        print("first", hour, minute, second, sep=":")
        
        hour_limit = hour % 12
        second_limit = second // 2

        print("second", hour_limit, minute, second_limit, sep=":")

        hour_start_idx = hour * 10
        min_start = minute * 2
        sec_start = second * 2

        # blue for PM, red for AM
        hour_color = colors.BLUE if hour > 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE

        #clear board
        for i in range(num_pixels):
                strip.setPixelColor(i, colors.OFF)
    
        #set the hour pixels
        for i in range(hour_start_idx):
            strip.setPixelColor(i, hour_color)

       
        # set the minute dependent on the hour
        if(min_start < hour_start_idx):
            print("dots")
            strip.setPixelColor(min_start, minute_color)
            strip.setPixelColor(min_start+1, minute_color)
        
        else:
            print("fill")
            for i in range(hour_start_idx, min_start):
                strip.setPixelColor(i, minute_color)

        # set the second depenedent on the minute
        if(sec_start < min_start):
            print("dots")
            strip.setPixelColor(sec_start, second_color)
            strip.setPixelColor(sec_start+1, second_color)
        
        else:
            print("fill")
            for i in range(min_start, sec_start):
                strip.setPixelColor(i, second_color)
        
        strip.show()
        time.sleep(1)


def clock4(strip):
    "clock with markers"
    num_pixels = strip.numPixels()
    timezone = pytz.timezone('America/New_York')

    while True and not stop_flag:
        ct = dt.now(timezone).time()
        hour = ct.hour
        minute = ct.minute
        second = ct.second

        print("first", hour, minute, second, sep=":")

        hour_start = hour * 10
        min_start = minute * 2
        sec_start = second * 2

        # blue for PM, red for AM
        hour_color = colors.BLUE if hour > 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE

        #clear board
        for i in range(num_pixels):
                strip.setPixelColor(i, colors.OFF)
    
        #draw marker for every five minuts
        marker_max = (min_start // 10) * 10
        for i in range(min_start):
            if(i >= marker_max):
                print("drawing loops", i, min_start, sep=":")
                for j in range(i, min_start):
                    strip.setPixelColor(j, minute_color if j % 2 else colors.OFF)
                break
            elif(i % 10 == 0):
                strip.setPixelColor(i, minute_color)
                strip.setPixelColor(i+1, minute_color)
            else:
                strip.setPixelColor(i, colors.OFF)
                
        #set the hour pixels
        for i in range(hour_start):
            strip.setPixelColor(i, hour_color if (i != 0 and (i+1) % 10 == 0) else colors.OFF)

        # draw the seconds  
        strip.setPixelColor(sec_start, second_color)
        strip.setPixelColor(sec_start+1, second_color)
            
        strip.show()
        time.sleep(1)




