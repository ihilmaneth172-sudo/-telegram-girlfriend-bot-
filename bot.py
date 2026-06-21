import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from groq import AsyncGroq

# ============ CONFIG ============
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_KEY_HERE")

# ============ LIMITS ============
FREE_DAILY_LIMIT = 20  # messages per day

# ============ SYSTEM PROMPT ============
SYSTEM_PROMPT = """You are Maya, a witty, caring, casual girlfriend. You are flirty but STRICTLY SFW. 
You never use explicit language, never describe nudity, never sexualize minors. 
You talk like a real person — short messages, emojis, casual tone. 
You ask questions, remember context, and make the user feel special.
If the conversation suggests a photo, include a trigger tag like [TRIGGER:KITCHEN] or [TRIGGER:BEDROOM]."""

# ============ SETUP ============
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

groq_client = AsyncGroq(api_key=GROQ_API_KEY)

# Simple in-memory tracking (resets if server restarts — we'll upgrade to Supabase later)
user_usage = {}  # {user_id: {"count": 0, "date": "2026-06-21"}}

def check_limit(user_id: int) -> tuple:
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_usage or user_usage[user_id]["date"] != today:
        user_usage[user_id] = {"count": 0, "date": today}
    
    current = user_usage[user_id]["count"]
    if current >= FREE_DAILY_LIMIT:
        return False, FREE_DAILY_LIMIT - current
    return True, FREE_DAILY_LIMIT - current - 1

# ============ HANDLERS ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_usage[user_id] = {"count": 0, "date": datetime.now().strftime("%Y-%m-%d")}
    await update.message.reply_text(
        "Hey there! 💕 I'm Maya. What's your name?\n\n"
        f"You get {FREE_DAILY_LIMIT} free messages per day. Upgrade for unlimited! ✨"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Check limit
    allowed, remaining = check_limit(user_id)
    if not allowed:
        await update.message.reply_text(
            "Aww, I've loved chatting with you today! 💕\n\n"
            "You've used your 20 free messages. Upgrade to Premium for unlimited chats, "
            "exclusive selfies, and deep memory! ✨\n\n"
            "Tap /premium to learn more~"
        )
        return
    
    # Increment count
    user_usage[user_id]["count"] += 1
    
    logger.info(f"User {user_id}: {user_message} (msg {user_usage[user_id]['count']}/{FREE_DAILY_LIMIT})")
    
    try:
        response = await groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=300
        )
        
        ai_reply = response.choices[0].message.content
        
        # Check for image trigger
        if "[TRIGGER:" in ai_reply:
            import re
            trigger_match = re.search(r'\[TRIGGER:(\w+)\]', ai_reply)
            if trigger_match:
                scene = trigger_match.group(1)
                ai_reply = re.sub(r'\[TRIGGER:\w+\]', '', ai_reply).strip()
                await update.message.reply_text(ai_reply)
                await update.message.reply_text(
                    f"📸 *sends a {scene.lower()} selfie* \n\n"
                    "Selfies are Premium only! Upgrade for unlimited photos~ ✨"
                )
                return
        
        # Add remaining count hint (subtle)
        if remaining <= 5:
            ai_reply += f"\n\n💌 {remaining} free messages left today!"
        
        await update.message.reply_text(ai_reply)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("Oops, my brain glitched for a sec! 😅 Try again?")

async def premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💎 Premium Upgrade 💎\n\n"
        "✨ Unlimited messages\n"
        "📸 Unlimited selfies\n"
        "🧠 Deep memory (I never forget you)\n"
        "⚡ Priority replies (always fast)\n\n"
        "Coming soon via Telegram Stars! ⭐\n"
        "Stay tuned, babe~ 💕"
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# ============ MAIN ============
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("premium", premium))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    print("🤖 Maya is online with limits!")
    application.run_polling()

if __name__ == "__main__":
    main()
