from rpi_ws281x import Color

OFF = Color(0 , 0, 0)
RED = Color(255, 0, 0)
GREEN = Color(0, 255, 0)
BLUE = Color(0, 0, 255)
YELLOW = Color(150, 100, 0)
ORANGE = Color(200, 20, 0)
PURPLE = Color(255, 0, 255)
WHITE = Color(255, 255, 255)

LIME_GREEN = Color(50,205,50)

# Additional colors for new effects
CYAN = Color(0, 255, 255)
MAGENTA = Color(255, 0, 255)
PINK = Color(255, 192, 203)
GOLD = Color(255, 215, 0)
SILVER = Color(192, 192, 192)
TURQUOISE = Color(64, 224, 208)
CORAL = Color(255, 127, 80)
LAVENDER = Color(230, 230, 250)

# Function to generate colors in a wheel
def wheel(pos):
    """Generate a rainbow color based on position (0-255)."""
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)

def warm_wheel(pos):
    """Generate a warm color (red, orange, yellow) based on position (0-255)."""
    if pos < 85:  # Transition from red to orange
        return Color(255, pos * 3, 0)  # Increasing green for orange
    elif pos < 170:  # Transition from orange to yellow
        pos -= 85
        return Color(255 - pos * 3, 255, 0)  # Decreasing red for yellow
    else:  # Transition from yellow back to red
        pos -= 170
        return Color(pos * 3, 255 - pos * 3, 0)  # Increasing red, decreasing green

def cool_wheel(pos):
    """Generate a cool color (blue, cyan, green) based on position (0-255)."""
    if pos < 85:  # Transition from blue to cyan
        return Color(0, pos * 3, 255)  # Increasing green
    elif pos < 170:  # Transition from cyan to green
        pos -= 85
        return Color(0, 255, 255 - pos * 3)  # Decreasing blue
    else:  # Transition from green back to blue
        pos -= 170
        return Color(0, 255 - pos * 3, pos * 3)  # Decreasing green, increasing blue

def pastel_wheel(pos):
    """Generate pastel colors based on position (0-255)."""
    if pos < 85:
        return Color(128 + pos, 255 - pos, 128)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos, 128, 128 + pos)
    else:
        pos -= 170
        return Color(128, 128 + pos, 255 - pos)

def red_hue(r):
    return Color(r, 0, 0)

def blue_hue(b):
    return Color (0, 0, b)

def green_hue(g):
    return Color (0, g, 0)

def dim_color(color, brightness):
    """Dim a color by a brightness factor (0-255)."""
    r = ((color >> 16) & 0xFF) * brightness // 255
    g = ((color >> 8) & 0xFF) * brightness // 255
    b = (color & 0xFF) * brightness // 255
    return Color(r, g, b)

def blend_colors(color1, color2, factor):
    """Blend two colors together. Factor 0 = color1, factor 1 = color2."""
    r1, g1, b1 = (color1 >> 16) & 0xFF, (color1 >> 8) & 0xFF, color1 & 0xFF
    r2, g2, b2 = (color2 >> 16) & 0xFF, (color2 >> 8) & 0xFF, color2 & 0xFF
    
    r = int(r1 + (r2 - r1) * factor)
    g = int(g1 + (g2 - g1) * factor)
    b = int(b1 + (b2 - b1) * factor)
    
    return Color(r, g, b)