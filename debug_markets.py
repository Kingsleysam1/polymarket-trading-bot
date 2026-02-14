
import config
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds

def debug_markets():
    print("Initializing Client...")
    host = config.CLOB_API_URL
    key = config.POLYGON_PRIVATE_KEY
    chain_id = config.POLYGON_CHAIN_ID
    client = ClobClient(host=host, key=key, chain_id=chain_id, signature_type=config.SIGNATURE_TYPE)

    print(f"Fetching markets from {config.GAMMA_API_URL}...")
    # The SDK uses the gamma-api under the hood for some calls, or we might need to hit it directly if the SDK doesn't expose a broad enough search.
    # config.py has MARKET_KEYWORDS = ["5 min", "BTC", "Bitcoin"]
    
    # Let's try to list markets using the ClobClient if possible, or just standard requests if the SDK is limited for searching.
    # Looking at market_monitor.py might be better first, but let's try to mimic what it does.
    
    # We'll use requests to hit the Gamma API directly as market_monitor.py likely does (or should).
    import requests
    
    # Try the exact logic from MarketMonitor (guessing based on common patterns, but I should verify market_monitor.py content first)
    # Actually, let's look at `market_monitor.py` first to see exactly what it does.
    pass

if __name__ == "__main__":
    # creating a simple script to fetch and print ALL BTC markets
    import requests
    import json
    
    url = "https://gamma-api.polymarket.com/events?limit=20&active=true&closed=false&parent_slug=btc-price-5-min"
    # The URL user gave is https://polymarket.com/event/btc-updown-5m-1771105200
    # "Up/Down" might be the key difference if we are looking for "Price"
    
    print(f"Querying: {url}")
    try:
        response = requests.get(url)
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Found {len(data)} events")
        for event in data:
            print(f"- {event.get('title')} (ID: {event.get('id')})")
            # print active markets within event
            for market in event.get('markets', []):
                 print(f"  > Market: {market.get('question')} (End: {market.get('end_date_iso')})")
    except Exception as e:
        print(f"Error: {e}")

    print("-" * 20)
    print("Trying search for 'BTC'...")
    url_search = "https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=50&slug=btc"
    try:
        response = requests.get(url_search)
        data = response.json()
        print(f"Found {len(data)} markets via search")
        for market in data:
            # check keywords
             print(f"  > {market.get('question')} | End: {market.get('end_date_iso')}")
    except Exception as e:
        print(f"Error: {e}")
