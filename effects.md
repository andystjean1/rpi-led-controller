# LED Strip Effects Documentation

## Strip Configurations

### Strip 1: Linear Strip (120 LEDs - GPIO Pin 18)
- **Layout**: Linear arrangement
- **LED Count**: 120 pixels
- **Use Cases**: General animations, effects, and clock displays
- **Compatible Effects**: All effects work on this strip

### Strip 2: Matrix Strip (240 LEDs - GPIO Pin 19)
- **Layout**: 2D Matrix arrangement (4 rows × 60 columns, serpentine layout)
- **LED Count**: 240 pixels
- **Use Cases**: 2D animations, patterns, text displays, and matrix-specific effects
- **Compatible Effects**: All Strip 1 effects work, PLUS 13 matrix-specific effects

**Matrix Layout**:
```
Row 0:  [0   →   59]    (left to right)
Row 1:  [119 ←   60]    (right to left - serpentine)
Row 2:  [120 →   179]   (left to right)
Row 3:  [239 ←   180]   (right to left - serpentine)
```

**Note**: Strip 2 can run both linear effects (treating it as a 240-LED strip) and matrix-specific effects (utilizing the 4×60 2D layout). Matrix effects are implemented in `matrix_effects.py` and accessible via the `/matrix` web interface.

---

## Universal Effects (Work on Both Strips)

### 🌈 Color Wheel
**Function**: `color_wheel(controller)`
**File**: `effects.py:27`

**Description**:
Cycles through the full RGB color spectrum creating a rainbow effect that moves along the entire strip.

**How It Works**:
- Iterates through 256 color positions (0-255)
- Each LED gets a color based on its position plus the current cycle offset
- Creates a smooth rainbow that appears to flow along the strip
- Uses the `colors.wheel()` function to generate RGB values

**Visual Effect**:
Imagine a rainbow that continuously scrolls from start to end, with each LED showing a different color that smoothly transitions through red, orange, yellow, green, cyan, blue, purple, and back to red.

**Customizable**:
- Speed controlled by `controller.delay` setting

---

### 🔥 Warm Wheel
**Function**: `warm_wheel(controller)`
**File**: `effects.py:113`

**Description**:
Similar to Color Wheel but restricted to warm colors (reds, oranges, yellows) creating a cozy, fire-like effect.

**How It Works**:
- Creates a 5-LED wide window that moves along the strip
- Each LED in the window gets a warm color from the `colors.warm_wheel()` function
- Window wraps around from end to start
- Clears LEDs behind the window as it moves

**Visual Effect**:
A wave of warm, fire-like colors (red → orange → yellow) flows smoothly along the strip, like watching embers flow.

**Customizable**:
- Speed controlled by `controller.delay`
- Window size: 5 LEDs

---

### ⚡ Flash
**Function**: `flash(controller)`
**File**: `effects.py:42`

**Description**:
Creates an alternating checkerboard pattern that flips between two colors.

**How It Works**:
- Divides the strip into even and odd positioned LEDs
- Alternates which set gets which color from `controller.color_list`
- Pattern flips every delay cycle
- Formula: `(iteration % 2) == (pixel_position % 2)`

**Visual Effect**:
Like a racing finish line flag, alternating colors flash back and forth creating a strobe-like checkerboard effect.

**Customizable**:
- Uses first two colors from color settings
- Speed controlled by `controller.delay`

---

### 🐸 Leap Frog
**Function**: `leap_frog(controller)`
**File**: `effects.py:56`

**Description**:
A 5-LED window of colors that "leaps" around the strip in a continuous loop.

**How It Works**:
- Creates a 5-LED window that displays colors from `controller.color_list`
- Window moves one position at a time
- Wraps around: when it reaches the end, continues from the start
- Clears the LED just before the window
- Uses `set_pixel_color_list()` to cycle through configured colors

**Visual Effect**:
A small group of colored LEDs hops along the strip like a frog leaping from lily pad to lily pad.

**Customizable**:
- Colors from color settings (cycles through all three)
- Speed controlled by `controller.delay`
- Window size: 5 LEDs

---

### 🏀 Bounce
**Function**: `bouncing_window(controller)`
**File**: `effects.py:135`

