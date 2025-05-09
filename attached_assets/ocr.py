import sys
import platform # For more detailed OS checking if needed, though sys.platform is usually sufficient

# --- Platform Check for Vision Framework ---
IS_DARWIN = sys.platform == "darwin"

# Attempt to import macOS-specific Vision and Quartz frameworks only on Darwin
if IS_DARWIN:
    try:
        import objc  # PyObjC bridge, ensure it's installed
        from objc import NULL, autorelease_pool # For memory management in PyObjC
        
        # Vision Framework for OCR
        from Vision import VNRecognizeTextRequest, VNImageRequestHandler
        
        # Quartz CoreGraphics for image handling (CGImage)
        from Quartz.CoreGraphics import (
            CGDataProviderCreateWithCFData,
            CGImageCreate,
            CGColorSpaceCreateDeviceRGB,
            kCGImageAlphaPremultipliedLast, # Or kCGImageAlphaNoneSkipLast if alpha isn't needed
            kCGRenderingIntentDefault,
            # Potentially other constants if image formats vary
        )
        import numpy as np # For converting PIL to CGImage data buffer
        from PIL import Image # For image manipulation and type checking
        
        # Check macOS version for Vision availability (VNRecognizeTextRequest needs macOS 10.15+)
        # This is a bit more advanced but good for robustness.
        # mac_ver = platform.mac_ver()
        # if mac_ver and float(mac_ver[0].split('.')[0] + '.' + mac_ver[0].split('.')[1]) < 10.15:
        #     raise ImportError("VNRecognizeTextRequest requires macOS 10.15 Catalina or newer.")

    except ImportError as e:
        missing_module = e.name if hasattr(e, 'name') else "a PyObjC framework"
        # Provide a more user-friendly error message
        error_message = (
            f"Failed to import macOS-specific Vision/Quartz frameworks (PyObjC). "
            f"Missing module: '{missing_module}'. "
            f"Ensure 'pyobjc-framework-Vision', 'pyobjc-framework-Quartz', and 'pyobjc-framework-Cocoa' "
            f"are installed. This module is required for OCR on macOS. Original error: {e}"
        )
        # Instead of raising immediately, we can set a flag or make functions no-op
        # For Eidon, OCR is critical, so raising an error might be appropriate if on macOS.
        # However, to allow the rest of the app to potentially load (e.g. for viewing existing data),
        # we can define a stub and log an error.
        # For this iteration, let's keep the original behavior of raising an ImportError if critical components are missing on macOS.
        raise ImportError(error_message) from e
    except Exception as e: # Catch other potential objc/framework loading issues
        raise RuntimeError(f"An unexpected error occurred while importing macOS frameworks for OCR: {e}")


# --- Helper Function: PIL Image to CGImage (macOS only) ---
if IS_DARWIN:
    def _pil_to_cgimage(pil_img: Image.Image):
        """
        Convert a PIL.Image object to a CGImageRef suitable for Apple Vision framework.
        """
        # Ensure image is in a suitable format for CGImage (e.g., RGBA or RGB)
        # Vision framework generally works well with RGBA.
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        
        width, height = pil_img.size
        # Get image data as bytes
        img_data_bytes = pil_img.tobytes() # "raw", pil_img.mode would give "RGBA"

        # Create a CGDataProvider from the image data
        # CGDataProviderCreateWithCFData expects CFDataRef, which can be Python bytes directly.
        data_provider = CGDataProviderCreateWithCFData(img_data_bytes)
        if not data_provider:
            raise RuntimeError("Failed to create CGDataProvider from PIL image data.")

        # Create a CGColorSpace (DeviceRGB is common)
        color_space = CGColorSpaceCreateDeviceRGB()
        if not color_space:
            raise RuntimeError("Failed to create CGColorSpaceCreateDeviceRGB.")

        # Define CGImage parameters
        bits_per_component = 8
        bits_per_pixel = 32  # 4 components (RGBA) * 8 bits
        bytes_per_row = 4 * width # For RGBA: 4 bytes per pixel * width

        # Create the CGImage
        # kCGImageAlphaPremultipliedLast means alpha is the last component, and RGB values are premultiplied by alpha.
        # If your image is not premultiplied, kCGImageAlphaLast might be more appropriate,
        # or ensure conversion handles premultiplication. PIL's "RGBA" is typically not premultiplied.
        # For simplicity and common cases, kCGImageAlphaPremultipliedLast often works.
        # If text recognition is poor, experimenting with alpha modes (e.g. kCGImageAlphaNoneSkipLast if alpha is irrelevant) might help.
        cg_image = CGImageCreate(
            width, height,
            bits_per_component,
            bits_per_pixel,
            bytes_per_row,
            color_space,
            kCGImageAlphaPremultipliedLast, # BitmapInfo: Alpha info and byte order
            data_provider,
            None,  # Decode array (usually None)
            False, # shouldInterpolate (usually False for direct data)
            kCGRenderingIntentDefault # Rendering intent
        )

        if not cg_image:
            raise RuntimeError("Failed to create CGImage from PIL image.")
            
        return cg_image


