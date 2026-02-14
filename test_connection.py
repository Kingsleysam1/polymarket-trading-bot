"""
Test API Connection and Configuration
Run this to verify your setup before starting the bot
"""
import sys
from py_clob_client.client import ClobClient

try:
    import config
    from utils import setup_logger
    from market_monitor import MarketMonitor
    
    logger = setup_logger("ConnectionTest")
    
    print("=" * 60)
    print("🧪 TESTING POLYMARKET BOT SETUP")
    print("=" * 60)
    
    # Test 1: Configuration
    print("\n1️⃣ Testing Configuration...")
    print(f"   ✓ Private key configured: {'Yes' if config.POLYGON_PRIVATE_KEY else 'No'}")
    print(f"   ✓ Chain ID: {config.POLYGON_CHAIN_ID}")
    print(f"   ✓ Order size: ${config.ORDER_SIZE_USD}")
    print(f"   ✓ Min spread: ${config.MIN_SPREAD_TO_TRADE}")
    
    if not config.POLYGON_PRIVATE_KEY:
        print("   ❌ ERROR: No private key configured")
        print("   Please add POLYGON_PRIVATE_KEY to your .env file")
        sys.exit(1)
    
    # Test 2: CLOB Client Initialization
    print("\n2️⃣ Testing CLOB Client Connection...")
    try:
        client = ClobClient(
            host=config.CLOB_API_URL,
            key=config.POLYGON_PRIVATE_KEY,
            chain_id=config.POLYGON_CHAIN_ID,
            signature_type=config.SIGNATURE_TYPE,
            funder=config.FUNDER_ADDRESS if config.FUNDER_ADDRESS else None
        )
        print("   ✓ CLOB client initialized successfully")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        sys.exit(1)
    
    # Test 3: Market Monitor
    print("\n3️⃣ Testing Market Monitor...")
    try:
        monitor = MarketMonitor()
        print("   ✓ Market monitor initialized")
        
        print("   Searching for active 5-minute Bitcoin markets...")
        market = monitor.find_current_5min_btc_market()
        
        if market:
            print(f"   ✓ Found market: {market.get('question', 'Unknown')}")
            yes_token, no_token = monitor.get_market_tokens(market)
            print(f"   ✓ YES token: {yes_token}")
            print(f"   ✓ NO token: {no_token}")
        else:
            print("   ⚠️  No active 5-minute Bitcoin markets found right now")
            print("      This is normal - markets may not always be active")
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Test 4: Order Book Access
    if market and yes_token:
        print("\n4️⃣ Testing Order Book Access...")
        try:
            yes_book = client.get_order_book(yes_token)
            print(f"   ✓ Retrieved order book for YES token")
            
            if yes_book.get("asks"):
                best_ask = yes_book["asks"][0]
                print(f"   ✓ Best ask: ${float(best_ask['price']):.4f}")
            
            if yes_book.get("bids"):
                best_bid = yes_book["bids"][0]
                print(f"   ✓ Best bid: ${float(best_bid['price']):.4f}")
                
        except Exception as e:
            print(f"   ⚠️  Could not fetch order book: {e}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Approve token allowances: python bot.py --approve-tokens")
    print("2. Test in dry-run mode: python bot.py --dry-run")
    print("3. Start live trading: python bot.py")
    print("\nRemember to start with small order sizes!")
    
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
