import requests
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

POLYMARKET_API_URL = "https://gamma-api.polymarket.com/events"

def send_telegram_message(message):
    """Sends a message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: Telegram configuration missing.")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print(f"Notification sent: {message[:50]}...")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Telegram message: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")

def get_events(limit=10):
    """Fetches recent events from Polymarket."""
    params = {
        "limit": limit
    }
    try:
        response = requests.get(POLYMARKET_API_URL, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch events: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")
        return []

def main():
    print("Starting Polymarket Monitor...")
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("WARNING: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
        print("Please create a .env file with your credentials.")
        return

    send_telegram_message("🤖 Polymarket Monitor Started!")
    
    seen_ids = set()
    
    # Initial fetch to populate seen_ids without sending notifications
    initial_events = get_events(limit=20)
    for event in initial_events:
        seen_ids.add(event.get('id'))
    
    print(f"Initialized with {len(seen_ids)} existing events.")

    # Send the latest event as a test to confirm formatting
    if initial_events:
        latest_event = initial_events[0]
        title = latest_event.get('title', 'Unknown Event')
        slug = latest_event.get('slug', '')
        url = f"https://polymarket.com/event/{slug}" if slug else "N/A"
        print(f"Sending test notification for: {title}")
        send_telegram_message(f"🧪 **Test Notification (Latest Event)**\n\n**{title}**\n\n[View on Polymarket]({url})")

    while True:
        try:
            print("Checking for new events...")
            events = get_events(limit=10)
            
            for event in reversed(events): # Process oldest to newest
                event_id = event.get('id')
                if event_id and event_id not in seen_ids:
                    title = event.get('title', 'Unknown Event')
                    slug = event.get('slug', '')
                    url = f"https://polymarket.com/event/{slug}" if slug else "N/A"
                    
                    message = f"🆕 **New Market Created!**\n\n**{title}**\n\n[View on Polymarket]({url})"
                    send_telegram_message(message)
                    
                    seen_ids.add(event_id)
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("Stopping monitor...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
