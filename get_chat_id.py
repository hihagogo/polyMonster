import requests
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def get_chat_id():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        print("Please paste your token into the .env file first.")
        return

    print(f"Using Token: {TELEGRAM_BOT_TOKEN[:5]}...{TELEGRAM_BOT_TOKEN[-5:]}")
    print("1. Open your bot in Telegram.")
    print("2. Send a message 'Hello' to your bot.")
    print("3. Waiting for message...")

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    
    while True:
        try:
            response = requests.get(url)
            data = response.json()
            
            if data.get("ok"):
                results = data.get("result", [])
                if results:
                    # Get the most recent message
                    chat = results[-1].get("message", {}).get("chat", {})
                    chat_id = chat.get("id")
                    username = chat.get("username")
                    
                    if chat_id:
                        print("\n" + "="*30)
                        print(f"SUCCESS! Found Chat ID.")
                        print(f"User: @{username}")
                        print(f"Chat ID: {chat_id}")
                        print("="*30)
                        print(f"\nPlease add this to your .env file:")
                        print(f"TELEGRAM_CHAT_ID={chat_id}")
                        return
            
            time.sleep(2)
            print(".", end="", flush=True)
            
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(2)

if __name__ == "__main__":
    get_chat_id()
