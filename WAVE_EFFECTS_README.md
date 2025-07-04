# 🌊 Wave Effects System

## Overview
The Wave Effects system provides a comprehensive set of customizable wave patterns for your LED strip, simulating various natural and artificial wave phenomena. This system includes both preset effects and a fully customizable wave generator.

## Features

### 🎨 Preset Wave Effects
The system includes 9 carefully crafted preset wave effects:

1. **Sine Wave** - Classic smooth sine wave with blue-to-red gradient
2. **Triangle Wave** - Sharp triangular patterns with green-yellow-orange colors
3. **Pulse Wave** - Digital pulse patterns with red and white colors
4. **Rainbow Wave** - Flowing rainbow colors with sine wave brightness
5. **Ocean Wave** - Realistic ocean simulation with multiple wave frequencies
6. **Fire Wave** - Flickering fire effect with random intensity variations
7. **Breathing Wave** - Gentle breathing effect with rainbow colors
8. **Lightning Wave** - Storm simulation with random lightning flashes
9. **Dual Wave** - Two interfering waves creating complex patterns

### ⚙️ Custom Wave Configuration
Create your own wave patterns with full control over:

#### Wave Parameters
- **Wave Type**: Choose from sine, triangle, square, sawtooth, or pulse waves
- **Speed**: Control wave movement speed (0.01 - 1.0)
- **Amplitude**: Adjust wave intensity (0.1 - 2.0)
- **Frequency**: Set wave frequency (0.1 - 5.0)
- **Wave Length**: Control the length of one wave cycle (5-50 pixels)
- **Phase Shift**: Offset the wave pattern (0-2π radians)
- **Direction**: Forward or backward wave movement

#### Visual Options
- **Color Palette**: Choose up to 4 custom colors for your wave
- **Color Shift**: Enable color cycling along the wave
- **Brightness Modulation**: Toggle brightness variations
- **Fade Edges**: Soft fade at strip edges

## How to Use

### Quick Start (Preset Effects)
1. Navigate to the main LED controller page
2. Click any of the Wave Effects buttons to start a preset
3. Use the "Wave Effects" link for the full control interface

### Custom Wave Creation
1. Go to `/waves` or click "Wave Effects" from the main menu
2. Adjust the parameters in the "Custom Wave Configuration" section
3. Select your preferred colors using the color palette
4. Click "Start Custom Wave" to activate your custom pattern

### API Usage
You can also control wave effects programmatically:

```javascript
// Start a preset wave effect
fetch('/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ effect: 'ocean_wave' })
});

// Create a custom wave configuration
fetch('/wave-config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        wave_type: 'sine',
        speed: 0.15,
        amplitude: 1.2,
        frequency: 1.5,
        wave_length: 25,
        color_palette: ['#FF0000', '#00FF00', '#0000FF', '#FFFFFF'],
        brightness_modulation: true,
        fade_edges: true
    })
});
```

### Available REST Endpoints

- `GET /waves` - Wave effects control interface
- `GET /wave-presets` - Get all available preset configurations
- `POST /wave-config` - Create and start a custom wave configuration
- `POST /start` - Start any wave effect by name
- `POST /stop` - Stop the current effect
- `GET /status` - Check current effect status

## Technical Details

### Wave Types
- **Sine**: Smooth, natural wave pattern
- **Triangle**: Sharp peaks and valleys
- **Square**: Digital on/off pattern
- **Sawtooth**: Ramping pattern
- **Pulse**: Short bursts with configurable duty cycle

### Color System
- Supports hex color codes (#RRGGBB)
- Automatic color interpolation between palette colors
- Rainbow mode for spectrum effects
- Brightness modulation for wave intensity

### Performance
- Optimized for 120 LED strips
- Configurable refresh rates
- Smooth transitions between effects
- Memory-efficient wave generation

## Tips for Best Results

1. **Ocean Effects**: Use blue/cyan colors with low frequency for realistic water
2. **Fire Effects**: Combine red/orange/yellow with high frequency and randomness
3. **Breathing Effects**: Use slow speed with low frequency for calming patterns
4. **Party Mode**: High frequency with rainbow colors and color shifting
5. **Subtle Ambiance**: Low amplitude with single color palette

## Troubleshooting

### Common Issues
- **Effect not starting**: Check that no other effect is running, use `/stop` first
- **Colors not showing**: Verify hex color format (#RRGGBB)
- **Too fast/slow**: Adjust speed parameter (0.01-1.0 range)
- **No brightness variation**: Enable brightness modulation

### Performance Tips
- Lower frequency values for smoother effects
- Use fade_edges for professional appearance
- Adjust wave_length based on your LED strip length
- Combine multiple effects by switching between them

## Examples

### Calm Ocean Scene
```json
{
    "wave_type": "sine",
    "speed": 0.08,
    "amplitude": 0.6,
    "frequency": 0.8,
    "wave_length": 30,
    "color_palette": ["#003264", "#0096FF", "#64FFFF"],
    "brightness_modulation": true,
    "fade_edges": true
}
```

### Energetic Fire
```json
{
    "wave_type": "sine",
    "speed": 0.3,
    "amplitude": 1.5,
    "frequency": 2.0,
    "wave_length": 8,
    "color_palette": ["#FF0000", "#FF6600", "#FFFF00"],
    "brightness_modulation": true,
    "fade_edges": false
}
```

### Gentle Breathing
```json
{
    "wave_type": "sine",
    "speed": 0.05,
    "amplitude": 0.8,
    "frequency": 0.3,
    "wave_length": 60,
    "color_palette": ["#4169E1", "#9370DB", "#FF69B4"],
    "brightness_modulation": true,
    "fade_edges": true
}
```

## Integration with Existing System

The wave effects system seamlessly integrates with your existing LED controller:
- All existing effects remain functional
- Wave effects respect the global stop mechanism
- Compatible with existing color and delay settings
- Works with the same 120 LED strip configuration

Enjoy creating stunning wave patterns with your LED strip! 🌊✨