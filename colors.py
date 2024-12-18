
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

def red_hue(r):
    return Color(r, 0, 0)

def blue_hue(b):
    return Color (0, 0, b)

def green_hue(g):
    return Color (0, g, 0)