import logging
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLYMARKET_API_URL = "https://gamma-api.polymarket.com/events"

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Global set to track seen events
seen_ids = set()
last_check_time = None

def get_events(limit=10):
    """Fetches recent events from Polymarket."""
    params = {"limit": limit}
    try:
        response = requests.get(POLYMARKET_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Failed to fetch events: {e}")
        return []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "🤖 **Polymarket Monitor is Online!**\n\n"
        "I will notify you when new markets are created.\n"
        "Commands:\n"
        "/status - Check if I'm running\n"
        "/latest - Show the most recent market\n"
        "/help - Show this message",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a help message."""
    await update.message.reply_text(
        "**Available Commands:**\n"
        "/status - Check bot health\n"
        "/latest - Fetch the newest market manually\n"
        "/help - Show available commands",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the status of the bot."""
    global last_check_time
    status_msg = "🟢 **System Operational**\n"
    if last_check_time:
        status_msg += f"Last Check: {last_check_time.strftime('%H:%M:%S UTC')}\n"
    else:
        status_msg += "Last Check: Never\n"
    
    status_msg += f"Events Tracked: {len(seen_ids)}"
    await update.message.reply_text(status_msg, parse_mode="Markdown")

async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetches and shows the single most recent event."""
    events = get_events(limit=1)
    if events:
        event = events[0]
        title = event.get('title', 'Unknown Event')
        slug = event.get('slug', '')
        url = f"https://polymarket.com/event/{slug}" if slug else "N/A"
        await update.message.reply_text(
            f"🆕 **Latest Market:**\n\n**{title}**\n\n[View on Polymarket]({url})",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("Could not fetch latest event.")

async def check_new_events(context: ContextTypes.DEFAULT_TYPE):
    """Background task to check for new events."""
    global last_check_time
    last_check_time = datetime.utcnow()
    
    events = get_events(limit=10)
    
    # Process from oldest to newest
    for event in reversed(events):
        event_id = event.get('id')
        if event_id and event_id not in seen_ids:
            # If we have seen_ids (meaning not first run), send notification
            if seen_ids:
                title = event.get('title', 'Unknown Event')
                slug = event.get('slug', '')
                url = f"https://polymarket.com/event/{slug}" if slug else "N/A"
                
                message = f"🆕 **New Market Created!**\n\n**{title}**\n\n[View on Polymarket]({url})"
                
                # Send to the configured channel/chat
                if TELEGRAM_CHAT_ID:
                    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
            
            seen_ids.add(event_id)

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    # Initialize seen_ids with current events so we don't spam on startup
    initial_events = get_events(limit=20)
    for event in initial_events:
        seen_ids.add(event.get('id'))
    print(f"Initialized with {len(seen_ids)} existing events.")

    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("latest", latest))

    # Add Background Job
    job_queue = application.job_queue
    job_queue.run_repeating(check_new_events, interval=60, first=10)

    # Run the bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
