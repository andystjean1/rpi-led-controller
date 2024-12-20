# led_strip_controller.py
from rpi_ws281x import Color, PixelStrip
import colors
import effects

# LED strip configuration
LED_COUNT = 120
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 5
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

class LEDStripController:    
    def __init__(self):
        # Initialize the LED strip
        strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        strip.begin()
        self.strip = strip
        self.numPixels = strip.numPixels()
        self.color_list = [colors.RED, colors.GREEN, colors.BLUE]
        self.delay = 500 / 1000 #milliseconds

    def set_colors(self, color_list):
        self.color_list = color_list
    
    def get_colors(self):
        return self.color_list
    
    def set_delay(self, delay):
        self.delay = delay / 1000
    
    def get_delay(self):
        return self.delay * 1000

    def off(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, colors.OFF)
        self.strip.show()

    def set_pixel(self, index, color):
        if 0 <= index < self.strip.numPixels():
            self.strip.setPixelColor(index, color)

    def show(self):
        self.strip.show()

    def fill_color(self, color):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, color)
        self.strip.show()

    def set_multiple_pixels(self, indices, color):
        for index in indices:
            if 0 <= index < self.strip.numPixels():
                self.strip.setPixelColor(index, color)
        self.strip.show()
    
    def flash(self):
        print("starting flash")
        effects.flash(self)