**Description**:
A window of colored LEDs bounces back and forth between the ends of the strip like a ball bouncing between walls.

**How It Works**:
- 5-LED window starts at one end
- Moves forward until hitting the far end
- Reverses direction and moves back
- Continuously bounces back and forth
- Clears entire strip each frame for clean animation
- Direction tracked with variable: 1 (forward) or -1 (backward)

**Visual Effect**:
Like watching a beam of light or a ball bounce from one end to the other, reversing direction at each boundary.

**Customizable**:
- Colors from color settings (cycles through configured colors)
- Speed controlled by `controller.delay`
- Window size: 5 LEDs

---

### 📜 Rollout
**Function**: `roll_out(controller)`
**File**: `effects.py:89`

**Description**:
Creates a "rolling out carpet" effect where LEDs light up progressively, then roll back to the start, repeating the animation.

**How It Works**:
- Lights up LEDs sequentially from position 0 to current position
- Then "rolls out" by turning off LEDs from the end back to start
- Each iteration extends one LED further
- Creates a wave-like expanding and contracting effect

**Visual Effect**:
Like unfurling a scroll or carpet, the light expands forward then rolls back, growing longer with each cycle.

**Customizable**:
- Uses first color from color settings
- Speed controlled by `controller.delay`

---

### 💤 Turn Off
**Function**: `fill_strip(strip, colors.OFF)`
**File**: `effects.py:20`

**Description**:
Immediately turns off all LEDs on the strip.

**How It Works**:
- Sets every LED to color value 0,0,0 (OFF)
- Single operation, no animation
- Used to reset the strip

**Visual Effect**:
All lights instantly go dark.

---

### 🏁 Race
**Function**: `race(strip)`
**File**: `light_race.py:51`

**Description**:
An async racing game where three colored "racers" (red, green, blue) race to the end of the strip. First one to reach the end wins and the entire strip lights up with the winner's color.

**How It Works**:
- Three racers start at position 0
- Each racer has a 50% probability to advance each update (0.1s)
- All racers move independently and asynchronously
- Strip refreshes every 0.05s to show current positions
- When a racer reaches the end, they win and the entire strip displays their color
- Winner determined by random probability over time

**Visual Effect**:
Three dots of color (red, green, blue) race from start to finish. The winner's color floods the entire strip as a celebration.

**Customizable**:
- Racer probabilities can be adjusted in code
- Update speed: 0.1s per move attempt
- Display refresh: 0.05s

---

## Clock Effects (Work on Both Strips)

All clock effects display the current time in America/New_York timezone using different visualization styles.

**Color Coding (All Clocks)**:
- **Hours**: Red (AM) or Blue (PM)
- **Minutes**: Green
- **Seconds**: Purple
- **Markers**: Yellow (where applicable)

---

### ⏰ Clock 1 - Sectioned Layout
**Function**: `clock(strip, strip_id)`
**File**: `clock_effects.py:19`

**Description**:
Divides the strip into three distinct sections for hours, minutes, and seconds with spacing between them.

**How It Works**:
- **Section 1** (LEDs 6-17): Hours (0-11, one LED per hour in 12-hour format)
- **Section 2** (LEDs 20-79): Minutes (0-59, one LED per minute)
- **Section 3** (LEDs 82-111): Seconds (divided by 2, so 0-29 LEDs represent 0-58 seconds)
- 2 LED gap between each section
- Updates every second

**LED Layout**:
```
[6-17: Hours] [gap] [20-79: Minutes] [gap] [82-111: Seconds]
```

**Best For**: Clear separation of time components

---

### ⏰ Clock 2 - Full Strip Overlay
**Function**: `clock2(strip, strip_id)`
**File**: `clock_effects.py:72`

**Description**:
Uses the entire strip length with hours shown as a bar, minutes and seconds as position markers.

**How It Works**:
- **Hours**: Block of 10 LEDs per hour (LEDs 0-119, marking position `hour * 10`)
- **Minutes**: 2-LED marker at position `minute * 2`
- **Seconds**: 2-LED marker at position `second * 2`
- All three elements overlay on the same strip
- Updates every second

**LED Mapping**:
- 12 hours × 10 LEDs = 120 LEDs (perfect for 120 LED strip)
- 60 minutes × 2 LEDs = 120 LEDs
- 60 seconds × 2 LEDs = 120 LEDs

