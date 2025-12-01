import requests
import json

def get_token_ids():
    slugs = [
        "trump-out-as-president-by-march-31",
        "trump-out-as-president-before-2027"
    ]
    
    for slug in slugs:
        url = f"https://gamma-api.polymarket.com/events?slug={slug}"
        response = requests.get(url)
        events = response.json()
        
        if events:
            event = events[0]
            print(f"\nEvent: {event.get('title')}")
            print(f"Slug: {slug}")
            
            markets = event.get('markets', [])
            if markets:
                market = markets[0]
                print(f"Market keys: {list(market.keys())}")
                print(f"Full market data: {json.dumps(market, indent=2)[:500]}")
                
                # Try different possible token ID fields
                token_id = (market.get('tokenID') or 
                           market.get('token_id') or
                           market.get('clobTokenIds', [''])[0] if isinstance(market.get('clobTokenIds'), list) else market.get('clobTokenIds'))
                
                print(f"Token ID: {token_id}")

if __name__ == "__main__":
    get_token_ids()
