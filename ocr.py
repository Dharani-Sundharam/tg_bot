"""
OCR Processing Module using Gemini Vision API & Groq Llama Vision
Extracts payment details from screenshots using Google Gemini with Groq fallback
"""

import os
import json
import re
import random
import time
import base64
from typing import Dict, Optional, List
from google import genai
from google.genai import types
from groq import Groq
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

# Switch to gemini-1.5-flash for better free-tier reliability/limits
GEMINI_MODEL = "gemini-1.5-flash"

# Groq Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"


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


def encode_image(image_path: str) -> str:
    """Encode image to base64 string"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def clean_json_response(text_response: str) -> Dict:
    """Common JSON cleaning and parsing logic"""
    # Clean up the response (remove markdown code blocks if present)
    if text_response.startswith('```'):
        text_response = re.sub(r'^```(?:json)?\n?', '', text_response)
        text_response = re.sub(r'\n?```$', '', text_response)
    
    # Parse JSON
    try:
        data = json.loads(text_response)
        return data
    except json.JSONDecodeError:
        # Try to extract JSON from response
        json_match = re.search(r'\{[^{}]*\}', text_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise


def normalize_result(data: Dict, confidence: float = 0.8) -> Dict:
    """Normalize extracted data into standard format"""
    amount = data.get('amount')
    utr = data.get('utr')
    sender = data.get('sender')
    
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
        'needs_review': needs_review
    }


def process_with_groq(image_path: str) -> Dict:
    """Process image using Groq Llama 3.2 Vision"""
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
        
    try:
        base64_image = encode_image(image_path)
        client = Groq(api_key=GROQ_API_KEY)
        
        prompt = """Analyze this Indian UPI payment screenshot and extract these details in JSON format:
1. amount (number)
2. utr (12-digit transaction ID string)
3. sender (name string)

Return ONLY valid JSON: {"amount": 100, "utr": "123456789012", "sender": "Name"}"""

        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        text_response = completion.choices[0].message.content
        data = clean_json_response(text_response)
        return normalize_result(data, confidence=0.85) # Groq is usually quite confident
        
    except Exception as e:
        raise Exception(f"Groq processing failed: {str(e)}")


def process_payment_screenshot(image_path: str) -> Dict:
    """
    Process payment screenshot using Gemini Vision API with Groq fallback
    Returns extracted amount, UTR, sender with confidence
    """
    # Read image content
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
    
    # 1. Try Gemini (Primary) - Iterate keys
    keys_to_try = GEMINI_API_KEYS.copy()
    random.shuffle(keys_to_try)
    
    for api_key in keys_to_try:
        try:
            client = genai.Client(api_key=api_key)
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
            data = clean_json_response(response.text.strip())
            return normalize_result(data, confidence=data.get('confidence', 0.8))

        except Exception as e:
            error_str = str(e)
            last_error = error_str
            # Only retry for overload/quota errors
            if any(x in error_str for x in ["503", "429", "overloaded", "RESOURCE_EXHAUSTED"]):
                continue # Try next key
            else:
                # If it's a content safety/other error, continue but log it?
                continue

    # 2. Key Exhaustion / Fallback -> Try Groq
    if GROQ_API_KEY:
        try:
            print("Gemini keys exhausted/failed. Falling back to Groq Llama 3.2...")
            return process_with_groq(image_path)
        except Exception as e:
            last_error = f"{last_error} | Groq Error: {str(e)}"

    # If all failed
    return {
        'success': False,
        'error': f'All OCR providers failed: {last_error}',
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
    print("OCR EXTRACTION RESULT")
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