**Best For**: Compact time display using full strip capacity

---

### ⏰ Clock 3 - Filled Progress
**Function**: `clock3(strip, strip_id)`
**File**: `clock_effects.py:114`

**Description**:
Extension of Clock 2 that fills sections instead of just marking positions, creating a progress bar effect.

**How It Works**:
- **Hours**: Fills from start to hour position (`hour * 10`)
- **Minutes**: If ahead of hours, fills from hour position to minute position
- **Seconds**: If ahead of minutes, fills from minute position to second position
- Creates cascading fill effect showing time progression
- Updates every second

**Visual Effect**:
Like three progress bars (hours, minutes, seconds) filling up from the start, each extending beyond the previous one.

**Best For**: Visualizing time as progress through the day

---

### ⏰ Clock 4 - Marker Style
**Function**: `clock4(strip, strip_id)`
**File**: `clock_effects.py:175`

**Description**:
Uses small markers/dots at intervals to represent time, similar to a traditional clock face.

**How It Works**:
- **Hour markers**: One LED every 10 positions showing completed hours
- **Minute markers**: Dots at 10-minute intervals plus dots for remaining minutes
- **Seconds**: 2-LED marker at current second position
- Creates a sparse, minimalist display
- Calculates markers dynamically based on current time

**Visual Effect**:
Looks like tick marks on a clock face - evenly spaced markers for hours and minutes with a distinct second hand.

**Best For**: Minimalist time display with less light pollution

---

### ⏰ Clock 5 - Rollout Animation
**Function**: `clock5(strip, strip_id)`
**File**: `clock_effects.py:227`

**Description**:
Animated clock where the second indicator rolls out like a wave each second.

**How It Works**:
- Fills strip from start to current second position
- Then animates a rollout effect that clears from end to start
- Timing calculated so rollout completes in exactly 1 second
- Formula: `time.sleep(1 / second)` ensures consistent timing
- Creates dramatic animated transition each second

**Visual Effect**:
Each second, a wave of light expands to the second position, then rolls back like a wave receding.

**Best For**: Dynamic, animated time display

---

### ⏰ Clock 6 - Async Rollout with Markers
**Function**: `clock6(strip, strip_id)` (async)
**File**: `clock_effects.py:266`

**Description**:
Most sophisticated clock using async programming for smooth rollout animation with permanent hour markers.

**How It Works**:
- **Hour markers**: Yellow LEDs every 5 minutes (12 positions around strip)
- **Hour indicator**: Single LED at hour position
- **Minute indicator**: Single LED at minute position
- **Seconds**: Smooth rollout animation that fills from 0 to current second
- Uses async/await for non-blocking smooth animation
- Calculates delay to complete second rollout in exactly 1 second
- After rollout completes, clears for next second

**Visual Effect**:
Like a modern digital watch - permanent markers for orientation, with a smooth filling animation showing seconds progress.

**Best For**:
- Strips with 240 LEDs (higher resolution for smoother animation)
- Most visually impressive clock display

---

## Matrix-Specific Effects (Strip 2 Only)

The following effects are implemented in `matrix_effects.py` and only work on Strip 2 (240 LEDs arranged as 4 rows × 60 columns in a serpentine layout).

**Matrix Configuration:**
- Width: 60 columns
- Height: 4 rows
- Total LEDs: 240
- Layout: Serpentine (alternating row directions)

---

### 📜 Text Scroller
**Function**: `text_scroller(strip, text="HELLO", color=None, strip_id="strip2")`
**File**: `matrix_effects.py:145`

**Description**:
Scrolls custom text messages across the matrix display from right to left.

**How It Works**:
- Uses a 5x3 bitmap font with characters A-Z, space, and punctuation
- Converts text into a pixel buffer of columns
- Scrolls the buffer across the matrix width
- Vertically centers the text on the 4-row display
- Wraps around: text reappears from the right after scrolling off left edge

**Visual Effect**:
Like an LED marquee sign - text flows smoothly across the display continuously.

**Parameters**:
- `text`: String to display (default: "HELLO")
- `color`: LED color (default: GREEN)

**Best For**: Messages, notifications, information display

