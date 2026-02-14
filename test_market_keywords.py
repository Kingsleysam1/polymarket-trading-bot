import unittest
from market_monitor import MarketMonitor
import config

class TestMarketMonitor(unittest.TestCase):
    def setUp(self):
        self.monitor = MarketMonitor()
        
    def test_5m_keyword_matching(self):
        # Case 1: Standard "5 min" (should already work)
        market_standard = {
            "question": "Will BTC go up in 5 min?",
            "description": "Standard 5 minute market"
        }
        self.assertTrue(self.monitor._is_5min_btc_market(market_standard), 
                        "Failed to match standard '5 min' keyword")
        
        # Case 2: "5m" in slug style (The fix)
        market_5m_slug = {
            "question": "BTC Up/Down 5m",
            "description": "Bitcoin price action"
        }
        self.assertTrue(self.monitor._is_5min_btc_market(market_5m_slug), 
                        "Failed to match '5m' keyword")
        
        # Case 3: "5 m" separated
        market_5_m = {
            "question": "Bitcoin 5 m prediction",
            "description": "Price check"
        }
        self.assertTrue(self.monitor._is_5min_btc_market(market_5_m), 
                        "Failed to match '5 m' keyword")

        # Case 4: No time keyword (Should fail)
        market_no_time = {
            "question": "Will Bitcoin go up?",
            "description": "General prediction"
        }
        self.assertFalse(self.monitor._is_5min_btc_market(market_no_time), 
                         "Incorrectly matched market without time keyword")

        # Case 5: No BTC keyword (Should fail)
        market_no_btc = {
            "question": "Will ETH go up in 5m?",
            "description": "Ethereum 5 minute"
        }
        self.assertFalse(self.monitor._is_5min_btc_market(market_no_btc), 
                         "Incorrectly matched market without BTC keyword")

if __name__ == '__main__':
    unittest.main()
