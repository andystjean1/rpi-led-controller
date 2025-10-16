"""
Matrix effects for 2D LED displays
Designed for Strip 2 (240 LEDs arranged as a matrix)
"""
import time
import math
import random
from datetime import datetime

import colors

# Matrix configuration for 240 LED strip
# Strip 2: 4 rows x 60 columns = 240 LEDs (serpentine layout)
MATRIX_WIDTH = 60
MATRIX_HEIGHT = 4

# Dictionary to track stop flags per strip
stop_flags = {}

def set_stop_flag(value: bool, strip_id="strip2"):
    global stop_flags
    stop_flags[strip_id] = value

def get_stop_flag(strip_id="strip2"):
    return stop_flags.get(strip_id, False)


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def xy_to_index(x, y, width=MATRIX_WIDTH, height=MATRIX_HEIGHT, serpentine=True):
    """
    Convert 2D coordinates to 1D LED strip index.

    Args:
        x: Column (0 to width-1)
        y: Row (0 to height-1)
        width: Matrix width
        height: Matrix height
        serpentine: If True, even rows go left-to-right, odd rows right-to-left

    Returns:
        LED index (0 to width*height-1) or None if out of bounds
    """
    if x < 0 or x >= width or y < 0 or y >= height:
        return None

    if serpentine and y % 2 == 1:
        # Odd rows: reverse direction
        return y * width + (width - 1 - x)
    else:
        # Even rows: normal direction
        return y * width + x


def clear_matrix(strip):
    """Clear all LEDs in the matrix"""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colors.OFF)
    strip.show()


def set_pixel_xy(strip, x, y, color, width=MATRIX_WIDTH, height=MATRIX_HEIGHT):
    """Set a pixel at x,y coordinates"""
    index = xy_to_index(x, y, width, height)
    if index is not None:
        strip.setPixelColor(index, color)


def draw_line(strip, x0, y0, x1, y1, color):
    """Draw a line using Bresenham's algorithm"""
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        set_pixel_xy(strip, x0, y0, color)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy


