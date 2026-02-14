import requests
import json
from datetime import datetime

def check_markets():
    print("STARTING BROAD SEARCH FOR ACTIVE BTC MARKETS...")
    base_url = "https://gamma-api.polymarket.com/markets"
    
    found_count = 0
    
    for offset in range(0, 500, 50): # Smaller chunks of 50
        print(f"Fetching active markets offset {offset}...")
        try:
            response = requests.get(
                base_url, 
                params={"limit": 50, "active": False, "closed": False, "offset": offset},
                timeout=10
            )
            markets = response.json()
            
            if not markets:
                print("No more markets.")
                break
                
            for m in markets:
                q = m.get('question', '').lower()
                d = m.get('description', '').lower()
                s = m.get('slug', '').lower()
                market_id = m.get('id')
                end = m.get('end_date_iso')
                
                text = q + " " + d + " " + s
                
                # Check for BTC + (5 or Up or Down)
                if ("btc" in text or "bitcoin" in text):
                    # We are looking for the 'missing' market
                    print(f"Found BTC Market: {m.get('question')} (ID: {market_id})")
                    print(f"  Slug: {m.get('slug')}")
                    print(f"  End: {end}")
                    
                    if "5" in text:
                        print("  >>> HAS '5' keyword!")
                    
                    found_count += 1

        except Exception as e:
            print(f"Error on offset {offset}: {e}")
            
    print(f"Total BTC markets found in top 500: {found_count}")

if __name__ == "__main__":
    check_markets()
