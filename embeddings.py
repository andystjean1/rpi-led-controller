import openai
from rpi_ws281x import PixelStrip, Color
import numpy as np

# Flask app
app = Flask(__name__)

# OpenAI API Key (replace with your key)
openai.api_key = "your-openai-api-key"


def clear_strip():
    """Turn off all LEDs."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, Color(0, 0, 0))
    strip.show()


def get_embeddings(text):
    """Generate embeddings for the input text using OpenAI."""
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response["data"][0]["embedding"]


def normalize_embeddings(embeddings, count):
    """Normalize embeddings and map to RGB colors for the LED strip."""
    embeddings = np.array(embeddings[:count * 3])  # Truncate to match LED count * 3 (RGB)
    normalized = ((embeddings - embeddings.min()) / (embeddings.max() - embeddings.min())) * 255
    return normalized.astype(int)


def display_text_as_lights(text):
    """Display text embeddings on the LED strip."""
    embeddings = get_embeddings(text)  # Generate embeddings
    colors = normalize_embeddings(embeddings, LED_COUNT)  # Normalize to RGB values

    # Map colors to the LED strip
    for i in range(LED_COUNT):
        r, g, b = colors[i * 3:i * 3 + 3]
        strip.setPixelColor(i, Color(r, g, b))
    strip.show()


@app.route('/text_effect', methods=['POST'])
def text_effect():
    """Endpoint to trigger the text-to-LED effect."""
    data = request.json
    text = data.get("text", "")

    if not text:
        return jsonify({"error": "Text input is required"}), 400

    try:
        display_text_as_lights(text)
        return jsonify({"status": "Effect displayed for text", "text": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


