#!/usr/bin/env python3
"""
Script to manually clear Telegram webhook and check bot status.
Run this locally to force-clear any stuck webhooks.
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

print("=" * 60)
print("Telegram Bot Webhook Cleaner")
print("=" * 60)

# 1. Check current webhook status
print("\n1. Checking current webhook info...")
response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo")
webhook_info = response.json()
print(f"Response: {webhook_info}")

# 2. Delete webhook with drop_pending_updates
print("\n2. Deleting webhook and dropping pending updates...")
response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook?drop_pending_updates=true")
delete_result = response.json()
print(f"Response: {delete_result}")

# 3. Verify webhook is cleared
print("\n3. Verifying webhook is cleared...")
response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo")
webhook_info = response.json()
print(f"Response: {webhook_info}")

# 4. Check bot info
print("\n4. Checking bot info...")
response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
bot_info = response.json()
print(f"Response: {bot_info}")

print("\n" + "=" * 60)
if delete_result.get('ok') and not webhook_info.get('result', {}).get('url'):
    print("✅ SUCCESS: Webhook cleared! Bot is ready for polling.")
else:
    print("⚠️  WARNING: There might still be issues. Check the responses above.")
print("=" * 60)
