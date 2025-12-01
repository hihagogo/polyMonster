import logging
import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import json

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
POLYMARKET_API_URL = "https://gamma-api.polymarket.com/events"
CLOB_API_URL = "https://clob.polymarket.com"

# Target events to track daily
TARGET_EVENT_SLUGS = [
    "trump-out-as-president-by-march-31",
    "trump-out-as-president-before-2027"
]

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

def get_market_details(slug):
    """Fetches detailed market data for a specific event slug."""
    try:
        response = requests.get(f"{POLYMARKET_API_URL}?slug={slug}")
        response.raise_for_status()
        events = response.json()
        
        if not events or len(events) == 0:
            return None
            
        event = events[0]
        title = event.get('title', 'Unknown')
        markets = event.get('markets', [])
        
        if not markets:
            return None
            
        # Get the first market (usually the main Yes/No market)
        market = markets[0]
        
        # outcomePrices is a list like ['0.05', '0.95'], first is Yes price
        outcome_prices = market.get('outcomePrices', ['0', '0'])
        yes_price = outcome_prices[0] if isinstance(outcome_prices, list) else '0'
        
        return {
            'title': title,
            'yes_price': yes_price,
            'volume': market.get('volume', '0'),
            'liquidity': market.get('liquidity', '0')
        }
    except Exception as e:
        logging.error(f"Failed to fetch market details for {slug}: {e}")
        return None

def get_token_id(slug):
    """Gets the CLOB token ID for a specific event slug."""
    try:
        response = requests.get(f"{POLYMARKET_API_URL}?slug={slug}")
        response.raise_for_status()
        events = response.json()
        
        if not events or len(events) == 0:
            return None
            
        event = events[0]
        markets = event.get('markets', [])
        
        if not markets:
            return None
            
        market = markets[0]
        clob_token_ids = market.get('clobTokenIds', [])
        
        # Return first token ID (Yes token)
        if isinstance(clob_token_ids, list) and len(clob_token_ids) > 0:
            return clob_token_ids[0]
        return None
    except Exception as e:
        logging.error(f"Failed to get token ID for {slug}: {e}")
        return None

def fetch_price_history(token_id, interval='1w', fidelity=60):
    """Fetches historical price data from CLOB API."""
    try:
        url = f"{CLOB_API_URL}/prices-history"
        params = {
            'market': token_id,
            'interval': interval,
            'fidelity': fidelity
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Failed to fetch price history: {e}")
        return []

def generate_chart(slug, title, price_data):
    """Generates a price chart and returns the file path."""
    try:
        if not price_data:
            return None
            
        # Parse timestamps and prices
        timestamps = [datetime.fromtimestamp(item['t']) for item in price_data]
        prices = [float(item['p']) * 100 for item in price_data]  # Convert to percentage
        
        # Create the chart
        plt.figure(figsize=(10, 6))
        plt.plot(timestamps, prices, linewidth=2, color='#3b82f6')
        plt.title(f"{title}", fontsize=14, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Yes Price (%)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Save to temp file
        filepath = f"/tmp/chart_{slug}.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return filepath
    except Exception as e:
        logging.error(f"Failed to generate chart: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "🤖 **Polymarket Monitor is Online!**\n\n"
        "I will notify you when new markets are created.\n\n"
        "**Commands:**\n"
        "/status - Check bot health\n"
        "/latest - Show the most recent market\n"
        "/tracking - Check Trump event prices\n"
        "/chart - Show price history charts\n"
        "/help - Show all commands",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a help message."""
    await update.message.reply_text(
        "**📋 All Available Commands:**\n\n"
        "/start - Welcome message\n"
        "/status - Check bot health & uptime\n"
        "/latest - Show the most recent market\n"
        "/tracking - Check Trump event prices & volume\n"
        "/chart - Show price history charts (past week)\n"
        "/help - Show this command list",
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

async def tracking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check tracked Trump event prices and volume."""
    message = "📊 **Tracked Events Update**\n\n"
    
    for slug in TARGET_EVENT_SLUGS:
        details = get_market_details(slug)
        if details:
            yes_price = float(details['yes_price'])
            volume = float(details['volume'])
            
            message += f"**{details['title']}**\n"
            message += f"Yes Price: {yes_price:.1%}\n"
            message += f"Volume: ${volume:,.0f}\n\n"
        else:
            message += f"❌ Could not fetch data for {slug}\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

async def chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generates and sends price charts for tracked events."""
    await update.message.reply_text("📊 Generating charts...")
    
    for slug in TARGET_EVENT_SLUGS:
        # Get event details
        details = get_market_details(slug)
        if not details:
            await update.message.reply_text(f"❌ Could not fetch data for {slug}")
            continue
            
        # Get token ID
        token_id = get_token_id(slug)
        if not token_id:
            await update.message.reply_text(f"❌ Could not get token ID for {slug}")
            continue
            
        # Fetch price history
        price_data = fetch_price_history(token_id, interval='1w', fidelity=60)
        if not price_data:
            await update.message.reply_text(f"❌ No price history available for {details['title']}")
            continue
            
        # Generate chart
        chart_path = generate_chart(slug, details['title'], price_data)
        if not chart_path:
            await update.message.reply_text(f"❌ Failed to generate chart for {details['title']}")
            continue
            
        # Send chart
        try:
            with open(chart_path, 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption=f"**{details['title']}** (Past Week)", parse_mode="Markdown")
            # Clean up
            os.remove(chart_path)
        except Exception as e:
            logging.error(f"Failed to send chart: {e}")
            await update.message.reply_text(f"❌ Failed to send chart for {details['title']}")

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

async def daily_market_update(context: ContextTypes.DEFAULT_TYPE):
    """Sends daily update for tracked Trump events."""
    message = "📊 **Daily Trump Event Update**\n\n"
    
    for slug in TARGET_EVENT_SLUGS:
        details = get_market_details(slug)
        if details:
            yes_price = float(details['yes_price'])
            volume = float(details['volume'])
            
            message += f"**{details['title']}**\n"
            message += f"Yes Price: {yes_price:.1%}\n"
            message += f"24h Volume: ${volume:,.0f}\n\n"
        else:
            message += f"❌ Could not fetch data for {slug}\n\n"
    
    if TELEGRAM_CHAT_ID:
        await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")

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
    application.add_handler(CommandHandler("tracking", tracking))
    application.add_handler(CommandHandler("chart", chart))

    # Add Background Job
    job_queue = application.job_queue
    job_queue.run_repeating(check_new_events, interval=60, first=10)
    
    # Add Daily Trump Event Update (runs at 8:00 AM UTC)
    import datetime
    daily_time = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc)
    job_queue.run_daily(daily_market_update, time=daily_time)

    # Run the bot
    print("Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()
