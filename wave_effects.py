import time
import math
import random
from rpi_ws281x import Color
import colors

stop_flag = False

def set_stop_flag(value: bool):
    global stop_flag
    stop_flag = value

class WaveConfig:
    """Configuration class for wave effects"""
    def __init__(self):
        self.speed = 0.1  # Wave speed (0.01 - 1.0)
        self.amplitude = 1.0  # Wave amplitude (0.1 - 2.0)
        self.frequency = 1.0  # Wave frequency (0.1 - 5.0)
        self.phase_shift = 0  # Phase shift in radians
        self.wave_length = 20  # Length of one wave cycle in pixels
        self.color_shift = False  # Whether to shift colors along the wave
        self.brightness_modulation = True  # Whether to modulate brightness
        self.color_palette = [colors.RED, colors.GREEN, colors.BLUE]  # Color palette for the wave
        self.wave_type = 'sine'  # 'sine', 'triangle', 'square', 'sawtooth', 'pulse'
        self.direction = 1  # 1 for forward, -1 for backward
        self.fade_edges = True  # Whether to fade at strip edges

def interpolate_color(color1, color2, ratio):
    """Interpolate between two colors based on ratio (0-1)"""
    r1, g1, b1 = (color1 >> 16) & 0xFF, (color1 >> 8) & 0xFF, color1 & 0xFF
    r2, g2, b2 = (color2 >> 16) & 0xFF, (color2 >> 8) & 0xFF, color2 & 0xFF
    
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)
    
    return Color(r, g, b)

def generate_wave_value(position, time_offset, config):
    """Generate wave value based on position and time"""
    # Calculate the wave position
    wave_pos = (position / config.wave_length * 2 * math.pi * config.frequency) + (time_offset * config.speed * config.direction) + config.phase_shift
    
    if config.wave_type == 'sine':
        return math.sin(wave_pos) * config.amplitude
    elif config.wave_type == 'triangle':
        return (2 / math.pi) * math.asin(math.sin(wave_pos)) * config.amplitude
    elif config.wave_type == 'square':
        return config.amplitude if math.sin(wave_pos) >= 0 else -config.amplitude
    elif config.wave_type == 'sawtooth':
        return 2 * (wave_pos / (2 * math.pi) - math.floor(wave_pos / (2 * math.pi) + 0.5)) * config.amplitude
    elif config.wave_type == 'pulse':
        pulse_width = 0.3  # 30% duty cycle
        return config.amplitude if (wave_pos % (2 * math.pi)) < (2 * math.pi * pulse_width) else -config.amplitude
    else:
        return math.sin(wave_pos) * config.amplitude

def sine_wave(controller, config=None):
    """Classic sine wave effect"""
    if config is None:
        config = WaveConfig()
        config.wave_type = 'sine'
        config.color_palette = [colors.BLUE, colors.PURPLE, colors.RED]
    
    time_offset = 0
    num_pixels = controller.numPixels
    
    while not stop_flag:
        for i in range(num_pixels):
            if stop_flag:
                break
            
            # Generate wave value (-1 to 1)
            wave_value = generate_wave_value(i, time_offset, config)
            
            # Convert to brightness (0 to 1)
            if config.brightness_modulation:
                brightness = (wave_value + 1) / 2  # Map -1,1 to 0,1
            else:
                brightness = 1.0
            
            # Select color from palette
            if config.color_shift:
                color_index = (i + int(time_offset * 10)) % len(config.color_palette)
            else:
                color_index = int((wave_value + 1) / 2 * len(config.color_palette))
                color_index = max(0, min(len(config.color_palette) - 1, color_index))
            
            base_color = config.color_palette[color_index]
            
            # Apply brightness modulation
            if config.brightness_modulation:
                r = int(((base_color >> 16) & 0xFF) * brightness)
                g = int(((base_color >> 8) & 0xFF) * brightness)
                b = int((base_color & 0xFF) * brightness)
                final_color = Color(r, g, b)
            else:
                final_color = base_color
            
            # Apply edge fading
            if config.fade_edges:
                edge_fade = min(i / 10.0, (num_pixels - i) / 10.0, 1.0)
                r = int(((final_color >> 16) & 0xFF) * edge_fade)
                g = int(((final_color >> 8) & 0xFF) * edge_fade)
                b = int((final_color & 0xFF) * edge_fade)
                final_color = Color(r, g, b)
            
            controller.set_pixel(i, final_color)
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def triangle_wave(controller):
    """Triangle wave effect"""
    config = WaveConfig()
    config.wave_type = 'triangle'
    config.color_palette = [colors.GREEN, colors.YELLOW, colors.ORANGE]
    config.wave_length = 15
    sine_wave(controller, config)

