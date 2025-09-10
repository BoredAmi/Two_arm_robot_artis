import base64
import requests
from openai import OpenAI
from PIL import Image
import tempfile
import os
import shutil
from datetime import datetime

client = OpenAI(api_key="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")

# Predefined prompts for different styles
PROMPTS = {
    "minimalist": """
        Convert the input into a minimalist black-and-white line art portrait. Use only solid, continuous black outlines with consistent thickness on a plain white background (remember nothing else than person on a picture). Avoid shading, gradients, textures, or colors. Depict all essential facial features (eyes, eyebrows, nose, lips, hair if visible) with uniform stroke thickness and closed contours. The lines should be smooth, bold, and clean, suitable for binary thresholding and contour extraction. The style should be modern, simple, and precise, like a coloring book illustration or technical outline drawing.
    """,
    "caricature": """
        Create a humorous caricature portrait in black and white line art. Exaggerate facial features in a playful, cartoon-like manner with oversized distinctive features. Use clean, bold outlines with no shading, emphasizing the subject's most recognizable characteristics in an amusing but respectful way. Plain white background.
    """
}

def create_catalog_structure():
    """Create organized directory structure for saving line art conversions"""
    base_dir = "line_art_catalog"
    
    # Create main catalog directory
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
        print(f"Created catalog directory: {base_dir}")
    
    return base_dir

def save_conversion_to_catalog(input_path, output_path, prompt_type, base_dir):
    """
    Save input and output files to organized catalog with timestamp and metadata
    
    Args:
        input_path: Path to original input image
        output_path: Path to generated line art output
        prompt_type: Type of conversion (minimalist, caricature, etc.)
        base_dir: Base catalog directory
        
    Returns:
        Dictionary with saved file paths and metadata
    """
    try:
        # Create timestamp for unique folder naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create conversion-specific directory
        conversion_dir = os.path.join(base_dir, f"{timestamp}_{prompt_type}")
        os.makedirs(conversion_dir, exist_ok=True)
        
        # Generate meaningful filenames
        input_basename = os.path.splitext(os.path.basename(input_path))[0]
        
        # Define target paths
        saved_input_path = os.path.join(conversion_dir, f"input_{input_basename}.png")
        saved_output_path = os.path.join(conversion_dir, f"output_{prompt_type}_lineart.png")
        metadata_path = os.path.join(conversion_dir, "conversion_info.txt")
        
        # Copy input file
        shutil.copy2(input_path, saved_input_path)
        
        # Copy output file
        shutil.copy2(output_path, saved_output_path)
        
        # Create metadata file
        metadata = [
            f"Line Art Conversion - {timestamp}",
            f"==========================================",
            f"Conversion Type: {prompt_type}",
            f"Original Input: {os.path.basename(input_path)}",
            f"Generated Output: output_{prompt_type}_lineart.png",
            f"Conversion Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Input File Size: {os.path.getsize(input_path)} bytes",
            f"Output File Size: {os.path.getsize(output_path)} bytes",
            f"",
            f"Prompt Used:",
            f"------------",
            f"{PROMPTS.get(prompt_type, 'Unknown prompt type')}",
            f"",
            f"Files in this conversion:",
            f"- input_{input_basename}.png (original image)",
            f"- output_{prompt_type}_lineart.png (generated line art)",
            f"- conversion_info.txt (this metadata file)",
        ]
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(metadata))
        
        result = {
            'conversion_dir': conversion_dir,
            'input_saved': saved_input_path,
            'output_saved': saved_output_path,
            'metadata_saved': metadata_path,
            'timestamp': timestamp
        }
        
        print(f"✅ Conversion saved to catalog:")
        print(f"   Directory: {conversion_dir}")
        print(f"   Input: {os.path.basename(saved_input_path)}")
        print(f"   Output: {os.path.basename(saved_output_path)}")
        print(f"   Metadata: {os.path.basename(metadata_path)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error saving to catalog: {e}")
        return None

