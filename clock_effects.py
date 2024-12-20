import time
from datetime import datetime as dt
import asyncio

import pytz
import rpi_ws281x
import colors

stop_flag = False
def set_stop_flag(value: bool):
    global stop_flag
    stop_flag = value

def clock(strip):
    """clock 1 : theres some sections and offsets every 2 seconds, seconds updates"""
    num_pixels = strip.numPixels()
    timezone = pytz.timezone('America/New_York')
    
    offset = 2
    hour_offset = 12
    minute_offset = 60

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

        hour_start = (hour % 12) * 10
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

        hour_start_idx = (hour % 12) * 10
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
        if(min_start <= hour_start_idx):
            print("dots")
            strip.setPixelColor(min_start, minute_color)
            strip.setPixelColor(min_start+1, minute_color)
        
        else:
            print("fill")
            for i in range(hour_start_idx, min_start):
                strip.setPixelColor(i, minute_color)

        # set the second depenedent on the minute
        if(sec_start <= max(hour_start_idx, min_start)):
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

        hour_start = (hour % 12) * 10
        min_start = minute * 2
        sec_start = second * 2

        # blue for PM, red for AM
        hour_color = colors.BLUE if hour >= 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE

        #clear board
        for i in range(num_pixels):
                strip.setPixelColor(i, colors.OFF)

        #draw the minute markers
        minute_max = (min_start//10) * 10
        minute_markers = [minute_max - i for i in range(1, min_start, 10)]
        extra_min = min_start - minute_max
        minute_markers.extend([minute_max + i for i in range(extra_min) if i % 2])
    
        for i in minute_markers:
            strip.setPixelColor(i, minute_color)

        hour_max = (hour_start // 10) * 10
        hour_markers = [hour_max - i for i in range(1, hour_start, 10)]
        for i in hour_markers:
                strip.setPixelColor(i, hour_color)
        

        if(extra_min == 0):
            strip.setPixelColor(minute_max -1, minute_color)

        # draw the seconds  
        strip.setPixelColor(sec_start, second_color)
        strip.setPixelColor(sec_start+1, second_color)
            
        strip.show()
        time.sleep(1)


def clock5(strip):
    "clock with markers"
    num_pixels = strip.numPixels()
    timezone = pytz.timezone('America/New_York')

    while not stop_flag:
        ct = dt.now(timezone).time()
        hour = ct.hour
        minute = ct.minute
        second = ct.second

        print("first", hour, minute, second, sep=":")

        hour_start = (hour % 12) * 10
        min_start = minute * 2
        sec_start = second * 2

        # blue for PM, red for AM
        hour_color = colors.BLUE if hour >= 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE

        for i in (range(num_pixels)):
            strip.setPixelColor(i, colors.OFF)

        #light up the strip
        for j in (range(sec_start-1)):
            strip.setPixelColor(j, second_color)

        #loop through and rollout
        for j in (range(1, sec_start)):
            strip.setPixelColor(j, colors.OFF)
            strip.setPixelColor(j - 1, second_color)
            strip.show()
            time.sleep(1 / second) #this should always make the rollout take one second
        
            
        strip.show()

async def clock6(strip):
    """Clock with rollout animation for seconds."""
    global stop_flag
    num_pixels = strip.numPixels()
    timezone = pytz.timezone("America/New_York")

    while not stop_flag:
        ct = dt.now(timezone).time()
        hour = ct.hour
        minute = ct.minute
        second = ct.second

        # Calculate LED positions
        hour_start = (hour % 12) * (num_pixels // 12)  # Hour markers
        min_start = (minute * num_pixels) // 60       # Minute markers
        sec_start = (second * num_pixels) // 60       # Second markers

        # Colors
        hour_color = colors.BLUE if hour >= 12 else colors.RED
        minute_color = colors.GREEN
        second_color = colors.PURPLE
        marker_color = colors.YELLOW

        # Clear the strip
        for i in range(num_pixels):
            strip.setPixelColor(i, colors.OFF)

        # Add markers every 5 minutes
        for i in range(0, num_pixels, num_pixels // 12):
            strip.setPixelColor(i, marker_color)

        # Set hour and minute markers
        strip.setPixelColor(hour_start, hour_color)
        strip.setPixelColor(min_start, minute_color)

        # Rollout animation for seconds
        rollout_steps = sec_start  # Number of steps for the animation
        delay = 1.0 / rollout_steps if rollout_steps > 0 else 1.0  # Calculate step delay

        for j in range(rollout_steps):
            if stop_flag:
                break
            strip.setPixelColor(j, second_color)
            strip.show()
            await asyncio.sleep(delay)

        # Turn off the second's rollout once complete
        for j in range(rollout_steps):
            if stop_flag:
                break
            strip.setPixelColor(j, colors.OFF)

        # Show the strip
        strip.show()

        # Wait for the next update
        await asyncio.sleep(1 - delay * rollout_steps if rollout_steps > 0 else 1)

