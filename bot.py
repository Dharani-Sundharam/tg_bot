"""
CodePaste Telegram Payment Bot
Handles payment screenshot processing and license key generation
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime

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
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://dharani3318s_db_user:HslGkpCG93kO3KC6@userdb.jjgrkqq.mongodb.net/')
DATABASE_NAME = 'autotyper_db'

# Admin chat ID for forwarding screenshots (@Hex_April)
ADMIN_CHAT_ID = 6724557255


def escape_markdown(text: str) -> str:
    """Escape/remove special characters for Telegram Markdown"""
    if not text:
        return text
    # For Telegram Markdown v1, just remove problematic characters
    # These characters cause parsing issues: _ * ` [ ]
    import re
    # Replace underscores with spaces, remove other special markdown chars
    text = str(text)
    text = text.replace('_', ' ')
    text = text.replace('*', '')
    text = text.replace('`', "'")
    text = text.replace('[', '(')
    text = text.replace(']', ')')
    return text


def get_database():
    """Get MongoDB connection"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DATABASE_NAME]
        db.command('ping')
        return db
    except Exception as e:
        logger.error(f"MongoDB connection error: {e}")
        return None


def check_utr_exists(utr: str) -> dict:
    """Check if UTR already exists in database"""
    db = get_database()
    if db is None:
        return {"exists": False, "error": "Database unavailable"}
    
    transactions = db["transactions"]
    existing = transactions.find_one({"utr": utr})
    
    if existing:
        return {
            "exists": True,
            "user": existing.get("telegram_user"),
            "date": existing.get("created_at"),
            "credits": existing.get("credits")
        }
    return {"exists": False}