def view_catalog_summary():
    """Display a summary of all conversions in the catalog"""
    base_dir = "line_art_catalog"
    
    if not os.path.exists(base_dir):
        print("No catalog found. No conversions have been saved yet.")
        return
    
    conversions = []
    total_size = 0
    
    # Scan catalog directory
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            # Parse directory name for info
            parts = item.split('_', 2)  # timestamp_type format
            if len(parts) >= 2:
                timestamp_part = parts[0] + '_' + parts[1]  # YYYYMMDD_HHMMSS
                prompt_type = parts[2] if len(parts) > 2 else "unknown"
                
                # Get metadata if available
                metadata_path = os.path.join(item_path, "conversion_info.txt")
                metadata_info = ""
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Extract date from metadata
                            for line in content.split('\n'):
                                if line.startswith('Conversion Date:'):
                                    metadata_info = line.replace('Conversion Date: ', '')
                                    break
                    except:
                        pass
                
                # Calculate directory size
                dir_size = 0
                for root, dirs, files in os.walk(item_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        if os.path.exists(file_path):
                            dir_size += os.path.getsize(file_path)
                
                total_size += dir_size
                
                conversions.append({
                    'folder': item,
                    'type': prompt_type,
                    'timestamp': timestamp_part,
                    'date': metadata_info,
                    'size': dir_size,
                    'path': item_path
                })
    
    if not conversions:
        print("Catalog directory exists but no conversions found.")
        return
    
    # Sort by timestamp (newest first)
    conversions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    print(f"📁 LINE ART CONVERSION CATALOG")
    print(f"=" * 50)
    print(f"Total conversions: {len(conversions)}")
    print(f"Total catalog size: {total_size / (1024*1024):.1f} MB")
    print(f"Catalog location: {os.path.abspath(base_dir)}")
    print()
    
    print("Recent conversions:")
    print("-" * 50)
    for i, conv in enumerate(conversions[:10]):  # Show last 10
        size_mb = conv['size'] / (1024*1024)
        print(f"{i+1:2d}. {conv['type'].title()} - {conv['date'] or conv['timestamp']}")
        print(f"    📁 {conv['folder']}")
        print(f"    💾 {size_mb:.1f} MB")
        print()
    
    if len(conversions) > 10:
        print(f"... and {len(conversions) - 10} more conversions")
    
    print(f"To view a specific conversion, check: {base_dir}/[folder_name]/")

def generate_image_from_text(text_prompt, style="line_art"):
    """Generate an image from text using OpenAI's image generation capabilities."""
    try:
        # Enhance the prompt to ensure line art style suitable for robot drawing
        enhanced_prompt = f"""
        Create a simple black and white line art drawing of: {text_prompt}
        
        Style requirements:
        - Pure black lines on white background
        - Clean, continuous outlines
        - No shading, gradients, or textures
        - Bold, uniform line thickness
        - Simple geometric shapes where possible
        - Suitable for robot drawing and contour detection
        - Minimalist design like a coloring book illustration
        """
        
        
        result = client.images.generate(
            model="gpt-image-1", 
            prompt=enhanced_prompt,
            quality="high",
            n=1,
            size="1536x1024"
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
        
        print(f"Image successfully generated from text and saved as {output_path}")
        
        # Save to catalog for archival and organization
        catalog_base = create_catalog_structure()
        
        # Create a temporary text file to represent the "input" for catalog purposes
        temp_text_file = os.path.join(tempfile.gettempdir(), "text_prompt.txt")
        with open(temp_text_file, 'w', encoding='utf-8') as f:
            f.write(f"Text Prompt: {text_prompt}\nStyle: {style}")
        
        catalog_result = save_text_generation_to_catalog(
            text_prompt=text_prompt,
            output_path=output_path,
            style=style,
            base_dir=catalog_base
        )
        
        if catalog_result:
            print(f"📁 Generation archived in: {catalog_result['conversion_dir']}")
        
        # Clean up temporary file
        if os.path.exists(temp_text_file):
            os.remove(temp_text_file)
            
        return {
            'output_path': output_path,
            'catalog_info': catalog_result
        }
            
    except Exception as e:
        print(f"Error in generate_image_from_text: {e}")
        raise e

def save_text_generation_to_catalog(text_prompt, output_path, style, base_dir):
    """
    Save text-to-image generation to organized catalog with timestamp and metadata
    
    Args:
        text_prompt: Original text prompt used for generation
        output_path: Path to generated image output
        style: Style of generation (line_art, etc.)
        base_dir: Base catalog directory
        
    Returns:
        Dictionary with saved file paths and metadata
    """
    try:
        # Create timestamp for unique folder naming
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create conversion-specific directory
        conversion_dir = os.path.join(base_dir, f"{timestamp}_text_generated_{style}")
        os.makedirs(conversion_dir, exist_ok=True)
        
        # Define target paths
        saved_output_path = os.path.join(conversion_dir, f"output_text_generated_{style}.png")
        saved_prompt_path = os.path.join(conversion_dir, "text_prompt.txt")
        metadata_path = os.path.join(conversion_dir, "generation_info.txt")
        
        # Copy output file
        shutil.copy2(output_path, saved_output_path)
        
        # Save the text prompt
        with open(saved_prompt_path, 'w', encoding='utf-8') as f:
            f.write(text_prompt)
        
        # Create metadata file
        metadata = [
            f"Text-to-Image Generation - {timestamp}",
            f"==========================================",
            f"Generation Type: text_to_image",
            f"Style: {style}",
            f"Generated Output: output_text_generated_{style}.png",
            f"Generation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Output File Size: {os.path.getsize(output_path)} bytes",
            f"",
            f"Original Text Prompt:",
            f"--------------------",
            f"{text_prompt}",
            f"",
            f"Files in this generation:",
            f"- output_text_generated_{style}.png (generated image)",
            f"- text_prompt.txt (original text prompt)",
            f"- generation_info.txt (this metadata file)",
        ]
        
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(metadata))
        
        result = {
            'conversion_dir': conversion_dir,
            'output_saved': saved_output_path,
            'prompt_saved': saved_prompt_path,
            'metadata_saved': metadata_path,
            'timestamp': timestamp
        }
        
        print(f"✅ Generation saved to catalog:")
        print(f"   Directory: {conversion_dir}")
        print(f"   Output: {os.path.basename(saved_output_path)}")
        print(f"   Prompt: {os.path.basename(saved_prompt_path)}")
        print(f"   Metadata: {os.path.basename(metadata_path)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error saving generation to catalog: {e}")
        return None

def convert_to_lineart(face_image_path, prompt_type="minimalist"):
    """Convert a face image to line art using OpenAI's image editing capabilities."""
    try:
        print(f"Converting image '{face_image_path}' to line art using prompt type '{prompt_type}'")
        # Get the appropriate prompt
        if prompt_type in PROMPTS:
            prompt = PROMPTS[prompt_type]
        else:
            prompt = PROMPTS["minimalist"]  # Default fallback
        
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
                model="gpt-image-1", 
                image=image_file,
                prompt=prompt,
                quality="medium",  
                size="1536x1024"
            )

        # Handle response based on format 
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
        
        print(f"Line art successfully generated and saved as {output_path}")
        
        # Save to catalog for archival and organization
        catalog_base = create_catalog_structure()
        catalog_result = save_conversion_to_catalog(
            input_path=face_image_path,  
            output_path=output_path,
            prompt_type=prompt_type,
            base_dir=catalog_base
        )
        
        if catalog_result:
            print(f"📁 Conversion archived in: {catalog_result['conversion_dir']}")
        
        # Clean up temporary file if created
        if temp_png_path and os.path.exists(temp_png_path):
            os.remove(temp_png_path)
            
        return {
            'output_path': output_path,
            'catalog_info': catalog_result
        }
            
    except Exception as e:
        print(f"Error in convert_to_lineart: {e}")
        raise e