---

### 🌀 Spiral Pattern
**Function**: `spiral_pattern(strip, strip_id="strip2")`
**File**: `matrix_effects.py:206`

**Description**:
Draws an expanding and contracting spiral that radiates from the center of the matrix.

**How It Works**:
- Calculates spiral path using polar coordinates (angle and radius)
- Starts at center point (30, 2)
- Each pixel colored based on its distance from center
- Uses `colors.wheel()` for rainbow gradient along spiral
- Animates by increasing radius over time

**Visual Effect**:
A colorful spiral that grows outward from the center like a galaxy or whirlpool.

**Best For**: Mesmerizing ambient display, screensaver effect

---

### ⬛ Checkerboard Pattern
**Function**: `checkerboard_pattern(strip, strip_id="strip2")`
**File**: `matrix_effects.py:236`

**Description**:
Animated checkerboard pattern that alternates between two states.

**How It Works**:
- Divides matrix into alternating squares using modulo math: `(x + y + phase) % 2`
- Each square gets a color from the color wheel based on its x position
- Phase toggles between 0 and 1, flipping the pattern
- Updates every 0.1 seconds

**Visual Effect**:
Like a racing flag that flips its pattern, creating a pulsing checkerboard effect with rainbow colors.

**Best For**: Testing matrix layout, visual rhythm effect

---

### 🌊 Wave Pattern
**Function**: `wave_pattern(strip, strip_id="strip2")`
**File**: `matrix_effects.py:257`

**Description**:
Sine wave that flows horizontally across the matrix.

**How It Works**:
- Calculates wave height for each column using: `MATRIX_HEIGHT / 2 + (MATRIX_HEIGHT / 3) * sin((x + offset) * 0.5)`
- Draws 3 rows of pixels around the wave height for thickness
- Uses `colors.warm_wheel()` for gradient coloring
- Offset increases each frame to create flowing motion

**Visual Effect**:
A smooth, flowing wave that undulates across the display like ocean waves or audio waveforms.

**Best For**: Calming ambient effect, audio visualization aesthetic

---

### ⭕ Expanding Circles
**Function**: `expanding_circles(strip, strip_id="strip2")`
**File**: `matrix_effects.py:281`

**Description**:
Concentric circles that expand outward from the center like ripples in water.

**How It Works**:
- Centers at (30, 2)
- Draws multiple circles at different radii using Midpoint Circle Algorithm
- Each circle colored differently using color wheel
- Radius increases each frame, creating expanding effect
- Resets when circles reach edge

**Visual Effect**:
Ripples expanding from center like a stone dropped in water or radar pulse effect.

**Best For**: Attention-grabbing display, sonar/radar aesthetic

---

### 🏀 Bouncing Ball
**Function**: `bouncing_ball(strip, strip_id="strip2")`
**File**: `matrix_effects.py:309`

**Description**:
A ball bounces around the matrix with physics-like motion, leaving a fading trail.

**How It Works**:
- Ball starts at center (30, 2) with velocity (1, 1)
- Position updated each frame: `x += vx`, `y += vy`
- Bounces off edges by reversing velocity: `vx = -vx` or `vy = -vy`
- Ball color changes randomly on each bounce
- Draws 4-pixel trail behind ball with fading colors

**Visual Effect**:
A glowing ball bouncing around like DVD screensaver, leaving colorful trails.

**Best For**: Dynamic movement display, screensaver

---

### 🧬 Game of Life
**Function**: `game_of_life(strip, strip_id="strip2")`
**File**: `matrix_effects.py:350`

**Description**:
Implementation of Conway's Game of Life cellular automaton.

**How It Works**:
- Grid initialized with random alive/dead cells
- Each generation, cells evolve based on neighbors:
  - Alive cell with 2-3 neighbors survives
  - Dead cell with exactly 3 neighbors becomes alive
  - All other cells die
- Color shifts with each generation for visual interest
- Automatically resets if grid becomes empty or static (after 100 generations)

**Visual Effect**:
Organic patterns emerge, evolve, and die - sometimes stable structures, sometimes chaotic.

**Best For**: Mesmerizing mathematical art, demonstrating emergence

---

