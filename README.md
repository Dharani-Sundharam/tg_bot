# CodePaste Telegram Payment Bot

Automated payment verification bot for CodePaste using OCR and license key generation.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Run the bot:
```bash
python bot.py
```

## Features

- ✅ Payment screenshot processing
- ✅ OCR extraction (Amount, UTR, Sender)
- ✅ Encrypted license key generation
- ✅ 5-minute expiry
- ✅ One-time redemption

## Bot Commands

- `/start` - Welcome message
- `/help` - Usage instructions

## Development Status

- [x] Phase 1: Basic bot setup
- [ ] Phase 2: OCR processing
- [ ] Phase 3: License system
- [ ] Phase 4: Backend API
- [ ] Phase 5: Desktop app integration
- [ ] Phase 6: Deployment

## Bot Link

https://t.me/CodePastebot
