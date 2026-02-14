import requests
import json

def probe_api():
    base_url = "https://gamma-api.polymarket.com"
    target_slug = "btc-updown-5m-1771105200"
    target_id = "1771105200.0" # Sometimes float?
    
    endpoints = [
        f"/events?slug={target_slug}",
        f"/events?id={target_slug}", # unlikely
        f"/markets?slug={target_slug}",
        # Try finding events that *contain* the slug pattern
        f"/events?slug=btc-updown-5m",
        f"/events?q=BTC+Up+Down",
        f"/markets?q=BTC+Up+Down"
    ]
    
    print(f"Probing for {target_slug}...")
    
    for ep in endpoints:
        url = base_url + ep
        print(f"Fetching: {url}")
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    print(f"  [SUCCESS] Found {len(data)} items!")
                    print(f"  Item 0 Slug: {data[0].get('slug')}")
                    print(f"  Item 0 ID: {data[0].get('id')}")
                    # Print markets inside event
                    if 'markets' in data[0]:
                        for m in data[0]['markets']:
                            print(f"    Market: {m.get('question')} (ID: {m.get('id')})")
                            print(f"    Active: {m.get('active')}")
                            print(f"    End: {m.get('end_date_iso')}")
                elif isinstance(data, dict) and data.get('id'):
                     print(f"  [SUCCESS] Found 1 item!")
                     print(f"  Slug: {data.get('slug')}")
                else:
                     print("  [EMPTY] Response OK but no data.")
            else:
                print(f"  [FAIL] Status {resp.status_code}")
        except Exception as e:
            print(f"  [ERROR] {e}")
            
    # Try fetching events and looking specifically for "5m" in slug
    print("-" * 30)
    print("Listing recent events to find pattern...")
    try:
        url = base_url + "/events?limit=20&active=true"
        resp = requests.get(url)
        events = resp.json()
        for e in events:
            slug = e.get('slug', '')
            if 'btc' in slug or 'updown' in slug:
                print(f"Event: {e.get('title')} | Slug: {slug}")
    except:
        pass

if __name__ == "__main__":
    probe_api()
