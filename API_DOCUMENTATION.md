# LED Lighting Effects Project - API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Flask Applications](#flask-applications)
3. [Core Components](#core-components)
4. [Effect Functions](#effect-functions)
5. [Color Utilities](#color-utilities)
6. [LED Strip Controller](#led-strip-controller)
7. [Specialized Effects](#specialized-effects)
8. [Web Interface](#web-interface)
9. [Configuration](#configuration)
10. [Usage Examples](#usage-examples)

## Overview

This project provides a comprehensive LED lighting effects system designed for Raspberry Pi with WS281X LED strips. It features multiple Flask applications, a variety of lighting effects, color utilities, and a web-based control interface.

### Key Features
- Multiple Flask application variants (synchronous, asynchronous, controller-based)
- Rich collection of lighting effects (color wheels, animations, clocks, racing games)
- Text-to-light embedding using OpenAI
- Web-based control interface
- Configurable LED strip settings
- Real-time clock displays

---

## Flask Applications

### 1. Main Application (`app.py`)

Basic Flask application with simple route-based effect triggering.

#### Configuration
```python
LED_COUNT = 120          # Number of LEDs
LED_PIN = 18            # GPIO pin connected to the pixels (PWM pin)
LED_FREQ_HZ = 800000    # LED signal frequency (800kHz)
LED_DMA = 5             # DMA channel
LED_BRIGHTNESS = 255    # Brightness (0-255)
LED_INVERT = False      # Invert signal
LED_CHANNEL = 0         # PWM channel
```

#### API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/` | GET | Main interface | None |
| `/wheel` | GET | Trigger color wheel effect | None |
| `/warm-wheel` | GET | Trigger warm color wheel | None |
| `/lime-green` | GET | Set all LEDs to lime green | None |
| `/start-race` | GET | Start light racing game | None |
| `/text_effect` | POST | Text-to-LED effect | `{"text": "string"}` |
| `/flash` | GET | Flash effect | None |
| `/leapfrog` | GET | Leapfrog animation | None |
| `/bounce` | GET | Bouncing window effect | None |
| `/bits` | POST | Display binary data | `{"bits": [1,0,1,0...]}` |
| `/off` | GET | Turn all LEDs off | None |

#### Usage Example
```bash
# Start color wheel effect
curl http://localhost:5000/wheel

# Send text effect
curl -X POST http://localhost:5000/text_effect \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello World"}'

# Display binary data
curl -X POST http://localhost:5000/bits \
  -H "Content-Type: application/json" \
  -d '{"bits": [1,1,0,1,0,1,1,0]}'
```

### 2. Async Application (`async-app.py`)

Advanced Flask application with thread management and job control.

#### API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/` | GET | Async interface | None |
| `/poker-voice-control` | GET | Voice control interface | None |
| `/start` | POST | Start any effect | `{"effect": "string", "args": []}` |
| `/stop` | POST | Stop current effect | None |
| `/status` | GET | Get current status | None |

#### Available Effects
- `wheel`, `warm_wheel`, `lime_green`, `flash`, `leapfrog`
- `bounce`, `off`, `text_effect`, `race`
- `clock`, `clock2`, `clock3`, `clock4`, `clock5`, `clock6`
- `rollout`, `allin`

#### Usage Example
```bash
# Start color wheel effect
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d '{"effect": "wheel"}'

# Start text effect with parameters
curl -X POST http://localhost:5000/start \
  -H "Content-Type: application/json" \
  -d '{"effect": "text_effect", "args": ["Hello LED"]}'

# Check status
curl http://localhost:5000/status

# Stop current effect
curl -X POST http://localhost:5000/stop
```

### 3. Controller Application (`controller-app.py`)

Full-featured application with settings management and LED controller integration.

#### Additional API Endpoints

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/clocks` | GET | Clock effects interface | None |
| `/settings` | GET | Settings configuration page | None |
| `/update-settings` | POST | Update LED settings | Form data |
| `/get-settings` | GET | Get current settings | None |

#### Settings Management
```bash
# Update settings via form data
curl -X POST http://localhost:5000/update-settings \
  -d "color1=#ff0000&color2=#00ff00&color3=#0000ff&delay=20"

# Get current settings
curl http://localhost:5000/get-settings
```

---

## Core Components

### LED Strip Controller (`ledstrip.py`)

Object-oriented LED strip control with advanced configuration.

#### Class: LEDStripController

```python
class LEDStripController:
    def __init__(self)
    def set_colors(self, color_list)
    def get_colors(self)
    def set_delay(self, delay)
    def get_delay(self)
    def off(self)
    def set_pixel(self, index, color)
    def set_pixel_color_list(self, index)
    def show(self)
    def fill_color(self, color)
    def set_multiple_pixels(self, indices, color)
```

#### Usage Example
```python
from ledstrip import LEDStripController
import colors

# Initialize controller
controller = LEDStripController()

# Set custom colors
controller.set_colors([colors.RED, colors.GREEN, colors.BLUE])

# Set individual pixel
controller.set_pixel(0, colors.WHITE)
controller.show()

# Fill entire strip
controller.fill_color(colors.LIME_GREEN)

# Set multiple pixels
controller.set_multiple_pixels([0, 5, 10], colors.PURPLE)
```

---

## Effect Functions

### Basic Effects (`effects.py`)

#### Global Control
```python
def set_stop_flag(value: bool)  # Control effect stopping
```

#### Core Functions

##### `fill_strip(strip, color)`
Fill entire LED strip with a single color.
```python
import colors
from effects import fill_strip

fill_strip(strip, colors.RED)  # Fill with red
```

##### `color_wheel(controller)`
Animated rainbow color wheel effect.
```python
effects.color_wheel(controller)  # Continuous rainbow animation
```

##### `flash(controller)`
Alternating flash pattern between two colors.
```python
effects.flash(controller)  # Uses controller's color list
```

##### `leap_frog(controller)`
Moving window of lights that travels across the strip.
```python
effects.leap_frog(controller)  # 5-pixel window animation
```

##### `bouncing_window(controller)`
Window of lights that bounces back and forth.
```python
effects.bouncing_window(controller)  # Bouncing 5-pixel window
```

##### `warm_wheel(controller)`
Warm color (red, orange, yellow) wheel effect.
```python
effects.warm_wheel(controller)  # Warm color animation
```

##### `display_bits(strip, bits)`
Display binary data as colored pixels.
```python
bits = [1, 0, 1, 1, 0, 1, 0, 0]
effects.display_bits(strip, bits)
# 1 = Green, 0 = Off, -1 = Red
```

##### `roll_out(controller)`
Progressive rollout animation.
```python
effects.roll_out(controller)  # Progressive light rollout
```

### Clock Effects (`clock_effects.py`)

Specialized time display effects with various visualization styles.

#### Global Control
```python
def set_stop_flag(value: bool)  # Control clock stopping
```

#### Clock Functions

##### `clock(strip)` - Clock 1
Sectioned time display with offset markers.
- **Hours**: Blue (PM) or Red (AM), 12-hour format
- **Minutes**: Green pixels
- **Seconds**: Purple pixels (divided by 2)
- **Update**: Every second

```python
clock_effects.clock(strip)  # Basic sectioned clock
```

##### `clock2(strip)` - Clock 2
Full strip utilization with position-based time.
- **Hours**: 10-pixel blocks for each hour
- **Minutes**: 2-pixel markers
- **Seconds**: 2-pixel markers

```python
clock_effects.clock2(strip)  # Position-based clock
```

##### `clock3(strip)` - Clock 3
Filled time display with progressive illumination.
- Fills pixels progressively based on time values
- Smart overlapping logic for different time units

```python
clock_effects.clock3(strip)  # Progressive fill clock
```

##### `clock4(strip)` - Clock 4
Marker-based time display.
- Uses markers every 10 units
- Distinct visualization for each time component

```python
clock_effects.clock4(strip)  # Marker-based clock
```

##### `clock5(strip)` - Clock 5
Rollout animation for seconds.
- Real-time second rollout animation
- Dynamic timing based on current second

```python
clock_effects.clock5(strip)  # Rollout animation clock
```

##### `clock6(strip)` - Clock 6 (Async)
Advanced async clock with smooth animations.
- **Async function** - requires `await`
- Smooth rollout animations
- Marker system for readability

```python
await clock_effects.clock6(strip)  # Advanced async clock
```

---

## Color Utilities

### Color Constants (`colors.py`)

#### Predefined Colors
```python
OFF = Color(0, 0, 0)          # Black/Off
RED = Color(255, 0, 0)        # Pure Red
GREEN = Color(0, 255, 0)      # Pure Green
BLUE = Color(0, 0, 255)       # Pure Blue
YELLOW = Color(150, 100, 0)   # Yellow
ORANGE = Color(200, 20, 0)    # Orange
PURPLE = Color(255, 0, 255)   # Purple/Magenta
WHITE = Color(255, 255, 255)  # White
LIME_GREEN = Color(50, 205, 50)  # Lime Green
```

#### Color Generation Functions

##### `wheel(pos)` - Rainbow Colors
Generate rainbow colors based on position (0-255).
```python
color = colors.wheel(128)  # Middle of color spectrum
for i in range(256):
    color = colors.wheel(i)  # Full rainbow cycle
```

##### `warm_wheel(pos)` - Warm Colors
Generate warm colors (red, orange, yellow) based on position.
```python
warm_color = colors.warm_wheel(85)  # Warm orange
for i in range(256):
    color = colors.warm_wheel(i)  # Warm color cycle
```

##### Hue Functions
```python
colors.red_hue(brightness)    # Red with variable brightness
colors.blue_hue(brightness)   # Blue with variable brightness  
colors.green_hue(brightness)  # Green with variable brightness
```

#### Usage Examples
```python
import colors
from rpi_ws281x import Color

# Use predefined colors
strip.setPixelColor(0, colors.RED)
strip.setPixelColor(1, colors.LIME_GREEN)

# Generate rainbow
for i in range(strip.numPixels()):
    color = colors.wheel((i * 256 // strip.numPixels()) % 256)
    strip.setPixelColor(i, color)

# Create custom color
custom_color = Color(128, 64, 192)  # Custom RGB
```

---

## Specialized Effects

### Text-to-Light Embeddings (`embeddings.py`)

Convert text to LED patterns using OpenAI embeddings.

#### Configuration
Requires OpenAI API key in environment variable:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

#### Functions

##### `get_embeddings(text)`
Generate OpenAI embeddings for input text.
```python
embeddings = get_embeddings("Hello World")
# Returns 120-dimensional embedding vector
```

##### `display_text_as_lights(strip, text)`
Display text as LED pattern using embeddings.
```python
embeddings.display_text_as_lights(strip, "Machine Learning")
# Converts text to unique LED color pattern
```

#### Normalization Functions
Various methods to convert embeddings to LED colors:

```python
# Basic normalization
normalize_embeddings(embeddings, count)

# Dynamic range mapping
normalize_dynamic_embeddings(embeddings, count)

# Custom normalization
normalize_custom_embeddings(embeddings, count)

# Sinusoidal transformation
normalize_color_transform_embeddings(embeddings, count)

# With noise addition
normalize_embeddings_with_noise(embeddings, count)

# HSV color space
normalize_embeddings_hsv(embeddings, count)
```

#### Usage Example
```python
from embeddings import display_text_as_lights

# Convert text to lights
display_text_as_lights(strip, "Data Science")
display_text_as_lights(strip, "Rainbow Colors")
display_text_as_lights(strip, "LED Effects")
```

### Light Racing Game (`light_race.py`)

Async racing game with multiple colored racers.

#### Racer Configuration
```python
racers = [
    {"color": Color(255, 0, 0), "position": 0, "probability": 0.5},  # Red
    {"color": Color(0, 255, 0), "position": 0, "probability": 0.5},  # Green  
    {"color": Color(0, 0, 255), "position": 0, "probability": 0.5}   # Blue
]
```

#### Functions

##### `race(strip)` - Main Race Function
Start an async racing game.
```python
await light_race.race(strip)
# Race until one racer reaches the end
```

##### Helper Functions
```python
clear_strip(strip)                    # Clear all LEDs
display_winner(strip, winning_color)  # Show winner
move_racer(strip, racer, winner_event)  # Move individual racer
update_strip(strip, winner_event)     # Update display
```

#### Usage Example
```python
import asyncio
import light_race

# Start a race
await light_race.race(strip)

# Custom race with modified probabilities
light_race.racers[0]["probability"] = 0.7  # Make red faster
await light_race.race(strip)
```

---

## Web Interface

### Frontend Components

#### JavaScript API (`static/index.js`)

##### `triggerEndpoint(endpoint, data)`
Send POST requests to effect endpoints.
```javascript
// Basic effect trigger
await triggerEndpoint('/start', { effect: 'wheel' });

// Effect with parameters
await triggerEndpoint('/start', { 
    effect: 'text_effect', 
    args: ['Hello World'] 
});
```

##### `sendTextEffect()`
Helper function for text effects.
```javascript
// Called by text input form
sendTextEffect();  // Reads from textInput field
```

#### HTML Templates

##### Main Interface (`async.html`)
Primary control interface with buttons for all effects.

**Available Controls:**
- Color Wheel Effect
- Warm Wheel Effect
- Lime Green
- Start Race
- Text Effect (with input field)
- Flash, Leap Frog, Bounce, Rollout
- Turn Off
- Navigation to specialized pages

##### Specialized Pages
- `clocks.html` - Clock effect controls
- `settings.html` - LED configuration
- `voice-control.html` - Voice control interface

#### CSS Styling (`static/styles.css`)
Responsive design with centered layout and styled buttons.

### API Integration Examples

#### JavaScript Usage
```javascript
// Start color wheel
triggerEndpoint('/start', { effect: 'wheel' });

// Start text effect
triggerEndpoint('/start', { 
    effect: 'text_effect', 
    args: ['Machine Learning'] 
});

// Check status
fetch('/status').then(response => response.json());

// Stop current effect
triggerEndpoint('/stop', {});
```

#### Python Requests
```python
import requests

# Start effect
requests.post('http://localhost:5000/start', 
              json={'effect': 'flash'})

# Text effect
requests.post('http://localhost:5000/start',
              json={'effect': 'text_effect', 'args': ['Hello']})

# Stop effect
requests.post('http://localhost:5000/stop')

# Get status
response = requests.get('http://localhost:5000/status')
status = response.json()
```

---

## Configuration

### LED Strip Settings
```python
# Hardware configuration
LED_COUNT = 120          # Number of LEDs in strip
LED_PIN = 18            # GPIO pin (PWM capable)
LED_FREQ_HZ = 800000    # Signal frequency
LED_DMA = 5             # DMA channel
LED_BRIGHTNESS = 255    # Global brightness (0-255)
LED_INVERT = False      # Signal inversion
LED_CHANNEL = 0         # PWM channel
```

### Environment Variables
```bash
# Required for text effects
OPENAI_API_KEY="your-openai-api-key"
```

### Controller Settings
```python
# Via LEDStripController
controller.set_colors([colors.RED, colors.GREEN, colors.BLUE])
controller.set_delay(500)  # Milliseconds between updates
```

---

## Usage Examples

### Basic Setup
```python
from rpi_ws281x import PixelStrip
from ledstrip import LEDStripController
import effects
import colors

# Method 1: Direct strip control
strip = PixelStrip(120, 18, 800000, 5, False, 255, 0)
strip.begin()
effects.fill_strip(strip, colors.RED)

# Method 2: Using controller
controller = LEDStripController()
controller.fill_color(colors.BLUE)
```

### Effect Sequences
```python
import time

# Color sequence
colors_sequence = [colors.RED, colors.GREEN, colors.BLUE, colors.WHITE]
for color in colors_sequence:
    effects.fill_strip(strip, color)
    time.sleep(1)

# Pattern sequence
effects.color_wheel(controller)
time.sleep(5)
effects.flash(controller)
time.sleep(3)
effects.bouncing_window(controller)
```

### Async Effects
```python
import asyncio

async def effect_sequence():
    await light_race.race(strip)
    await clock_effects.clock6(strip)

# Run async sequence
asyncio.run(effect_sequence())
```

### Web API Integration
```python
import requests

base_url = "http://localhost:5000"

# Start rainbow effect
requests.post(f"{base_url}/start", json={"effect": "wheel"})

# Wait and switch to clock
time.sleep(10)
requests.post(f"{base_url}/start", json={"effect": "clock"})

# Turn off after delay
time.sleep(30)
requests.post(f"{base_url}/start", json={"effect": "off"})
```

### Custom Effect Development
```python
def custom_effect(controller):
    """Custom breathing effect"""
    while not effects.stop_flag:
        for brightness in range(0, 255, 5):
            if effects.stop_flag:
                break
            color = colors.Color(brightness, 0, 0)
            controller.fill_color(color)
            time.sleep(0.05)
        
        for brightness in range(255, 0, -5):
            if effects.stop_flag:
                break
            color = colors.Color(brightness, 0, 0)
            controller.fill_color(color)
            time.sleep(0.05)

# Use custom effect
custom_effect(controller)
```

---

## Error Handling

### Common Issues and Solutions

#### Hardware Issues
```python
# Check if strip initializes properly
try:
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()
    print("Strip initialized successfully")
except Exception as e:
    print(f"Strip initialization failed: {e}")
```

#### API Error Handling
```python
# Web API error handling
try:
    response = requests.post('/start', json={'effect': 'invalid'})
    if response.status_code != 200:
        print(f"API Error: {response.json()}")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

#### Effect Control
```python
# Proper effect stopping
try:
    effects.set_stop_flag(True)  # Stop current effect
    time.sleep(0.5)  # Allow time to stop
    effects.set_stop_flag(False)  # Reset for next effect
except Exception as e:
    print(f"Effect control error: {e}")
```

---

This documentation provides comprehensive coverage of all public APIs, functions, and components in the LED lighting effects project. Each section includes detailed explanations, parameter descriptions, and practical usage examples to help developers effectively utilize the system.