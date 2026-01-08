"""
Test OCR extraction without Tesseract
Manually extracts data from the GPay screenshot format
"""

import re

# Sample text that would be extracted from the GPay screenshot
SAMPLE_TEXT = """
To Dharani Sundharam
+91 96262 62425

₹10

Pay again

Completed

8 Jan 2024, 1:40 pm

State Bank of India 1661

UPI transaction ID
600821857735

To: DHARANI SUNDHARAM, G
Google Pay • dharani3318@okaxis

From: DHARSHAN L (State Bank of India)
Google Pay • dharshan12007@okicici

Google transaction ID
CJCAg1joaIPOGA
"""

# Regex patterns
PATTERNS = {
    'amount': [
        r'₹\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
    ],
    'utr': [
        r'UPI\s+transaction\s+ID[:\s]*(\d{12})',
        r'(\d{12})',
    ],
    'sender': [
        r'From[:\s]+([A-Z\s]+?)\s*\(',
    ],
    'recipient': [
        r'To[:\s]+([A-Z\s,\.]+?)(?:\n|Google)',
    ]
}

def extract_amount(text):
    for pattern in PATTERNS['amount']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            amount_str = match.group(1).replace(',', '')
            return float(amount_str)
    return None

def extract_utr(text):
    for pattern in PATTERNS['utr']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None

def extract_sender(text):
    for pattern in PATTERNS['sender']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            sender = match.group(1).strip()
            return re.sub(r'\s+', ' ', sender).title()
    return None

def extract_recipient(text):
    for pattern in PATTERNS['recipient']:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            recipient = match.group(1).strip()
            return re.sub(r'\s+', ' ', recipient).title()
    return None

# Test extraction
print("="*60)
print("TESTING OCR EXTRACTION (Without Tesseract)")
print("="*60)
print("\nSample GPay Screenshot Text:")
print("-"*60)
print(SAMPLE_TEXT)
print("-"*60)

print("\n" + "="*60)
print("EXTRACTED DATA:")
print("="*60)

amount = extract_amount(SAMPLE_TEXT)
utr = extract_utr(SAMPLE_TEXT)
sender = extract_sender(SAMPLE_TEXT)
recipient = extract_recipient(SAMPLE_TEXT)

print(f"💰 Amount: ₹{amount}")
print(f"🔢 UPI Transaction ID: {utr}")
print(f"👤 Sender: {sender}")
print(f"📧 Recipient: {recipient}")

# Calculate confidence
confidence = 0.0
if amount: confidence += 0.5
if utr: confidence += 0.4
if sender: confidence += 0.1

print(f"\n📊 Confidence Score: {confidence:.0%}")
print(f"🔍 Needs Review: {'Yes' if confidence < 0.7 else 'No'}")

print("\n" + "="*60)
print("REGEX PATTERNS USED:")
print("="*60)
print("Amount:", PATTERNS['amount'])
print("UTR:", PATTERNS['utr'])
print("Sender:", PATTERNS['sender'])
print("Recipient:", PATTERNS['recipient'])