def save_transaction(utr: str, amount: float, credits: int, sender: str, telegram_user: str, telegram_id: int):
    """Save transaction to database"""
    db = get_database()
    if db is None:
        return False
    
    transactions = db["transactions"]
    transactions.insert_one({
        "utr": utr,
        "amount": amount,
        "credits": credits,
        "sender": sender,
        "telegram_user": telegram_user,
        "telegram_id": telegram_id,
        "created_at": datetime.utcnow(),
        "status": "license_generated"
    })
    return True


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    welcome_message = """
🎉 *Welcome to CodePaste Payment Bot!*

I verify payments and generate license keys for CodePaste.

💡 *Recommended:* Please use **Google Pay (GPay)** for the best results.

*How it works:*
1. Send me a screenshot of your payment confirmation (GPay preferred)
2. I'll verify the details and generate your license key
3. Enter the key in CodePaste app to get credits

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
📖 *How to Verify Payment*

✅ *Best Results:* Use **Google Pay (GPay)** for instant verification.

*Step 1: Send Screenshot*
Send a clear screenshot of your payment showing:
• Payment amount
• UTR/Transaction ID
• Sender name
• *Recommendation:* Use GPay for faster processing.

*Step 2: Get License Key*
I'll verify the screenshot and send you a license key.
⏰ License keys expire in 5 minutes!

*Step 3: Redeem in App*
Open CodePaste app → Buy Credits → Enter license key

*Troubleshooting:*
• Screenshot blurry? → I'll ask for manual review
• Payment not detected? → Send clearer screenshot (GPay recommended)

Need help? Contact: @Hex_April
    """
    await update.message.reply_text(help_message, parse_mode='Markdown')


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment screenshot uploads"""
    user = update.effective_user
    logger.info(f"Received photo from {user.username} ({user.id})")
    
    # Forward the photo to admin for record-keeping
    try:
        await update.message.forward(chat_id=ADMIN_CHAT_ID)
        logger.info(f"Forwarded photo from {user.username} to admin")
    except Exception as e:
        logger.warning(f"Failed to forward photo to admin: {e}")
    
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
            error_msg = result.get('error', '')
            # Check for specific overload/rate limit/quota errors
            if any(err in error_msg for err in ["503", "429", "overloaded", "UNAVAILABLE", "RESOURCE_EXHAUSTED"]):
                await processing_msg.edit_text(
                    "⚠️ *Server Busy / Quota Limit*\n\n"
                    "The AI server is currently at its limit or overloaded.\n"
                    "Please try sending the screenshot again in a few minutes.\n\n"
                    "If the issue persists, please DM your screenshot to: @Hex_April",
                    parse_mode='Markdown'
                )
            else:
                # IMPORTANT: Safety Fallback
                # If anything else goes wrong (OCR failed, unknown error),
                # explicitly tell user to DM the screenshot for manual help.
                await processing_msg.edit_text(
                    "❌ *Verification Failed*\n\n"
                    "I couldn't verify this screenshot automatically.\n\n"
                    "🔸 *Action Required:*\n"
                    "Please **Forward this screenshot** directly to: @Hex_April\n"
                    "They will manually verify it and grant your credits!",
                    parse_mode='Markdown'
                )
            return
        
        # Extract data
        amount = result.get('amount')
        utr = result.get('utr')
        sender = result.get('sender')
        recipient = result.get('recipient')
        recipient_valid = result.get('recipient_valid', False)
        confidence = result.get('confidence', 0)
        
        # Check if payment was sent to the correct account
        if not recipient_valid:
            await processing_msg.edit_text(
                "❌ Wrong Recipient Account\n\n"
                f"Payment was sent to: {recipient if recipient else 'Unknown'}\n\n"
                "Please ensure you send the payment to the correct OR code displayed and try again.\n"
                "If you believe this is an error, contact: @Hex_April"
            )
            logger.warning(f"Wrong recipient: {recipient} by user {user.username}")
            return
        
        # Check if manual review needed
        if result.get('needs_review'):
            await processing_msg.edit_text(
                "⚠️ Low Confidence Detection\n\n"
                f"Detected:\n"
                f"• Amount: ₹{amount if amount else 'Not found'}\n"
                f"• UTR: {utr if utr else 'Not found'}\n"
                f"• Sender: {sender if sender else 'Not found'}\n"
                f"• Recipient: {recipient if recipient else 'Not found'}\n"
                f"• Confidence: {confidence:.0%}\n\n"
                "🔍 This needs manual review.\n"
                "Please send a clearer screenshot or contact support: @Hex_April"
            )
            return
        
        # ===== CHECK FOR DUPLICATE UTR =====
        if utr:
            utr_check = check_utr_exists(utr)
            if utr_check.get('exists'):
                # This UTR has already been used!
                await processing_msg.edit_text(
                    "🚫 *Duplicate Payment Detected!*\n\n"
                    f"This UTR (`{utr}`) has already been used.\n\n"
                    f"Previously used by: @{utr_check.get('user', 'Unknown')}\n"
                    f"Credits awarded: {utr_check.get('credits', 0):,}\n\n"
                    "⚠️ Each payment can only be redeemed once.\n"
                    "If you believe this is an error, contact: @Hex_April",
                    parse_mode='Markdown'
                )
                logger.warning(f"Duplicate UTR attempt: {utr} by user {user.username}")
                return
        
        # Check if amount was detected
        if not amount:
            await processing_msg.edit_text(
                "⚠️ Could Not Detect Amount\n\n"
                f"🔢 UTR: {utr}\n"
                f"👤 Sender: {sender}\n\n"
                "❌ The payment amount could not be detected.\n"
                "Please send a clearer screenshot showing:\n"
                "• The payment amount (₹10, ₹49, ₹99)\n"
                "• 'Paid' or 'Sent' text near the amount\n\n"
                "Need help? Contact: @Hex_April"
            )
            return
        
        # Success - show extracted data
        await processing_msg.edit_text(
            "✅ Payment Verified!\n\n"
            f"💰 Amount: ₹{amount}\n"
            f"🔢 UTR: {utr}\n"
            f"👤 Sender: {sender}\n"
            f"📊 Confidence: {confidence:.0%}\n\n"
            "⏳ Generating license key..."
        )
        
        # Generate license key
        from license_manager import generate_license_key, calculate_credits
        credits = calculate_credits(amount)
        license_key = generate_license_key(amount, utr, credits)
        
        # ===== SAVE TRANSACTION TO DATABASE =====
        save_transaction(
            utr=utr,
            amount=amount,
            credits=credits,
            sender=sender or "Unknown",
            telegram_user=user.username or str(user.id),
            telegram_id=user.id
        )
        
        # Send license key to user - send key separately for easy copying
        await update.message.reply_text(
            "🎉 *License Key Generated!*\n\n"
            f"⭐ Credits: {credits:,}\n"
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
        
        # ===== NOTIFY ADMIN WITH PAYMENT DETAILS =====
        try:
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            admin_notification = (
                "💰 NEW PAYMENT RECEIVED\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"🕐 Time: {current_time}\n"
                f"👤 TG User: @{user.username or 'N/A'}\n"
                f"🆔 TG ID: {user.id}\n"
                f"📛 TG Name: {user.first_name or ''} {user.last_name or ''}\n\n"
                f"💵 Amount: ₹{amount}\n"
                f"🔢 UTR: {utr}\n"
                f"👤 Sender (from screenshot): {sender}\n"
                f"🎁 Credits Awarded: {credits:,}\n\n"
                f"🔑 License Key: {license_key}"
            )
            await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_notification)
            logger.info(f"Admin notified about payment from {user.username}")
        except Exception as e:
            logger.warning(f"Failed to notify admin: {e}")
        
        logger.info(f"License key generated for {user.username}: {credits} credits, UTR: {utr}")
        
    except Exception as e:
        logger.error(f"Error processing photo: {e}")
        await processing_msg.edit_text(
            "❌ An error occurred while processing your screenshot.\n\n"
            "Please try again in a few minutes.\n"
            "If the issue persists, please DM your screenshot to: @Hex_April\n"
            "Reference Error: Processing Failed"
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
