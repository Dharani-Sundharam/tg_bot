# Installing Tesseract OCR

## Windows

### Option 1: Download Installer (Recommended)
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer
3. Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`
4. Add to PATH or update `ocr.py` line 12

### Option 2: Chocolatey
```powershell
choco install tesseract
```

### Option 3: Scoop
```powershell
scoop install tesseract
```

## After Installation

Uncomment line 12 in `ocr.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

## Verify Installation
```bash
tesseract --version
```

## Test OCR
```bash
python ocr.py path/to/payment_screenshot.jpg
```
