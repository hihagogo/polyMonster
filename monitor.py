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
        
        # outcomePrices can be a list or a string representation of a list
        outcome_prices = market.get('outcomePrices', ['0', '0'])
        
        if isinstance(outcome_prices, str):
            try:
                import json
                outcome_prices = json.loads(outcome_prices)
            except:
                outcome_prices = ['0', '0']
                
        yes_price = outcome_prices[0] if isinstance(outcome_prices, list) and len(outcome_prices) > 0 else '0'
        
        return {
            'title': title,
            'yes_price': yes_price,
            'volume': market.get('volume', '0'),
            'liquidity': market.get('liquidity', '0')
        }
    except Exception as e:
        logging.error(f"Failed to fetch market details for {slug}: {e}")
        return None



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message."""
    await update.message.reply_text(
        "🤖 Polymarket Monitor is Online!\n\n"
        "I will notify you when new markets are created.\n\n"
        "📋 Available Commands:\n\n"
        "/start - Welcome message\n"
        "/help - Show this command list\n"
        "/status - Check bot health and uptime\n"
        "/latest - Show the most recent market\n"
        "/tracking - Check Trump event prices and volume\n"
        "/95 - Find high conviction events (>94% bid, >$500k liq)\n"
        "/95_1d - High conviction events ending within 24 hours"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a help message."""
    await update.message.reply_text(
        "📋 All Available Commands:\n\n"
        "/start - Welcome message\n"
        "/status - Check bot health and uptime\n"
        "/latest - Show the most recent market\n"
        "/tracking - Check Trump event prices and volume\n"
        "/95 - Find high conviction events (>94% bid, >$500k liq)\n"
        "/95_1d - High conviction events ending within 24 hours\n"
        "/help - Show this command list"
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
            message += f"Yes Price: {yes_price * 100:.1f}¢ (${yes_price:.3f})\n"
            message += f"Volume: ${volume:,.0f}\n"
            
            # Use specific Predicts.guru links
            if slug == "trump-out-as-president-by-march-31":
                message += f"[View on Predicts.guru](https://www.predicts.guru/event-analytics/trump-out-as-president-by-march-31)\n\n"
            elif slug == "trump-out-as-president-before-2027":
                message += f"[View on Predicts.guru](https://www.predicts.guru/event-analytics/trump-out-as-president-before-2027)\n\n"
            else:
                message += f"[View on Polymarket](https://polymarket.com/event/{slug})\n\n"
        else:
            message += f"❌ Could not fetch data for {slug}\n\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

def get_high_conviction_events():
    """Helper function to fetch high conviction events (>94% bid, >$500k liquidity)."""
    url = f"{POLYMARKET_API_URL}"
    params = {
        "limit": 100,
        "active": "true",
        "closed": "false",
        "order": "liquidity",
        "ascending": "false"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        events = response.json()
        
        high_conviction_events = []
        
        for event in events:
            markets = event.get('markets', [])
            if not markets:
                continue
                
            market = markets[0]
            
            # Check Liquidity > $500k
            liquidity = float(market.get('liquidity', 0))
            if liquidity < 500_000:
                continue
                
            # Check Price > 94% (any outcome)
            outcome_prices = market.get('outcomePrices', ['0', '0'])
            if isinstance(outcome_prices, str):
                try:
                    import json
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = ['0', '0']
            
            if not isinstance(outcome_prices, list) or len(outcome_prices) < 1:
                continue
            
            # Convert all prices to floats and find the max
            prices = []
            for p in outcome_prices:
                try:
                    prices.append(float(p))
                except:
                    pass
            
            if not prices:
                continue
                
            max_price = max(prices)
                
            if max_price > 0.94:
                # Get end date
                end_date = market.get('endDateIso', 'N/A')
                
                high_conviction_events.append({
                    "title": event.get('title'),
                    "slug": event.get('slug'),
                    "max_price": max_price,
                    "liquidity": liquidity,
                    "end_date": end_date
                })
        
        return high_conviction_events
        
    except Exception as e:
        logging.error(f"Error fetching high conviction events: {e}")
        return None

async def cmd_95(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finds events with >94% bid and >$500k liquidity."""
    await update.message.reply_text("🔍 Scanning for high conviction events...")
    
    high_conviction_events = get_high_conviction_events()
    
    if high_conviction_events is None:
        await update.message.reply_text("❌ Failed to fetch events.")
        return
        
    if not high_conviction_events:
        await update.message.reply_text("No events found matching criteria (>94% bid, >$500k liquidity).")
        return
        
    message = "🚀 **High Conviction Events (>94%)**\n\n"
    for e in high_conviction_events:
        message += f"**{e['title']}**\n"
        message += f"Price: {e['max_price']:.1%} | Liq: ${e['liquidity']:,.0f}\n"
        message += f"End Date: {e['end_date']}\n"
        message += f"[View on Predicts.guru](https://www.predicts.guru/event-analytics/{e['slug']})\n\n"
        
    await update.message.reply_text(message, parse_mode="Markdown")

async def cmd_95_1d(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finds high conviction events ending within 24 hours."""
    await update.message.reply_text("🔍 Scanning for high conviction events ending soon...")
    
    high_conviction_events = get_high_conviction_events()
    
    if high_conviction_events is None:
        await update.message.reply_text("❌ Failed to fetch events.")
        return
    
    # Filter for events ending within 24 hours
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=24)
    
    filtered_events = []
    for e in high_conviction_events:
        end_date_str = e['end_date']
        if end_date_str == 'N/A':
            continue
        
        try:
            # Parse the end date (format: YYYY-MM-DD)
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            if now <= end_date <= cutoff:
                filtered_events.append(e)
        except:
            continue
    
    if not filtered_events:
        await update.message.reply_text("No events found ending within 24 hours (>94% bid, >$500k liquidity).")
        return
        
    message = "⏰ **High Conviction Events Ending Within 24 Hours**\n\n"
    for e in filtered_events:
        message += f"**{e['title']}**\n"
        message += f"Price: {e['max_price']:.1%} | Liq: ${e['liquidity']:,.0f}\n"
        message += f"End Date: {e['end_date']}\n"
        message += f"[View on Predicts.guru](https://www.predicts.guru/event-analytics/{e['slug']})\n\n"
        
    await update.message.reply_text(message, parse_mode="Markdown")



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

async def daily_95_report(context: ContextTypes.DEFAULT_TYPE):
    """Sends daily report of high conviction events (>94% bid, >$500k liq)."""
    url = f"{POLYMARKET_API_URL}"
    params = {
        "limit": 100,
        "active": "true",
        "closed": "false",
        "order": "liquidity",
        "ascending": "false"
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        events = response.json()
        
        high_conviction_events = []
        
        for event in events:
            markets = event.get('markets', [])
            if not markets:
                continue
                
            market = markets[0]
            
            # Check Liquidity > $500k
            liquidity = float(market.get('liquidity', 0))
            if liquidity < 500_000:
                continue
                
            # Check Price > 94% (any outcome)
            outcome_prices = market.get('outcomePrices', ['0', '0'])
            if isinstance(outcome_prices, str):
                try:
                    import json
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = ['0', '0']
            
            if not isinstance(outcome_prices, list) or len(outcome_prices) < 1:
                continue
            
            # Convert all prices to floats and find the max
            prices = []
            for p in outcome_prices:
                try:
                    prices.append(float(p))
                except:
                    pass
            
            if not prices:
                continue
                
            max_price = max(prices)
                
            if max_price > 0.94:
                # Get end date
                end_date = market.get('endDateIso', 'N/A')
                
                high_conviction_events.append({
                    "title": event.get('title'),
                    "slug": event.get('slug'),
                    "max_price": max_price,
                    "liquidity": liquidity,
                    "end_date": end_date
                })
        
        if not high_conviction_events:
            message = "📊 **Daily High Conviction Report**\n\nNo events found matching criteria (>94% bid, >$500k liquidity)."
        else:
            message = "📊 **Daily High Conviction Report**\n\n"
            for e in high_conviction_events:
                message += f"**{e['title']}**\n"
                message += f"Price: {e['max_price']:.1%} | Liq: ${e['liquidity']:,.0f}\n"
                message += f"End Date: {e['end_date']}\n"
                message += f"[View on Predicts.guru](https://www.predicts.guru/event-analytics/{e['slug']})\n\n"
        
        if TELEGRAM_CHAT_ID:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message, parse_mode="Markdown")
            
    except Exception as e:
        logging.error(f"Error in daily /95 report: {e}")
        if TELEGRAM_CHAT_ID:
            await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="❌ Failed to generate daily high conviction report.")

def main():
    """Start the bot."""
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found.")
        return

    # Delete any existing webhook to prevent conflicts with polling
    # Try multiple times to ensure it's cleared
    for attempt in range(3):
        try:
            delete_webhook_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
            response = requests.post(delete_webhook_url)
            result = response.json()
            print(f"Webhook deletion attempt {attempt + 1}: {result}")
            if result.get('ok'):
                break
        except Exception as e:
            print(f"Warning: Could not delete webhook (attempt {attempt + 1}): {e}")
        
        if attempt < 2:
            import time
            time.sleep(2)  # Wait before retry

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
    application.add_handler(CommandHandler("95", cmd_95))
    application.add_handler(CommandHandler("95_1d", cmd_95_1d))


    # Add Background Job
    job_queue = application.job_queue
    job_queue.run_repeating(check_new_events, interval=60, first=10)
    
    # Add Daily Trump Event Update (runs at 8:00 AM UTC)
    import datetime
    daily_time = datetime.time(hour=8, minute=0, tzinfo=datetime.timezone.utc)
    job_queue.run_daily(daily_market_update, time=daily_time)
    
    # Add /95 Report every 8 hours, first run at 6:15 PM Singapore time (10:15 AM UTC)
    # Singapore is UTC+8, so 6:15 PM SGT = 10:15 AM UTC
    # Calculate seconds until first run (10:15 AM UTC today or tomorrow)
    now = datetime.datetime.now(datetime.timezone.utc)
    target_time = now.replace(hour=10, minute=15, second=0, microsecond=0)
    if target_time <= now:
        target_time += datetime.timedelta(days=1)
    first_run_seconds = (target_time - now).total_seconds()
    job_queue.run_repeating(daily_95_report, interval=28800, first=first_run_seconds)  # Every 8 hours (28800 seconds)

    # Run the bot with retry logic for Telegram conflicts
    print("Bot is starting...")
    
    max_retries = 5
    retry_delay = 5
    
    for retry in range(max_retries):
        try:
            print(f"Starting polling (attempt {retry + 1}/{max_retries})...")
            application.run_polling(drop_pending_updates=True)
            break  # If successful, exit loop
        except Exception as e:
            error_msg = str(e)
            if "Conflict" in error_msg and retry < max_retries - 1:
                print(f"Telegram conflict detected. Waiting {retry_delay} seconds before retry...")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                
                # Try to delete webhook again
                try:
                    delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true"
                    requests.post(delete_url)
                except:
                    pass
            else:
                print(f"Fatal error: {e}")
                raise

if __name__ == "__main__":
    main()