def draw_circle(strip, cx, cy, radius, color, fill=False):
    """Draw a circle at center (cx, cy) with given radius"""
    if fill:
        for y in range(max(0, cy - radius), min(MATRIX_HEIGHT, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(MATRIX_WIDTH, cx + radius + 1)):
                if (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2:
                    set_pixel_xy(strip, x, y, color)
    else:
        # Midpoint circle algorithm
        x = radius
        y = 0
        err = 0

        while x >= y:
            set_pixel_xy(strip, cx + x, cy + y, color)
            set_pixel_xy(strip, cx + y, cy + x, color)
            set_pixel_xy(strip, cx - y, cy + x, color)
            set_pixel_xy(strip, cx - x, cy + y, color)
            set_pixel_xy(strip, cx - x, cy - y, color)
            set_pixel_xy(strip, cx - y, cy - x, color)
            set_pixel_xy(strip, cx + y, cy - x, color)
            set_pixel_xy(strip, cx + x, cy - y, color)

            if err <= 0:
                y += 1
                err += 2 * y + 1

            if err > 0:
                x -= 1
                err -= 2 * x + 1


# ==============================================================================
# TEXT SCROLLER
# ==============================================================================

# Simple 5x3 font (subset of characters)
FONT_5x3 = {
    'A': [[0,1,1,1,0], [1,0,0,0,1], [1,1,1,1,1], [1,0,0,0,1], [1,0,0,0,1]],
    'B': [[1,1,1,1,0], [1,0,0,0,1], [1,1,1,1,0], [1,0,0,0,1], [1,1,1,1,0]],
    'C': [[0,1,1,1,1], [1,0,0,0,0], [1,0,0,0,0], [1,0,0,0,0], [0,1,1,1,1]],
    'D': [[1,1,1,1,0], [1,0,0,0,1], [1,0,0,0,1], [1,0,0,0,1], [1,1,1,1,0]],
    'E': [[1,1,1,1,1], [1,0,0,0,0], [1,1,1,1,0], [1,0,0,0,0], [1,1,1,1,1]],
    'H': [[1,0,0,0,1], [1,0,0,0,1], [1,1,1,1,1], [1,0,0,0,1], [1,0,0,0,1]],
    'I': [[1,1,1], [0,1,0], [0,1,0], [0,1,0], [1,1,1]],
    'L': [[1,0,0,0,0], [1,0,0,0,0], [1,0,0,0,0], [1,0,0,0,0], [1,1,1,1,1]],
    'O': [[0,1,1,1,0], [1,0,0,0,1], [1,0,0,0,1], [1,0,0,0,1], [0,1,1,1,0]],
    'W': [[1,0,0,0,1], [1,0,0,0,1], [1,0,1,0,1], [1,0,1,0,1], [0,1,0,1,0]],
    ' ': [[0,0,0], [0,0,0], [0,0,0], [0,0,0], [0,0,0]],
    '!': [[1], [1], [1], [0], [1]],
}


def text_scroller(strip, text="HELLO", color=None, strip_id="strip2"):
    """
    Scroll text across the matrix from right to left
    """
    if color is None:
        color = colors.GREEN

    text = text.upper()

    # Build pixel buffer for entire text
    text_buffer = []
    for char in text:
        if char in FONT_5x3:
            char_pixels = FONT_5x3[char]
            text_buffer.append(char_pixels)
            # Add 1 column spacing between characters
            text_buffer.append([[0] * 5])

    # Flatten into columns
    columns = []
    for char_data in text_buffer:
        if char_data:
            char_width = len(char_data[0]) if char_data else 0
            for col_idx in range(char_width):
                col = []
                for row in char_data:
                    if col_idx < len(row):
                        col.append(row[col_idx])
                    else:
                        col.append(0)
                columns.append(col)

    # Scroll the text
    scroll_pos = MATRIX_WIDTH
    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Draw visible portion
        for x in range(MATRIX_WIDTH):
            src_col = scroll_pos + x
            if 0 <= src_col < len(columns):
                col_data = columns[src_col]
                for y, pixel in enumerate(col_data):
                    if pixel and y < MATRIX_HEIGHT:
                        # Center vertically
                        y_pos = (MATRIX_HEIGHT - len(col_data)) // 2 + y
                        if 0 <= y_pos < MATRIX_HEIGHT:
                            set_pixel_xy(strip, x, y_pos, color)

        strip.show()
        time.sleep(0.05)

        scroll_pos -= 1
        if scroll_pos < -len(columns):
            scroll_pos = MATRIX_WIDTH


# ==============================================================================
# MATRIX PATTERNS
# ==============================================================================

def spiral_pattern(strip, strip_id="strip2"):
    """Draw an expanding/contracting spiral pattern"""
    strip_id = strip_id or "strip2"

    while not get_stop_flag(strip_id):
        # Expanding spiral
        for radius in range(1, max(MATRIX_WIDTH, MATRIX_HEIGHT) // 2):
            if get_stop_flag(strip_id):
                break

            clear_matrix(strip)
            cx, cy = MATRIX_WIDTH // 2, MATRIX_HEIGHT // 2

            # Draw spiral
            angle = 0
            for step in range(radius * 20):
                r = (step / 20)
                x = int(cx + r * math.cos(angle))
                y = int(cy + r * math.sin(angle))

                color_val = int(255 * step / (radius * 20))
                color = colors.wheel(color_val)
                set_pixel_xy(strip, x, y, color)

                angle += 0.3

            strip.show()
            time.sleep(0.05)


def checkerboard_pattern(strip, strip_id="strip2"):
    """Animated checkerboard pattern"""
    strip_id = strip_id or "strip2"

    phase = 0
    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                is_checker = ((x + y + phase) % 2 == 0)
                if is_checker:
                    color_val = (x * 255 // MATRIX_WIDTH + phase * 10) % 256
                    color = colors.wheel(color_val)
                    set_pixel_xy(strip, x, y, color)

        strip.show()
        time.sleep(0.1)
        phase = (phase + 1) % 2


def wave_pattern(strip, strip_id="strip2"):
    """Sine wave pattern flowing across the matrix"""
    strip_id = strip_id or "strip2"

    offset = 0
    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        for x in range(MATRIX_WIDTH):
            # Calculate wave height
            wave_y = int(MATRIX_HEIGHT / 2 + (MATRIX_HEIGHT / 3) * math.sin((x + offset) * 0.5))
            wave_y = max(0, min(MATRIX_HEIGHT - 1, wave_y))

            # Draw wave with gradient
            for y in range(max(0, wave_y - 1), min(MATRIX_HEIGHT, wave_y + 2)):
                color_val = (x * 255 // MATRIX_WIDTH + offset * 5) % 256
                color = colors.warm_wheel(color_val)
                set_pixel_xy(strip, x, y, color)

        strip.show()
        time.sleep(0.05)
        offset += 1


def expanding_circles(strip, strip_id="strip2"):
    """Expanding circles from center"""
    strip_id = strip_id or "strip2"

    cx, cy = MATRIX_WIDTH // 2, MATRIX_HEIGHT // 2
    max_radius = max(MATRIX_WIDTH, MATRIX_HEIGHT)

    while not get_stop_flag(strip_id):
        for radius in range(1, max_radius):
            if get_stop_flag(strip_id):
                break

            clear_matrix(strip)

            # Draw multiple circles at different radii
            for r in range(0, radius, 2):
                color_val = (r * 255 // max_radius) % 256
                color = colors.wheel(color_val)
                draw_circle(strip, cx, cy, r, color)

            strip.show()
            time.sleep(0.05)


# ==============================================================================
# 2D ANIMATIONS
# ==============================================================================

def bouncing_ball(strip, strip_id="strip2"):
    """Ball bounces around the matrix"""
    strip_id = strip_id or "strip2"

    # Ball position and velocity
    x, y = MATRIX_WIDTH // 2, MATRIX_HEIGHT // 2
    vx, vy = 1, 1
    color = colors.RED

    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Draw ball
        set_pixel_xy(strip, int(x), int(y), color)

        # Draw trail
        for i in range(1, 4):
            trail_x = int(x - i * vx)
            trail_y = int(y - i * vy)
            if 0 <= trail_x < MATRIX_WIDTH and 0 <= trail_y < MATRIX_HEIGHT:
                # Fading trail
                trail_color = colors.wheel((256 - i * 60) % 256)
                set_pixel_xy(strip, trail_x, trail_y, trail_color)

        strip.show()

        # Update position
        x += vx
        y += vy

        # Bounce off walls
        if x <= 0 or x >= MATRIX_WIDTH - 1:
            vx = -vx
            color = colors.wheel(random.randint(0, 255))
        if y <= 0 or y >= MATRIX_HEIGHT - 1:
            vy = -vy
            color = colors.wheel(random.randint(0, 255))

        time.sleep(0.05)


def game_of_life(strip, strip_id="strip2"):
    """Conway's Game of Life"""
    strip_id = strip_id or "strip2"

    # Initialize random grid
    grid = [[random.choice([0, 1]) for _ in range(MATRIX_WIDTH)] for _ in range(MATRIX_HEIGHT)]

    generation = 0
    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Display current generation
        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                if grid[y][x]:
                    # Color based on generation
                    color_val = (generation * 10) % 256
                    color = colors.wheel(color_val)
                    set_pixel_xy(strip, x, y, color)

        strip.show()
        time.sleep(0.2)

        # Calculate next generation
        new_grid = [[0] * MATRIX_WIDTH for _ in range(MATRIX_HEIGHT)]

        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                # Count neighbors
                neighbors = 0
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = (y + dy) % MATRIX_HEIGHT, (x + dx) % MATRIX_WIDTH
                        neighbors += grid[ny][nx]

                # Apply rules
                if grid[y][x]:
                    new_grid[y][x] = 1 if neighbors in [2, 3] else 0
                else:
                    new_grid[y][x] = 1 if neighbors == 3 else 0

        grid = new_grid
        generation += 1

        # Reset if grid is empty or static
        if generation > 100 or sum(sum(row) for row in grid) < 5:
            grid = [[random.choice([0, 1]) for _ in range(MATRIX_WIDTH)] for _ in range(MATRIX_HEIGHT)]
            generation = 0


def snake_game(strip, strip_id="strip2"):
    """Simple snake animation (auto-play)"""
    strip_id = strip_id or "strip2"

    # Snake starts at center
    snake = [(MATRIX_WIDTH // 2, MATRIX_HEIGHT // 2)]
    direction = (1, 0)  # Moving right
    food = (random.randint(0, MATRIX_WIDTH - 1), random.randint(0, MATRIX_HEIGHT - 1))

    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Draw snake
        for i, (x, y) in enumerate(snake):
            color_val = (i * 255 // max(1, len(snake))) % 256
            color = colors.green_hue(255 - color_val)
            set_pixel_xy(strip, x, y, color)

        # Draw food
        set_pixel_xy(strip, food[0], food[1], colors.RED)

        strip.show()
        time.sleep(0.15)

        # Move snake
        head_x, head_y = snake[0]
        new_head = ((head_x + direction[0]) % MATRIX_WIDTH,
                    (head_y + direction[1]) % MATRIX_HEIGHT)

        snake.insert(0, new_head)

        # Check if ate food
        if new_head == food:
            food = (random.randint(0, MATRIX_WIDTH - 1), random.randint(0, MATRIX_HEIGHT - 1))
        else:
            snake.pop()

        # Simple AI: move toward food
        if random.random() < 0.7:  # 70% of time move toward food
            dx = food[0] - new_head[0]
            dy = food[1] - new_head[1]

            if abs(dx) > abs(dy):
                direction = (1 if dx > 0 else -1, 0)
            else:
                direction = (0, 1 if dy > 0 else -1)
        else:
            # Random turn
            direction = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])


def tetris_blocks(strip, strip_id="strip2"):
    """Falling tetris blocks animation"""
    strip_id = strip_id or "strip2"

    # Tetris shapes
    shapes = [
        [[1, 1, 1, 1]],  # I
        [[1, 1], [1, 1]],  # O
        [[0, 1, 0], [1, 1, 1]],  # T
        [[1, 1, 0], [0, 1, 1]],  # S
        [[0, 1, 1], [1, 1, 0]],  # Z
        [[1, 0, 0], [1, 1, 1]],  # L
        [[0, 0, 1], [1, 1, 1]],  # J
    ]

    colors_list = [colors.BLUE, colors.YELLOW, colors.PURPLE, colors.GREEN,
                   colors.RED, colors.ORANGE, colors.wheel(100)]

    while not get_stop_flag(strip_id):
        # Choose random shape and color
        shape = random.choice(shapes)
        color = random.choice(colors_list)
        x = random.randint(0, MATRIX_WIDTH - len(shape[0]))

        # Fall from top
        for y in range(-len(shape), MATRIX_HEIGHT):
            if get_stop_flag(strip_id):
                break

            clear_matrix(strip)

            # Draw the shape
            for sy, row in enumerate(shape):
                for sx, cell in enumerate(row):
                    if cell and 0 <= y + sy < MATRIX_HEIGHT:
                        set_pixel_xy(strip, x + sx, y + sy, color)

            strip.show()
            time.sleep(0.1)


# ==============================================================================
# VISUALIZATIONS
# ==============================================================================

def bar_graph(strip, strip_id="strip2"):
    """Animated bar graph"""
    strip_id = strip_id or "strip2"

    num_bars = min(10, MATRIX_WIDTH)
    bar_width = MATRIX_WIDTH // num_bars
    bars = [random.randint(1, MATRIX_HEIGHT) for _ in range(num_bars)]
    targets = [random.randint(1, MATRIX_HEIGHT) for _ in range(num_bars)]

    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Update bar heights
        for i in range(num_bars):
            if bars[i] < targets[i]:
                bars[i] += 1
            elif bars[i] > targets[i]:
                bars[i] -= 1
            else:
                targets[i] = random.randint(1, MATRIX_HEIGHT)

        # Draw bars
        for i, height in enumerate(bars):
            for y in range(MATRIX_HEIGHT - height, MATRIX_HEIGHT):
                for x in range(i * bar_width, (i + 1) * bar_width):
                    color_val = (y * 255 // MATRIX_HEIGHT) % 256
                    color = colors.wheel(color_val)
                    set_pixel_xy(strip, x, y, color)

        strip.show()
        time.sleep(0.1)


def spectrum_analyzer(strip, strip_id="strip2"):
    """Simulated audio spectrum analyzer"""
    strip_id = strip_id or "strip2"

    num_bands = MATRIX_WIDTH

    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Simulate frequency bands with random values
        for x in range(num_bands):
            # Simulate audio level (higher for lower frequencies)
            base_level = (num_bands - x) / num_bands
            level = int(MATRIX_HEIGHT * base_level * random.uniform(0.3, 1.0))

            # Draw band
            for y in range(MATRIX_HEIGHT - level, MATRIX_HEIGHT):
                # Color gradient: red at bottom, green at top
                color_val = (y * 255 // MATRIX_HEIGHT) % 256
                color = colors.warm_wheel(color_val)
                set_pixel_xy(strip, x, y, color)

        strip.show()
        time.sleep(0.05)


def heat_map(strip, strip_id="strip2"):
    """Animated heat map visualization"""
    strip_id = strip_id or "strip2"

    # Initialize heat grid
    heat = [[0.0] * MATRIX_WIDTH for _ in range(MATRIX_HEIGHT)]

    while not get_stop_flag(strip_id):
        clear_matrix(strip)

        # Add random heat sources
        if random.random() < 0.3:
            hx, hy = random.randint(0, MATRIX_WIDTH - 1), random.randint(0, MATRIX_HEIGHT - 1)
            heat[hy][hx] = 1.0

        # Display heat map
        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                if heat[y][x] > 0.05:
                    # Color based on heat (blue -> red)
                    if heat[y][x] > 0.7:
                        color = colors.RED
                    elif heat[y][x] > 0.4:
                        color = colors.ORANGE
                    elif heat[y][x] > 0.2:
                        color = colors.YELLOW
                    else:
                        color = colors.BLUE

                    set_pixel_xy(strip, x, y, color)

        strip.show()

        # Diffuse heat
        new_heat = [[0.0] * MATRIX_WIDTH for _ in range(MATRIX_HEIGHT)]
        for y in range(MATRIX_HEIGHT):
            for x in range(MATRIX_WIDTH):
                # Average with neighbors
                total = heat[y][x]
                count = 1
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < MATRIX_HEIGHT and 0 <= nx < MATRIX_WIDTH:
                        total += heat[ny][nx]
                        count += 1
                new_heat[y][x] = (total / count) * 0.95  # Cooling factor

        heat = new_heat
        time.sleep(0.1)


# ==============================================================================
# RACING GAME
# ==============================================================================

def matrix_race(strip, strip_id="strip2"):
    """Matrix racing game where 4 racers compete in separate lanes"""
    strip_id = strip_id or "strip2"

    # Define racers with their properties (one per row/lane)
    racers = [
        {"color": colors.RED, "position": 0, "lane": 0, "probability": 0.5},
        {"color": colors.GREEN, "position": 0, "lane": 1, "probability": 0.5},
        {"color": colors.BLUE, "position": 0, "lane": 2, "probability": 0.5},
        {"color": colors.YELLOW, "position": 0, "lane": 3, "probability": 0.5}
    ]

    winner = None

    while not get_stop_flag(strip_id) and winner is None:
        clear_matrix(strip)

        # Update racer positions
        for racer in racers:
            if random.random() < racer["probability"]:
                racer["position"] += 1

            # Check for winner
            if racer["position"] >= MATRIX_WIDTH - 1:
                winner = racer
                racer["position"] = MATRIX_WIDTH - 1  # Cap at finish line

        # Draw racers
        for racer in racers:
            x = racer["position"]
            y = racer["lane"]
            set_pixel_xy(strip, x, y, racer["color"])

            # Draw trail (3 pixels behind)
            for i in range(1, 4):
                trail_x = x - i
                if trail_x >= 0:
                    # Fading trail
                    trail_color = colors.wheel((256 - i * 60) % 256)
                    set_pixel_xy(strip, trail_x, y, trail_color)

        strip.show()
        time.sleep(0.05)

    # Display winner
    if winner and not get_stop_flag(strip_id):
        # Flash winner's lane
        for _ in range(5):
            if get_stop_flag(strip_id):
                break
            clear_matrix(strip)
            # Fill winner's lane
            for x in range(MATRIX_WIDTH):
                set_pixel_xy(strip, x, winner["lane"], winner["color"])
            strip.show()
            time.sleep(0.2)

            if get_stop_flag(strip_id):
                break
            clear_matrix(strip)
            strip.show()
            time.sleep(0.2)

        # Final display: all lanes with winner's color
        if not get_stop_flag(strip_id):
            for y in range(MATRIX_HEIGHT):
                for x in range(MATRIX_WIDTH):
                    set_pixel_xy(strip, x, y, winner["color"])
            strip.show()
            time.sleep(3)
