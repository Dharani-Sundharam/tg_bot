"""
License Key Manager - Compact Version
Generates short encrypted license keys using "Lillian" as the secret
"""

from cryptography.fernet import Fernet
import json
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional
import hashlib

# Generate Fernet key from "Lillian"
def get_fernet_key():
    """Convert 'Lillian' to a valid Fernet key"""
    # Fernet requires 32 bytes, base64 encoded
    key_material = hashlib.sha256(b"Lillian").digest()
    return base64.urlsafe_b64encode(key_material)

FERNET_KEY = get_fernet_key()
cipher = Fernet(FERNET_KEY)


def generate_license_key(amount: float, utr: str, credits: int) -> str:
    """
    Generate compact encrypted license key
    
    Args:
        amount: Payment amount
        utr: UPI transaction ID
        credits: Credits to be awarded
    
    Returns:
        Short encrypted license key (e.g., "CP-ABC123XYZ")
    """
    # Create minimal license data (only essential info)
    # Use time.time() for consistent UNIX timestamp (always UTC)
    import time
    license_data = {
        'u': utr,  # UTR
        'c': credits,  # Credits
        'e': int(time.time() + 300)  # Expiry: current time + 5 minutes (300 seconds)
    }
    
    # Convert to JSON and encrypt
    json_data = json.dumps(license_data, separators=(',', ':'))
    encrypted = cipher.encrypt(json_data.encode())
    
    # Convert to base64
    license_key = base64.urlsafe_b64encode(encrypted).decode()
    
    # Add prefix for branding
    return f"CP-{license_key}"


def decrypt_license_key(license_key: str) -> Optional[Dict]:
    """
    Decrypt and validate license key
    
    Args:
        license_key: Encrypted license key string (with or without CP- prefix)
    
    Returns:
        Dict with license data if valid, None otherwise
    """
    try:
        # Remove CP- prefix if present
        if license_key.startswith('CP-'):
            license_key = license_key[3:]
        
        # Decode from base64
        encrypted = base64.urlsafe_b64decode(license_key.encode())
        
        # Decrypt
        decrypted = cipher.decrypt(encrypted)
        license_data = json.loads(decrypted.decode())
        
        # Check expiry
        expires_at = datetime.fromtimestamp(license_data['e'])
        if datetime.utcnow() > expires_at:
            return {
                'valid': False,
                'error': 'License key expired',
                'data': license_data
            }
        
        return {
            'valid': True,
            'utr': license_data['u'],
            'credits': license_data['c'],
            'expires_at': expires_at.isoformat()
        }
        
    except Exception as e:
        return {
            'valid': False,
            'error': f'Invalid license key: {str(e)}'
        }


def calculate_credits(amount: float) -> int:
    """Calculate credits based on payment amount"""
    if amount >= 99:
        return 13000
    elif amount >= 49:
        return 7000
    elif amount >= 10:
        return 1000
    else:
        return int(amount * 100)


if __name__ == '__main__':
    # Test license key generation
    print("="*60)
    print("COMPACT LICENSE KEY GENERATION TEST")
    print("="*60)
    print(f"Encryption Key: 'Lillian'\n")
    
    # Test data
    amount = 10.0
    utr = "600821859735"
    credits = calculate_credits(amount)
    
    # Generate key
    license_key = generate_license_key(amount, utr, credits)
    
    print(f"💰 Amount: ₹{amount}")
    print(f"🔢 UTR: {utr}")
    print(f"⭐ Credits: {credits}")
    print(f"\n🔑 License Key:")
    print(f"{license_key}")
    print(f"\nKey Length: {len(license_key)} characters")
    
    # Test decryption
    print("\n" + "="*60)
    print("DECRYPTION TEST")
    print("="*60)
    
    result = decrypt_license_key(license_key)
    
    if result['valid']:
        print("✅ License key is VALID")
        print(f"\nDecrypted Data:")
        print(f"  UTR: {result['utr']}")
        print(f"  Credits: {result['credits']}")
        print(f"  Expires: {result['expires_at']}")
    else:
        print(f"❌ License key is INVALID")
        print(f"Error: {result['error']}")
