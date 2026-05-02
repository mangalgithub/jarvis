import base64
import re
from google import genai
from google.genai import types
from app.core.config import settings

class VisionService:
    def __init__(self):
        if settings.google_api_key:
            self.client = genai.Client(api_key=settings.google_api_key)
        else:
            self.client = None

    async def analyze_image(self, base64_image: str, prompt: str):
        if not self.client:
            return "ERROR: GOOGLE_API_KEY is missing."

        try:
            # Detect MIME type and extract pure base64
            mime_match = re.match(r"data:(image/[a-zA-Z]+);base64,", base64_image)
            mime_type = "image/jpeg" 
            
            if mime_match:
                mime_type = mime_match.group(1)
                image_data_str = base64_image.split(",")[1]
            else:
                image_data_str = base64_image

            # Decode base64 string to bytes
            image_bytes = base64.b64decode(image_data_str)

            # Generate content using the new SDK's strict types
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Content(
                        parts=[
                            types.Part.from_text(text=prompt),
                            types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                        ]
                    )
                ]
            )
            
            if response and response.text:
                return response.text
            return "ERROR: AI could not describe the image."
            
        except Exception as e:
            return f"ERROR: {str(e)}"

vision_service = VisionService()
