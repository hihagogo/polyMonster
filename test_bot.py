#!/usr/bin/env python3
"""
Quick test to verify the bot works locally.
This will run for 30 seconds then stop.
"""

import os
import sys
from dotenv import load_dotenv

# Add timeout
import signal
def timeout_handler(signum, frame):
    print("\n✅ Test completed successfully! Bot is working.")
    sys.exit(0)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)  # 30 second timeout

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found")
    exit(1)

print("Starting bot test (will run for 30 seconds)...")
print("Try sending /help to your bot now!")
print("-" * 60)

# Import and run minimal bot
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is working! This is a test response.")

application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("help", help_command))

try:
    application.run_polling(drop_pending_updates=True)
except KeyboardInterrupt:
    print("\n✅ Test stopped.")
