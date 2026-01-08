"""
CodePaste Telegram Payment Bot
Handles payment screenshot processing and license key generation
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome_message = """
🎉 *Welcome to CodePaste Payment Bot!*

To buy credits:
1. Pay via UPI to: `dharani3318s@oksbi`
2. Send me a screenshot of your payment confirmation
3. I'll generate a license key for you
4. Enter the key in CodePaste app to get credits

*Credit Packages:*
• ₹10 = 1,000 credits
• ₹49 = 7,000 credits  
• ₹99 = 13,000 credits

Send /help for more information.
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message when /help is issued"""
    help_message = """
📖 *How to Use CodePaste Payment Bot*

*Step 1: Make Payment*
Pay to UPI ID: `dharani3318s@oksbi`

*Step 2: Send Screenshot*
After payment, send me a clear screenshot showing:
• Payment amount
• UTR/Transaction ID
• Sender name

*Step 3: Get License Key*
I'll process your screenshot and send you a license key.
⏰ License keys expire in 5 minutes!

*Step 4: Redeem in App*
Open CodePaste app → Buy Credits → Enter license key

*Troubleshooting:*
• Screenshot blurry? → I'll ask for manual review
• License expired? → Contact support
• Payment not detected? → Send clearer screenshot

Need help? Contact: @YourSupportUsername
    """
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment screenshot uploads"""
    user = update.effective_user
    logger.info(f"Received photo from {user.username} ({user.id})")
    
    # Send processing message
    processing_msg = await update.message.reply_text("📸 Processing your screenshot...")
    
    try:
        # Get the largest photo
        photo = update.message.photo[-1]
        
        # Download photo
        file = await photo.get_file()
        file_path = f"screenshots/{user.id}_{photo.file_id}.jpg"
        
        # Create screenshots directory if not exists
        import os
        os.makedirs("screenshots", exist_ok=True)
        
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded photo to {file_path}")
        
        # Process with OCR
        from ocr import process_payment_screenshot
        result = process_payment_screenshot(file_path)
        
        if not result['success']:
            await processing_msg.edit_text(
                "❌ Failed to process screenshot.\n\n"
                f"Error: {result.get('error')}\n\n"
                "Please send a clearer screenshot."
            )
            return
        
        # Extract data
        amount = result.get('amount')
        utr = result.get('utr')
        sender = result.get('sender')
        confidence = result.get('confidence', 0)
        
        # Check if manual review needed
        if result.get('needs_review'):
            await processing_msg.edit_text(
                "⚠️ *Low Confidence Detection*\n\n"
                f"Detected:\n"
                f"• Amount: ₹{amount if amount else 'Not found'}\n"
                f"• UTR: {utr if utr else 'Not found'}\n"
                f"• Sender: {sender if sender else 'Not found'}\n"
                f"• Confidence: {confidence:.0%}\n\n"
                "🔍 This needs manual review.\n"
                "Please send a clearer screenshot or contact support.",
                parse_mode='Markdown'
            )
            return
        
        # Success - show extracted data
        await processing_msg.edit_text(
            "✅ *Payment Detected!*\n\n"
            f"💰 Amount: ₹{amount}\n"
            f"🔢 UTR: `{utr}`\n"
            f"👤 Sender: {sender}\n"
            f"📊 Confidence: {confidence:.0%}\n\n"
            "⏳ Generating license key...",
            parse_mode='Markdown'
        )
        
        # Generate license key
        from license_manager import generate_license_key, calculate_credits
        credits = calculate_credits(amount)
        license_key = generate_license_key(amount, utr, credits)
        
        # Send license key to user - send key separately for easy copying
        await update.message.reply_text(
            "🎉 *License Key Generated!*\n\n"
            f"⭐ Credits: {credits}\n"
            f"⏰ Valid for: 5 minutes\n\n"
            "*Copy the key from the next message:*",
            parse_mode='Markdown'
        )
        
        # Send license key as plain text (no markdown) for easy copying
        await update.message.reply_text(license_key)
        
        await update.message.reply_text(
            "*How to redeem:*\n"
            "1. Open CodePaste desktop app\n"
            "2. Click 'Buy Credits'\n"
            "3. Paste the license key above\n"
            "4. Credits will be added instantly!\n\n"
            "⚠️ Key expires in 5 minutes!",
            parse_mode='Markdown'
        )
        
        logger.info(f"License key generated for {user.username}: {credits} credits")
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await processing_msg.edit_text(
            "❌ An error occurred while processing your screenshot.\n\n"
            "Please try again or contact support."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    await update.message.reply_text(
        "Please send a payment screenshot or use /help for instructions."
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Register error handler
    app.add_error_handler(error_handler)
    
    # Start bot
    logger.info("Starting CodePaste Payment Bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