def pulse_wave(controller):
    """Pulse wave effect"""
    config = WaveConfig()
    config.wave_type = 'pulse'
    config.color_palette = [colors.RED, colors.WHITE]
    config.wave_length = 10
    config.speed = 0.2
    sine_wave(controller, config)

def rainbow_wave(controller):
    """Rainbow wave effect using color wheel"""
    time_offset = 0
    num_pixels = controller.numPixels
    
    while not stop_flag:
        for i in range(num_pixels):
            if stop_flag:
                break
            
            # Create a sine wave for brightness
            wave_value = math.sin((i / 10.0) + (time_offset * 0.1)) * 0.5 + 0.5
            
            # Create rainbow colors
            hue = (i * 256 // num_pixels + time_offset * 2) % 256
            base_color = colors.wheel(hue)
            
            # Apply wave brightness
            r = int(((base_color >> 16) & 0xFF) * wave_value)
            g = int(((base_color >> 8) & 0xFF) * wave_value)
            b = int((base_color & 0xFF) * wave_value)
            
            controller.set_pixel(i, Color(r, g, b))
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def dual_wave(controller):
    """Two interfering waves"""
    time_offset = 0
    num_pixels = controller.numPixels
    
    while not stop_flag:
        for i in range(num_pixels):
            if stop_flag:
                break
            
            # Two waves with different frequencies
            wave1 = math.sin((i / 8.0) + (time_offset * 0.1)) * 0.5
            wave2 = math.sin((i / 12.0) + (time_offset * 0.15)) * 0.5
            
            # Combine waves
            combined = wave1 + wave2
            brightness = (combined + 1) / 2  # Normalize to 0-1
            
            # Choose color based on wave interference
            if combined > 0.5:
                base_color = colors.BLUE
            elif combined > 0:
                base_color = colors.PURPLE
            elif combined > -0.5:
                base_color = colors.RED
            else:
                base_color = colors.ORANGE
            
            # Apply brightness
            r = int(((base_color >> 16) & 0xFF) * brightness)
            g = int(((base_color >> 8) & 0xFF) * brightness)
            b = int((base_color & 0xFF) * brightness)
            
            controller.set_pixel(i, Color(r, g, b))
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def ocean_wave(controller):
    """Ocean-like wave effect"""
    time_offset = 0
    num_pixels = controller.numPixels
    
    # Ocean color palette
    ocean_colors = [
        Color(0, 50, 100),    # Deep blue
        Color(0, 100, 150),   # Medium blue
        Color(0, 150, 200),   # Light blue
        Color(50, 200, 255),  # Cyan
        Color(100, 255, 255), # Light cyan
        Color(200, 255, 255)  # White foam
    ]
    
    while not stop_flag:
        for i in range(num_pixels):
            if stop_flag:
                break
            
            # Multiple wave components for realistic ocean effect
            wave1 = math.sin((i / 15.0) + (time_offset * 0.08)) * 0.3
            wave2 = math.sin((i / 8.0) + (time_offset * 0.12)) * 0.2
            wave3 = math.sin((i / 25.0) + (time_offset * 0.05)) * 0.1
            
            combined = wave1 + wave2 + wave3
            
            # Map to ocean colors
            color_index = int((combined + 0.6) / 1.2 * len(ocean_colors))
            color_index = max(0, min(len(ocean_colors) - 1, color_index))
            
            controller.set_pixel(i, ocean_colors[color_index])
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def fire_wave(controller):
    """Fire-like wave effect"""
    time_offset = 0
    num_pixels = controller.numPixels
    
    while not stop_flag:
        for i in range(num_pixels):
            if stop_flag:
                break
            
            # Create flickering fire effect
            base_wave = math.sin((i / 6.0) + (time_offset * 0.2)) * 0.5 + 0.5
            flicker = random.random() * 0.3 + 0.7  # Random flicker
            
            intensity = base_wave * flicker
            
            # Fire colors based on intensity
            if intensity > 0.8:
                color = Color(255, 255, 100)  # White-yellow
            elif intensity > 0.6:
                color = Color(255, 200, 0)    # Yellow
            elif intensity > 0.4:
                color = Color(255, 100, 0)    # Orange
            elif intensity > 0.2:
                color = Color(200, 0, 0)      # Red
            else:
                color = Color(50, 0, 0)       # Dark red
            
            # Apply intensity modulation
            r = int(((color >> 16) & 0xFF) * intensity)
            g = int(((color >> 8) & 0xFF) * intensity)
            b = int((color & 0xFF) * intensity)
            
            controller.set_pixel(i, Color(r, g, b))
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def breathing_wave(controller):
    """Breathing/pulsing wave effect"""
    time_offset = 0
    num_pixels = controller.numPixels
    
    while not stop_flag:
        # Global breathing effect
        global_breath = math.sin(time_offset * 0.05) * 0.5 + 0.5
        
        for i in range(num_pixels):
            if stop_flag:
                break
            
            # Local wave effect
            local_wave = math.sin((i / 20.0) + (time_offset * 0.1)) * 0.3 + 0.7
            
            # Combine global and local effects
            combined = global_breath * local_wave
            
            # Color progression
            hue = (i * 2 + time_offset) % 256
            base_color = colors.wheel(hue)
            
            # Apply combined brightness
            r = int(((base_color >> 16) & 0xFF) * combined)
            g = int(((base_color >> 8) & 0xFF) * combined)
            b = int((base_color & 0xFF) * combined)
            
            controller.set_pixel(i, Color(r, g, b))
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def lightning_wave(controller):
    """Lightning-like wave effect"""
    time_offset = 0
    num_pixels = controller.numPixels
    
    while not stop_flag:
        # Random lightning strikes
        if random.random() < 0.1:  # 10% chance of lightning
            # Flash the entire strip
            for i in range(num_pixels):
                controller.set_pixel(i, colors.WHITE)
            controller.show()
            time.sleep(0.05)
            
            # Fade out quickly
            for fade in range(5):
                brightness = (5 - fade) / 5.0
                for i in range(num_pixels):
                    color = Color(int(255 * brightness), int(255 * brightness), int(255 * brightness))
                    controller.set_pixel(i, color)
                controller.show()
                time.sleep(0.02)
        else:
            # Normal stormy background
            for i in range(num_pixels):
                if stop_flag:
                    break
                
                # Dark stormy colors with subtle movement
                wave_value = math.sin((i / 30.0) + (time_offset * 0.03)) * 0.3 + 0.3
                
                # Storm colors
                r = int(20 * wave_value)
                g = int(20 * wave_value)
                b = int(60 * wave_value)
                
                controller.set_pixel(i, Color(r, g, b))
        
        controller.show()
        time.sleep(controller.delay)
        time_offset += 1

def custom_wave(controller, wave_config):
    """Custom wave with user-defined configuration"""
    sine_wave(controller, wave_config)