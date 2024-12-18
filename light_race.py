import time
import random
import asyncio
from rpi_ws281x import PixelStrip, Color


# Define racers with their properties
racers = [
    {"color": Color(255, 0, 0), "position": 0, "probability": 0.5},  # Red racer
    {"color": Color(0, 255, 0), "position": 0, "probability": 0.5},  # Green racer
    {"color": Color(0, 0, 255), "position": 0, "probability": 0.5}   # Blue racer
]

winner_event = asyncio.Event()

def clear_strip(strip):
    """Turn off all LEDs."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()

async def display_winner(strip, winning_color):
    """Light up the entire strip with the winning color."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, winning_color)
    strip.show()

async def move_racer(strip, racer, winner_event):
    """Move a single racer asynchronously."""
    while not winner_event.is_set():
        await asyncio.sleep(0.1)  # Small delay for movement
        if random.random() < racer["probability"]:
            racer["position"] += 1

        # Stop if the racer reaches the end
        if racer["position"] >= strip.numPixels() - 1:
            print(f"Winner found: {racer}")
            winner_event.set()
            await display_winner(strip, racer["color"])

async def update_strip(strip, winner_event):
    """Update the LED strip asynchronously."""
    while not winner_event.is_set():
        clear_strip(strip)
        for racer in racers:
            position = min(racer["position"], strip.numPixels() - 1)
            strip.setPixelColor(position, racer["color"])
        strip.show()
        await asyncio.sleep(0.05)  # Refresh rate for visual updates

async def race(strip):
    """Main asynchronous race function."""
    global winner_event
    global racers

    #reset the strip
    clear_strip(strip)
    winner_event.clear()  
    for racer in racers:
        racer["position"] = 0

    # Create tasks for racers and LED updating
    tasks = [move_racer(strip, racer, winner_event) for racer in racers]
    tasks.append(update_strip(strip, winner_event))  # Add strip update task

    # Run all tasks until the winner is found
    await asyncio.gather(*tasks)

