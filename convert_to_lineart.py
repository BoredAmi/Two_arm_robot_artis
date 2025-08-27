import base64
import requests
from openai import OpenAI
from PIL import Image
import tempfile
import os

client = OpenAI(api_key="***REMOVED-OPENAI-KEY***")

# Predefined prompts for different styles
PROMPTS = {
    "minimalist": """
        Create a minimalist line art portrait in black and white. Use clean, continuous outlines with no shading or color. Depict all key facial features in detail, including eyes, eyebrows, nose, lips, and hair, with clear and expressive lines. Emphasize the structure and expression of the face, but avoid sketchiness or extra hatching. The background should be plain white. The style should be simple, modern, and suitable for robotic drawing, similar to a detailed coloring book.
    """,
    "caricature": """
        Create a humorous caricature portrait in black and white line art. Exaggerate facial features in a playful, cartoon-like manner with oversized distinctive features. Use clean, bold outlines with no shading, emphasizing the subject's most recognizable characteristics in an amusing but respectful way. Plain white background.
    """
}

def convert_to_lineart(face_image_path, prompt_type="minimalist"):
    """Convert a face image to line art using OpenAI's image editing capabilities."""
    try:
        # Get the appropriate prompt
        if prompt_type in PROMPTS:
            prompt = PROMPTS[prompt_type]
        else:
            prompt = PROMPTS["minimalist"]  # Default fallback
        # Convert image to PNG if needed (OpenAI API works better with PNG)
        
        # Open and convert image to ensure it's in a compatible format
        with Image.open(face_image_path) as img:
            # Convert to RGB if necessary
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Create temporary PNG file if the input isn't PNG
            temp_png_path = None
            if not face_image_path.lower().endswith('.png'):
                temp_png_path = os.path.join(tempfile.gettempdir(), "temp_input.png")
                img.save(temp_png_path, 'PNG')
                input_path = temp_png_path
            else:
                input_path = face_image_path

        # Use the processed input image path
        with open(input_path, "rb") as image_file:
            result = client.images.edit(
                model="gpt-image-1",  # Use gpt-image-1 as requested
                image=image_file,
                prompt=prompt,
                quality="medium",  # Use medium quality as requested
                n=1
            )

        # Handle response based on format (URL or base64)
        if hasattr(result.data[0], 'url') and result.data[0].url:
            # Download from URL
            image_url = result.data[0].url
            response = requests.get(image_url)
            response.raise_for_status()
            image_data = response.content
        elif hasattr(result.data[0], 'b64_json') and result.data[0].b64_json:
            # Decode base64
            image_data = base64.b64decode(result.data[0].b64_json)
        else:
            raise Exception("No image data received from API")
        
        # Save the image to a file
        output_path = os.path.join(os.getcwd(), "out.png")
        with open(output_path, "wb") as f:
            f.write(image_data)
            
        # Clean up temporary file if created
        if temp_png_path and os.path.exists(temp_png_path):
            os.remove(temp_png_path)
            
        print(f"Line art successfully generated and saved as {output_path}")
            
    except Exception as e:
        print(f"Error in convert_to_lineart: {e}")
        raise e