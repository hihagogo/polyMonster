#!/usr/bin/env python3
"""Debug script to check what events the API returns."""

import requests
from datetime import datetime, timezone, timedelta
import json

url = "https://gamma-api.polymarket.com/events"
params = {
    "limit": 100
    # No active filter
}

response = requests.get(url, params=params)
events = response.json()

print(f"Total events returned: {len(events)}\n")

# Check end dates
now = datetime.now(timezone.utc)
cutoff_1m = now + timedelta(days=30)

events_within_1m = 0
open_events_within_1m = 0

for event in events:
    end_date_iso = event.get('endDateIso')
    closed = event.get('closed')
    
    if end_date_iso and not closed:
        try:
            end_date = datetime.fromisoformat(end_date_iso.replace('Z', '+00:00'))
            if now < end_date <= cutoff_1m:
                open_events_within_1m += 1
                print(f"✓ {event.get('title')[:70]} - Ends: {end_date_iso.split('T')[0]}")
        except:
            pass

print(f"\n{open_events_within_1m} OPEN events ending within 1 month out of {len(events)} total")

# Check closed vs open
closed_count = sum(1 for e in events if e.get('closed'))
print(f"Closed events: {closed_count}")
print(f"Open events: {len(events) - closed_count}")

# Check a few sample events
print("\nSample of first 5 events:")
for i, event in enumerate(events[:5]):
    print(f"\n{i+1}. {event.get('title')}")
    print(f"   End Date: {event.get('endDateIso')}")
    print(f"   Active: {event.get('active')}")
    print(f"   Closed: {event.get('closed')}")