### 🐍 Snake Game
**Function**: `snake_game(strip, strip_id="strip2")`
**File**: `matrix_effects.py:402`

**Description**:
Auto-playing snake animation where the snake chases food.

**How It Works**:
- Snake starts at center as single pixel
- Food spawns at random location (red pixel)
- AI moves snake toward food 70% of time, random 30%
- Snake grows when eating food, maintains length otherwise
- Wraps around edges (no walls)
- Snake body colored with green gradient

**Visual Effect**:
A growing, slithering snake chasing food around the display.

**Best For**: Game aesthetic, autonomous animation

---

### 🧱 Tetris Blocks
**Function**: `tetris_blocks(strip, strip_id="strip2")`
**File**: `matrix_effects.py:453`

**Description**:
Falling tetris-style blocks with all 7 classic shapes.

**How It Works**:
- Randomly selects one of 7 tetromino shapes (I, O, T, S, Z, L, J)
- Spawns at random x position at top
- Falls downward one row at a time
- Each block has random color from preset list
- No collision detection - blocks fall through each other

**Visual Effect**:
Colorful tetris blocks continuously falling like gentle rain or building blocks.

**Best For**: Retro game aesthetic, continuous motion

---

### 📊 Bar Graph
**Function**: `bar_graph(strip, strip_id="strip2")`
**File**: `matrix_effects.py:498`

**Description**:
Animated bar chart with bars that grow and shrink dynamically.

**How It Works**:
- Creates 10 vertical bars across the width
- Each bar has current height and target height
- Heights gradually move toward targets (±1 per frame)
- When target reached, new random target chosen
- Bars colored with gradient based on height

**Visual Effect**:
Like a dancing equalizer or animated statistics chart with bars moving up and down.

**Best For**: Data visualization aesthetic, rhythm display

---

### 🎵 Spectrum Analyzer
**Function**: `spectrum_analyzer(strip, strip_id="strip2")`
**File**: `matrix_effects.py:531`

**Description**:
Simulated audio spectrum analyzer with frequency bands.

**How It Works**:
- Divides width into 60 frequency bands (one per column)
- Lower frequencies (left side) have higher amplitude
- Randomizes amplitude each frame to simulate audio input
- Each band drawn from bottom up with warm color gradient
- Updates rapidly (0.05s) for dynamic effect

**Visual Effect**:
Like an audio equalizer or spectrum analyzer on a stereo system.

**Best For**: Music visualization aesthetic, party mode

---

### 🔥 Heat Map
**Function**: `heat_map(strip, strip_id="strip2")`
**File**: `matrix_effects.py:557`

**Description**:
Animated heat map visualization with diffusing hot spots.

**How It Works**:
- Randomly spawns heat sources (30% chance per frame)
- Heat diffuses to neighboring pixels (averaging algorithm)
- Heat gradually cools (95% retention per frame)
- Color coded: Blue (cold) → Yellow → Orange → Red (hot)
- Continuous cycle of heating and cooling

**Visual Effect**:
Like thermal imaging camera or weather heat map with flowing, diffusing hot spots.

**Best For**: Ambient effect, temperature/intensity visualization

---

### 🏁 4-Lane Matrix Race
**Function**: `matrix_race(strip, strip_id="strip2")`
**File**: `matrix_effects.py:612`

**Description**:
Matrix racing game where 4 racers compete in separate lanes (one per row).

**How It Works**:
- Four racers (Red, Green, Blue, Yellow) each start at position 0 in their own lane (row)
- Each racer has a 50% probability of advancing one position per frame
- Racers leave colorful fading trails behind them (3 pixels long)
- First racer to reach the end (column 59) wins
- Winner's lane flashes 5 times, then entire matrix fills with winner's color

**Visual Effect**:
Like a horizontal horse race or drag race with 4 lanes. Racers move independently across the matrix, leaving rainbow trails. Dramatic winner celebration.

**Best For**: Entertainment, competitive display, gaming aesthetic

**Comparison with Linear Race**:
- **Strip 1 race** (`light_race.py`): 3 racers (red, green, blue) competing in the same line, all visible at same position
- **Strip 2 matrix race** (`matrix_effects.py`): 4 racers in separate lanes, can see who's ahead at any moment

---

---

## Effect Parameters

