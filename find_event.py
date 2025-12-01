import requests

def search_markets():
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "limit": 50,
        "q": "Trump",
        "active": "true"
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        print(f"Found {len(data)} markets.")
        
        for market in data:
            question = market.get('question', '')
            if 'March' in question:
                print(f"ID: {market.get('id')}")
                print(f"Question: {question}")
                print(f"Price: {market.get('outcomePrices')}")
                print("-" * 20)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search_markets()