# --- Main OCR Function ---
def extract_text_from_image(image_input) -> str:
    """
    Performs OCR on an image to extract text.

    On macOS, uses Apple's Vision framework.
    On other platforms, this function will raise a NotImplementedError.

    Args:
        image_input: Can be a PIL.Image.Image object or a NumPy array (will be converted to PIL Image).

    Returns:
        A string containing the extracted text, with lines separated by newlines.
        Returns an empty string if no text is found or an error occurs during OCR.
    """
    if not IS_DARWIN:
        # print("Warning: OCR is only supported on macOS with Apple Vision. No text will be extracted.")
        # raise NotImplementedError("OCR is only supported on macOS with Apple Vision.")
        return "" # Return empty string for non-macOS to allow app to function without OCR

    # Ensure objc and Vision components are loaded (already checked at module level, but good practice)
    if not all([objc, VNRecognizeTextRequest, VNImageRequestHandler, _pil_to_cgimage]):
        print("Error: macOS Vision components not available for OCR.")
        return ""

    try:
        # Convert input to PIL Image if it's a NumPy array
        if isinstance(image_input, np.ndarray):
            # Ensure the NumPy array is in a format PIL can understand (e.g., uint8)
            if image_input.dtype != np.uint8:
                # Attempt to convert if it's a float type (e.g. 0-1 range)
                if np.issubdtype(image_input.dtype, np.floating) and image_input.max() <= 1.0:
                    image_input = (image_input * 255).astype(np.uint8)
                else: # Otherwise, try a direct conversion if possible, or raise error
                    try:
                        image_input = image_input.astype(np.uint8)
                    except ValueError:
                         raise TypeError("Unsupported NumPy array dtype for image conversion. Expected uint8 or float (0-1).")
            pil_image = Image.fromarray(image_input)
        elif isinstance(image_input, Image.Image):
            pil_image = image_input
        else:
            raise TypeError(
                "Invalid input type for OCR. Expected PIL.Image.Image or NumPy array, "
                f"got {type(image_input).__name__}."
            )

        # Convert PIL Image to CGImage
        cg_image = _pil_to_cgimage(pil_image)

        # Create a Vision text recognition request
        # The completion handler is not strictly needed for synchronous execution but often set to None.
        request = VNRecognizeTextRequest.alloc().initWithCompletionHandler_(None)
        # You can set recognitionLevel to .accurate or .fast
        # request.setRecognitionLevel_(VNRecognizeTextRequest.VNRequestTextRecognitionLevelAccurate)
        # You can also set customWords if needed, or specify languages
        # request.setRecognitionLanguages_(['en-US'])


        # Create an image request handler with the CGImage
        # The options dictionary can be used to specify orientation if known (e.g., from EXIF)
        handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
        
        extracted_lines = []
        # Perform the request(s) within an autorelease pool for memory management
        with autorelease_pool():
            success, error = handler.performRequests_error_([request], None)

            if not success or error:
                error_str = error.localizedDescription() if error else "Unknown error"
                print(f"Error performing Vision text recognition request: {error_str}")
                return ""

            observations = request.results()
            if observations:
                for observation in observations:
                    # Each observation is a VNRecognizedTextObservation
                    # Get the top candidate (most likely recognition)
                    # topCandidates_ takes an integer for the max number of candidates to return
                    top_candidate = observation.topCandidates_(1)
                    if top_candidate and len(top_candidate) > 0:
                        extracted_lines.append(top_candidate[0].string())
            
        return "\n".join(extracted_lines)

    except Exception as e:
        # Log the error or handle it more gracefully
        print(f"An error occurred during OCR: {e}")
        # Potentially log traceback for debugging:
        # import traceback
        # print(traceback.format_exc())
        return "" # Return empty string on error

# --- Example Usage (for testing if run directly) ---
if __name__ == "__main__":
    if IS_DARWIN:
        print("Running ocr.py directly for testing (macOS)...")
        try:
            # Create a simple dummy image with text using PIL for testing
            # This requires Pillow to be installed.
            from PIL import Image, ImageDraw, ImageFont
            
            img_width, img_height = 400, 100
            test_image = Image.new("RGB", (img_width, img_height), color="white")
            draw = ImageDraw.Draw(test_image)
            try:
                # Try to load a common system font.
                font = ImageFont.truetype("Arial.ttf", 30)
            except IOError:
                # Fallback to default font if Arial isn't found
                font = ImageFont.load_default()
                print("Arial.ttf not found, using default PIL font for test image.")

            text_to_draw = "Hello Eidon OCR\nTest 123 !"
            
            # Get text bounding box to center it (simplified)
            # For Pillow 9.2.0+ textbbox; for older, textsize
            if hasattr(draw, 'textbbox'):
                bbox = draw.textbbox((0,0), text_to_draw, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else: # Fallback for older Pillow
                text_width, text_height = draw.textsize(text_to_draw, font=font)

            x = (img_width - text_width) / 2
            y = (img_height - text_height) / 2
            draw.text((x, y), text_to_draw, fill="black", font=font)
            
            # test_image.show() # Optionally show the image
            
            formatted_text_to_draw = text_to_draw.replace('\n', ' ')
            print(f"Attempting OCR on generated test image with text: '{formatted_text_to_draw}'")
            extracted = extract_text_from_image(test_image)
            print("--- Extracted Text ---")
            print(extracted)
            print("----------------------")

            # Test with a NumPy array
            np_image = np.array(test_image)
            print("\nAttempting OCR on NumPy array version of the test image...")
            extracted_np = extract_text_from_image(np_image)
            print("--- Extracted Text (from NumPy) ---")
            print(extracted_np)
            print("---------------------------------")

        except ImportError:
            print("Pillow is not installed. Skipping direct image generation test for OCR.")
        except Exception as e:
            print(f"Error during OCR self-test: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("OCR module loaded on non-macOS. `extract_text_from_image` will return empty string.")
        print(f"Test: extract_text_from_image(None) -> '{extract_text_from_image(None)}'")