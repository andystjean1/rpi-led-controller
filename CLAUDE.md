# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Raspberry Pi LED strip controller that provides a Flask-based web interface to control WS281x LED strips (120 LEDs). The project includes various visual effects, clock displays, and customizable color patterns.

## Architecture

### Core Application Structure

**Two Flask Applications:**
- `async-app.py` - Main production application with thread-based effect management, settings persistence, and proper job lifecycle management
- `app.py` - Legacy/simpler application without threading or advanced controls (avoid using)

**Key Pattern: Thread-Based Effect Execution**

The application runs long-running LED effects in background threads while maintaining Flask responsiveness:
- `effect_runner()` manages starting/stopping effects in threads
- Global `stop_flag` variables in `effects.py` and `clock_effects.py` signal effects to terminate
- `effect_lock` prevents concurrent effect execution
- Each effect checks `stop_flag` periodically and exits cleanly when True

### Module Responsibilities

**ledstrip.py**
- `LEDStripController` class wraps `rpi_ws281x.PixelStrip` with higher-level abstractions
- Manages configurable color lists and timing delays
- Provides methods: `set_pixel()`, `set_pixel_color_list()`, `fill_color()`, `off()`

**effects.py**
- Contains LED effect implementations (color_wheel, flash, leap_frog, bouncing_window, warm_wheel, roll_out, etc.)
- All effects accept a controller object (either `LEDStripController` or `StripControllerAdapter`)
- Effects run in infinite loops checking `stop_flag` for graceful termination
- `set_stop_flag(value: bool)` manages the global stop flag

**clock_effects.py**
- Six different clock visualizations (clock, clock2, clock3, clock4, clock5, clock6)
- Uses `pytz` for America/New_York timezone
- Maps hours/minutes/seconds to LED positions using different algorithms
- clock6 is async and uses rollout animations

**colors.py**
- Predefined color constants (RED, GREEN, BLUE, YELLOW, PURPLE, etc.)
- Color generation functions: `wheel()` for rainbow, `warm_wheel()` for warm tones
- Color components use `rpi_ws281x.Color(r, g, b)` format

**light_race.py**
- Contains race animation effects (not examined in detail)

**embeddings.py**
- Text-to-LED effects using embeddings (not examined in detail)

### Controller Adapter Pattern

`async-app.py` uses `StripControllerAdapter` to provide controller-style methods while using the raw `PixelStrip` internally. This allows effects to work with both `LEDStripController` and `StripControllerAdapter` interfaces interchangeably.

## Development Commands

### Running the Application

**Production (main application):**
```bash
python async-app.py
```

**Access web interface:** `http://localhost:5000/`

**Additional pages:**
- `/clocks` - Clock effect controls
- `/settings` - Customize colors and timing
- `/poker-voice-control` - Voice control interface

### Testing

**Run all tests:**
```bash
pytest
```

**Run tests with verbose output:**
```bash
pytest -v
```

**Run specific test file:**
```bash
pytest tests/test_async_app.py
```

**Test module uses:**
- `FakePixelStrip` class to mock hardware during testing
- Monkeypatching `rpi_ws281x` module
- Threading events to synchronize test execution

### Deployment

**Deploy to Raspberry Pi:**
```bash
./deploy.sh
```

This syncs code to the Pi at `10.1.10.72` using rsync and SSH. The application runs on the Pi at `/opt/rpi-led-controller`.

## Hardware Configuration

**LED Strip Settings (in ledstrip.py and async-app.py):**
- LED_COUNT: 120
- LED_PIN: 18 (GPIO PWM pin)
- LED_FREQ_HZ: 800000
- LED_DMA: 5
- LED_BRIGHTNESS: 255

## API Endpoints

**Effect Control:**
- `POST /start` - Start an effect: `{"effect": "wheel", "args": []}`
- `POST /stop` - Stop current effect
- `GET /status` - Get current effect status

**Settings:**
- `POST /update-settings` - Update colors (hex format) and delay (milliseconds)
- `GET /get-settings` - Retrieve current settings

**Available Effects:**
wheel, warm_wheel, lime_green, flash, leapfrog, bounce, off, race, clock, clock2, clock3, clock4, clock5, clock6, rollout, allin

## Adding New Effects

1. Implement effect function in `effects.py` or `clock_effects.py`
2. Accept controller parameter (with `.numPixels`, `.set_pixel()`, `.show()`, `.delay` attributes)
3. Include `stop_flag` checks in all loops: `while not stop_flag:`
4. Add effect to `jobs` dictionary in `async-app.py`:
   ```python
   jobs = {
       "my_effect": lambda: effects.my_effect(controller),
   }
   ```

## Important Implementation Details

**Thread Safety:**
- Only one effect runs at a time (enforced by `effect_lock`)
- Stopping an effect sets `stop_flag=True` and waits for thread completion
- Always reset stop flags after stopping: `reset_stop_flags()`

**Async Support:**
- `effect_runner()` detects awaitable return values and runs them with `asyncio.run()`
- Effects can be either synchronous or async (clock6 is async)

**Testing LED Code Without Hardware:**
- Use `FakePixelStrip` pattern from test_async_app.py
- Mock `rpi_ws281x` module in sys.modules before importing app code
