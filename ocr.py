"""
OCR Processing Module using Gemini Vision API
Extracts payment details from screenshots using Google Gemini
"""

import os
import json
import re
import random
import time
from typing import Dict, Optional
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gemini API configuration
# Load multiple API keys for rotation/fallback
GEMINI_API_KEYS = []
# Check potential keys GEMINI_API_KEY, GEMINI_API_KEY_2, ... GEMINI_API_KEY_5
possible_vars = ['GEMINI_API_KEY'] + [f'GEMINI_API_KEY_{i}' for i in range(2, 6)]

for var in possible_vars:
    key = os.getenv(var)
    if key and key.strip():
        GEMINI_API_KEYS.append(key.strip())

if not GEMINI_API_KEYS:
    # Use the hardcoded key as last resort/fallback if env vars are missing during dev
    default_key = 'AIzaSyAL9Qxf4u6afJ0lLiM9-JK6mTeAJ4TtYwk'
    if default_key:
         GEMINI_API_KEYS.append(default_key)
    else:
        raise ValueError("No GEMINI_API_KEYS found in environment variables")
    
GEMINI_MODEL = "gemini-2.0-flash-exp"


def get_mime_type(image_path: str) -> str:
    """Get MIME type based on file extension"""
    ext = image_path.lower().split('.')[-1]
    mime_types = {
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'png': 'image/png',
        'gif': 'image/gif',
        'webp': 'image/webp'
    }
    return mime_types.get(ext, 'image/jpeg')


def process_payment_screenshot(image_path: str) -> Dict:
    """
    Process payment screenshot using Gemini Vision API
    Returns extracted amount, UTR, sender with confidence
    """
    # Read image once
    try:
        with open(image_path, 'rb') as f:
            image_bytes = f.read()
            
        mime_type = get_mime_type(image_path)
    except Exception as e:
         return {
            'success': False,
            'error': f'Failed to read image: {str(e)}',
            'confidence': 0.0
        }

    # Prompt
    prompt = """Analyze this Indian UPI payment screenshot (GPay, PhonePe, Paytm, etc.) and extract:

1. **Amount**: The payment amount in Indian Rupees (just the number, e.g., 10, 49, 99)
2. **UTR/Transaction ID**: The 12-digit UPI transaction ID
3. **Sender Name**: The name of the person who sent the payment

Return ONLY valid JSON in this exact format (no markdown, no explanation):
{"amount": <number or null>, "utr": "<12-digit string or null>", "sender": "<string or null>", "confidence": <0.0 to 1.0>}"""

    last_error = None
    
    # Try up to 3 times with random keys
    for attempt in range(3):
        try:
            # Pick a random key
            api_key = random.choice(GEMINI_API_KEYS)
            client = genai.Client(api_key=api_key)
            
            # Generate response
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    ),
                    prompt
                ]
            )
            
            # Get response text
            text_response = response.text.strip()
            
            # Clean up the response (remove markdown code blocks if present)
            if text_response.startswith('```'):
                text_response = re.sub(r'^```(?:json)?\n?', '', text_response)
                text_response = re.sub(r'\n?```$', '', text_response)
            
            # Parse JSON
            try:
                data = json.loads(text_response)
                
                # Validate and clean data
                amount = data.get('amount')
                utr = data.get('utr')
                sender = data.get('sender')
                confidence = data.get('confidence', 0.8)
                
                # Ensure amount is a number
                if amount is not None:
                    try:
                        amount = float(str(amount).replace(',', '').replace('₹', '').replace('Rs', '').strip())
                    except:
                        amount = None
                
                # Clean UTR (should be 12 digits)
                if utr:
                    utr = re.sub(r'[^0-9]', '', str(utr))
                    if len(utr) != 12:
                        utr = None
                
                # Determine if needs review
                needs_review = confidence < 0.7 or amount is None or utr is None
                
                return {
                    'success': True,
                    'amount': amount,
                    'utr': utr,
                    'sender': sender,
                    'confidence': confidence,
                    'needs_review': needs_review,
                    'raw_text': text_response[:500]
                }
                
            except json.JSONDecodeError:
                 # If parsing failed, maybe retry?
                 last_error = f"Failed to parse response: {text_response[:200]}"
                 continue

        except Exception as e:
            error_str = str(e)
            last_error = error_str
            # Check for overload/rate limit errors
            if "503" in error_str or "429" in error_str or "overloaded" in error_str.lower():
                # specific server busy error - wait a 1.5 second and retry with different key
                time.sleep(1.5)
                continue
            else:
                # Other error (auth, etc) - continue just in case
                continue

    # If loop finished without returning
    return {
        'success': False,
        'error': f'Gemini processing error (after retries): {last_error}',
        'confidence': 0.0
    }


if __name__ == '__main__':
    # Test with a sample image
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        image_path = "image.jpeg"
    
    print(f"Processing: {image_path}\n")
    result = process_payment_screenshot(image_path)
    
    print("="*50)
    print("GEMINI VISION EXTRACTION RESULT")
    print("="*50)
    
    if result['success']:
        print(f"✅ Success!")
        print(f"💰 Amount: ₹{result['amount']}")
        print(f"🔢 UTR: {result['utr']}")
        print(f"👤 Sender: {result['sender']}")
        print(f"📊 Confidence: {result['confidence']:.0%}")
        print(f"🔍 Needs Review: {result.get('needs_review', False)}")
    else:
        print(f"❌ Error: {result['error']}")