### Common Parameters (All Effects)

**controller.delay**
- Controls animation speed
- Value in seconds (converted from milliseconds in settings)
- Smaller = faster, larger = slower
- Default: 0.5 seconds (500ms)

**controller.color_list**
- Array of 3 colors used by effects
- Configurable per strip in settings
- Format: `[primary, secondary, tertiary]`
- Default: `[RED, GREEN, BLUE]`

**controller.numPixels / controller.num_pixels**
- Number of LEDs on the strip
- Strip 1: 120
- Strip 2: 240
- Used to calculate boundaries and positions

---

## Implementation Notes

### Stop Flag System
All effects check `get_stop_flag(strip_id)` in their loops to allow graceful stopping without cutting off mid-animation.

### Thread Safety
Each strip has independent:
- Stop flags
- Thread management
- Settings (colors, delays)
- Effect execution

This allows running different effects simultaneously on both strips.

### Async vs Sync Effects
- Most effects: Synchronous (use `time.sleep()`)
- Clock 6 and Race: Asynchronous (use `await asyncio.sleep()`)
- Async effects detected and handled automatically by `effect_runner()`

---

## Adding New Effects

### Standard Effects (Linear Strip)

To create a new linear effect for Strip 1 or Strip 2:

1. Add function to `effects.py` or `clock_effects.py`
2. Accept `controller` parameter
3. Include stop flag checks: `while not get_stop_flag(strip_id):`
4. Access strip properties: `controller.numPixels`, `controller.delay`, `controller.color_list`
5. Update LEDs: `controller.set_pixel(index, color)` then `controller.show()`
6. Add to `get_jobs()` function in `async-app.py`

Example:
```python
def my_effect(controller):
    strip_id = getattr(controller, 'strip_id', 'strip1')
    while not get_stop_flag(strip_id):
        # Your effect logic here
        controller.set_pixel(0, colors.RED)
        controller.show()
        time.sleep(controller.delay)
```

### Matrix Effects (Strip 2 Only)

To create a new matrix effect:

1. Add function to `matrix_effects.py`
2. Accept `strip` parameter (raw PixelStrip object, not controller)
3. Include stop flag checks: `while not get_stop_flag(strip_id):`
4. Use helper functions: `set_pixel_xy(strip, x, y, color)`, `clear_matrix(strip)`
5. Use matrix dimensions: `MATRIX_WIDTH = 60`, `MATRIX_HEIGHT = 4`
6. Add to `get_jobs()` function in `async-app.py` within the `strip_id == "strip2"` block

Example:
```python
def my_matrix_effect(strip, strip_id="strip2"):
    while not get_stop_flag(strip_id):
        clear_matrix(strip)
        # Draw something at x=30, y=2
        set_pixel_xy(strip, 30, 2, colors.RED)
        strip.show()
        time.sleep(0.05)
```

---

## Color System

Colors defined in `colors.py` using `rpi_ws281x.Color(r, g, b)` format:

### Static Colors
- `OFF`: (0, 0, 0)
- `RED`: (255, 0, 0)
- `GREEN`: (0, 255, 0)
- `BLUE`: (0, 0, 255)
- `YELLOW`: (150, 100, 0)
- `ORANGE`: (200, 20, 0)
- `PURPLE`: (255, 0, 255)
- `WHITE`: (255, 255, 255)
- `LIME_GREEN`: (50, 205, 50)

### Dynamic Color Functions
- `wheel(pos)`: Rainbow colors 0-255
- `warm_wheel(pos)`: Warm colors (red/orange/yellow) 0-255
- `red_hue(r)`: Red gradient 0-255
- `blue_hue(b)`: Blue gradient 0-255
- `green_hue(g)`: Green gradient 0-255

---

## Performance Considerations

### Strip 1 (120 LEDs)
- Faster updates
- Lower memory usage
- Suitable for rapid animations

### Strip 2 (240 LEDs)
- Double the LEDs = double the processing time
- Better for high-resolution displays (clocks, patterns)
- May need slightly longer delays for smooth animations

### Optimization Tips
- Minimize `show()` calls (update all LEDs, then show once)
- Use delays appropriately (too fast causes flickering)
- Clear only necessary LEDs (don't redraw unchanged pixels)
