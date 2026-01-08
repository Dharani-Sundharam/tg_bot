# Deploying to Railway

## Prerequisites
1. GitHub account
2. Railway account (sign up at https://railway.app)

## Step 1: Push to GitHub

```bash
cd telegram_bot
git init
git add .
git commit -m "Initial commit: Telegram payment bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/codepaste-telegram-bot.git
git push -u origin main
```

## Step 2: Deploy to Railway

1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your `codepaste-telegram-bot` repository
5. Railway will auto-detect Python and start deploying

## Step 3: Add Environment Variables

In Railway dashboard, go to **Variables** tab and add:

```
TELEGRAM_BOT_TOKEN=8304423944:AAFDJiQISj3r3Zys8t8c7tMMInIXrxCXD-0
MONGODB_URI=mongodb+srv://dharani3318s_db_user:HslGkpCG93kO3KC6@userdb.jjgrkqq.mongodb.net/
DATABASE_NAME=autotyper_db
LICENSE_EXPIRY_MINUTES=5
OCR_CONFIDENCE_THRESHOLD=0.7
```

## Step 4: Deploy!

Railway will automatically:
- Install Python dependencies
- Install Tesseract OCR
- Start the bot
- Keep it running 24/7

## Monitoring

- **Logs**: Click "View Logs" in Railway dashboard
- **Restart**: Click "Restart" if needed
- **Metrics**: See CPU/Memory usage

## Troubleshooting

### Bot not responding?
- Check logs for errors
- Verify environment variables are set
- Ensure MongoDB URI is correct

### Tesseract errors?
- Railway has Tesseract pre-installed
- Check logs for specific error messages

## Free Tier Limits

- 500 hours/month (20+ days)
- 512 MB RAM
- 1 GB disk space
- More than enough for this bot!

## Next Steps

After deployment:
1. Test bot on Telegram
2. Send a payment screenshot
3. Verify OCR extraction works
4. Move to Phase 3 (License generation)
