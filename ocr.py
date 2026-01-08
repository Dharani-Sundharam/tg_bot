"""
OCR Processing Module for Payment Screenshots
Optimized for GPay, PhonePe, Paytm screenshots
Extracts: Amount, UTR/Transaction ID, Sender Name
"""

import re
import cv2
import numpy as np
from PIL import Image
import pytesseract
from typing import Dict, Optional

# Configure Tesseract path (Windows) - Uncomment if needed
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Enhanced regex patterns for Indian payment apps
PATTERNS = {
    'amount': [
        r'₹\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # ₹10 or ₹1,000.00
        r'Rs\.?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Rs.10 or Rs 1000
        r'INR\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # INR 10
        r'Amount[:\s]+₹?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',  # Amount: ₹10
    ],
    'utr': [
        # GPay/PhonePe UPI transaction ID (12 digits)
        r'UPI\s+transaction\s+ID[:\s]*(\d{12})',
        r'transaction\s+ID[:\s]*(\d{12})',
        # Generic UTR patterns
        r'(?:UPI Ref no|UTR|Reference)[:\s]*([A-Z0-9]{9,20})',
        r'Ref\.?\s*[Nn]o\.?\s*[:\s]*([A-Z0-9]{9,20})',
        r'Transaction\s+ID[:\s]*([A-Z0-9]{9,20})',
        # Just 12-digit numbers (common in GPay)
        r'(\d{12})',
    ],
    'sender': [
        # GPay format: "From: NAME (Bank)"
        r'From[:\s]+([A-Z\s]+?)\s*\(',
        r'Paid\s+by[:\s]+([A-Z\s]+?)\s*\(',
        # Generic patterns
        r'from\s+([A-Za-z\s]+?)(?=\s*[-@]|\s*UPI|\s*\()',
        r'Sender[:\s]+([A-Za-z\s]+?)(?=\s*[-@]|\s*\()',
    ],
    'recipient': [
        # GPay format: "To NAME"
        r'To\s+([A-Z\s]+?)(?:\n|$)',
        r'Paid\s+to[:\s]+([A-Z\s]+?)(?:\n|$)',
    ]
}


def preprocess_image(image_path: str) -> np.ndarray:
    """
    Preprocess image for better OCR accuracy
    Optimized for dark-themed payment apps (GPay, PhonePe)
    """
    # Read image
    img = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Invert colors (dark background -> white background)
    inverted = cv2.bitwise_not(gray)
    
    # Increase contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    enhanced = clahe.apply(inverted)
    
    # Apply thresholding
    _, thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(thresh, None, 10, 7, 21)
    
    return denoised


def extract_text_from_image(image_path: str) -> str:
    """Extract text from image using Tesseract OCR"""
    try:
        # Preprocess image
        processed_img = preprocess_image(image_path)
        
        # Convert to PIL Image
        pil_img = Image.fromarray(processed_img)
        
        # Try multiple OCR configurations
        configs = [
            r'--oem 3 --psm 6',  # Assume uniform block of text
            r'--oem 3 --psm 4',  # Assume single column
            r'--oem 3 --psm 3',  # Fully automatic
        ]
        
        best_text = ""
        for config in configs:
            text = pytesseract.image_to_string(pil_img, lang='eng', config=config)
            if len(text) > len(best_text):
                best_text = text
        
        return best_text
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""


def extract_amount(text: str) -> Optional[float]:
    """Extract payment amount from text"""
    # First try standard patterns with ₹ symbol
    for pattern in PATTERNS['amount']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                if 1 <= amount <= 100000:
                    return amount
            except ValueError:
                continue
    
    # GPay specific: Look for standalone number before "Pay again" or after phone number
    gpay_patterns = [
        r'\+91\s+\d+\s+\d+\s*\n+\s*(\d+(?:\.\d{2})?)\s*\n',  # After phone number
        r'(\d+(?:\.\d{2})?)\s*\n+\s*@?\s*(?:Pay again|Completed)',  # Before "Pay again"
    ]
    
    for pattern in gpay_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            amount_str = match.group(1).replace(',', '')
            try:
                amount = float(amount_str)
                if 1 <= amount <= 100000:
                    return amount
            except ValueError:
                continue
    
    return None


def extract_utr(text: str) -> Optional[str]:
    """Extract UTR/Transaction ID from text"""
    for pattern in PATTERNS['utr']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            utr = match.group(1).strip()
            # Validate UTR length
            if 9 <= len(utr) <= 20:
                return utr
    return None


def extract_sender(text: str) -> Optional[str]:
    """Extract sender name from text"""
    for pattern in PATTERNS['sender']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            sender = match.group(1).strip()
            # Clean up sender name
            sender = re.sub(r'\s+', ' ', sender)
            # Validate length
            if 2 <= len(sender) <= 50:
                return sender.title()
    return None


def extract_recipient(text: str) -> Optional[str]:
    """Extract recipient name from text (optional)"""
    for pattern in PATTERNS['recipient']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            recipient = match.group(1).strip()
            recipient = re.sub(r'\s+', ' ', recipient)
            if 2 <= len(recipient) <= 50:
                return recipient.title()
    return None


def calculate_confidence(amount: Optional[float], utr: Optional[str], sender: Optional[str]) -> float:
    """
    Calculate confidence score based on extracted data
    Returns: 0.0 to 1.0
    """
    score = 0.0
    
    if amount is not None:
        score += 0.5  # Amount is most important
    if utr is not None:
        score += 0.4  # UTR is critical
    if sender is not None:
        score += 0.1  # Sender is nice to have
    
    return score


def process_payment_screenshot(image_path: str) -> Dict:
    """
    Main function to process payment screenshot
    Returns dict with extracted data and confidence score
    """
    # Extract text from image
    text = extract_text_from_image(image_path)
    
    if not text:
        return {
            'success': False,
            'error': 'Failed to extract text from image',
            'confidence': 0.0
        }
    
    # Extract payment details
    amount = extract_amount(text)
    utr = extract_utr(text)
    sender = extract_sender(text)
    recipient = extract_recipient(text)
    
    # Calculate confidence
    confidence = calculate_confidence(amount, utr, sender)
    
    # Determine if manual review is needed
    needs_review = confidence < 0.7
    
    return {
        'success': True,
        'amount': amount,
        'utr': utr,
        'sender': sender,
        'recipient': recipient,
        'confidence': confidence,
        'needs_review': needs_review,
        'raw_text': text[:1000]  # First 1000 chars for debugging
    }


if __name__ == '__main__':
    # Test with the sample image
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    else:
        # Default test image
        image_path = "image.jpeg"
    
    print(f"Processing: {image_path}\n")
    result = process_payment_screenshot(image_path)
    
    print("="*50)
    print("OCR EXTRACTION RESULT")
    print("="*50)
    
    if result['success']:
        print(f"✅ Amount: ₹{result.get('amount')}")
        print(f"✅ UTR/Transaction ID: {result.get('utr')}")
        print(f"✅ Sender: {result.get('sender')}")
        print(f"✅ Recipient: {result.get('recipient')}")
        print(f"📊 Confidence: {result.get('confidence'):.0%}")
        print(f"🔍 Needs Review: {result.get('needs_review')}")
        print("\n" + "="*50)
        print("RAW TEXT EXTRACTED:")
        print("="*50)
        print(result.get('raw_text', ''))
    else:
        print(f"❌ Error: {result.get('error')}")
