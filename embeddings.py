from openai import OpenAI
from rpi_ws281x import PixelStrip, Color
import numpy as np
from colorsys import hsv_to_rgb
import os
from dotenv import load_dotenv
load_dotenv()

# OpenAI API Key (replace with your key)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def get_embeddings(text):
    """Generate embeddings for the input text using OpenAI."""
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    print(response)
    return response.data[0].embedding


def normalize_embeddings(embeddings, count):
    """Normalize embeddings and map to RGB colors for the LED strip."""
    embeddings = np.array(embeddings[:count * 3])  # Truncate to match LED count * 3 (RGB)
    normalized = ((embeddings - embeddings.min()) / (embeddings.max() - embeddings.min())) * 255
    return normalized.astype(int)


def display_text_as_lights(strip, text):
    """Display text embeddings on the LED strip."""
    embeddings = get_embeddings(text)  # Generate embeddings
    colors = normalize_dynamic_embeddings(embeddings, strip.numPixels()-1)  # Normalize to RGB values

    # Map colors to the LED strip
    for i in range(strip.numPixels() -1):
        r, g, b = colors[i * 3:i * 3 + 3]
        strip.setPixelColor(i, Color(r, g, b))
    strip.show()


## various embedding functions
def normalize_dynamic_embeddings(embeddings, count):
    """Normalize embeddings and map to RGB colors for the LED strip."""
    embeddings = np.array(embeddings[:count * 3])  # Truncate to match LED count * 3 (RGB)
    normalized = ((embeddings - embeddings.min()) / (embeddings.max() - embeddings.min())) * 1024
    normalized = normalized % 255  # Wrap values into RGB range
    return normalized.astype(int)



def normalize_color_transform_embeddings(embeddings, count):
    """Apply sinusoidal transformation for more color variety."""
    embeddings = np.array(embeddings[:count * 3])  # Truncate to match LED count * 3 (RGB)
    normalized = np.sin(embeddings)  # Apply sine transformation
    normalized = ((normalized - normalized.min()) / (normalized.max() - normalized.min())) * 255
    return normalized.astype(int)

def normalize_embeddings_with_noise(embeddings, count):
    """Normalize embeddings with added noise for more color variety."""
    embeddings = np.array(embeddings[:count * 3])  # Truncate to match LED count * 3 (RGB)
    noise = np.random.uniform(-0.1, 0.1, embeddings.shape)  # Add small noise
    embeddings += noise
    normalized = ((embeddings - embeddings.min()) / (embeddings.max() - embeddings.min())) * 255
    return normalized.astype(int)

def normalize_embeddings_hsv(embeddings, count):
    """Normalize embeddings and map to HSV for better color variety."""
    embeddings = np.array(embeddings[:count])  # Truncate to match LED count
    normalized = (embeddings - embeddings.min()) / (embeddings.max() - embeddings.min())  # Normalize to [0, 1]
    
    colors = []
    for value in normalized:
        hue = value  # Use the embedding value as hue (0 to 1)
        r, g, b = hsv_to_rgb(hue, 1.0, 1.0)  # Full saturation and brightness
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    
    return colors