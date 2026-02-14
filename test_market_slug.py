import unittest
from market_monitor import MarketMonitor
import config

class TestMarketMonitorSlug(unittest.TestCase):
    def setUp(self):
        self.monitor = MarketMonitor()
        
    def test_slug_matching(self):
        # Case 1: "5m" in slug only (The target case)
        market_slug_only = {
            "question": "Bitcoin Up or Down",
            "description": "Expires at 4:45 PM",
            "slug": "btc-updown-5m-1771105200"
        }
        self.assertTrue(self.monitor._is_5min_btc_market(market_slug_only), 
                        "Failed to match '5m' in slug")
        
        # Case 2: No 5m anywhere
        market_none = {
             "question": "Bitcoin Up or Down",
             "description": "Expires at 4:45 PM",
             "slug": "btc-updown-daily-1771105200"
        }
        self.assertFalse(self.monitor._is_5min_btc_market(market_none),
                         "Incorrectly matched market with no 5m keyword")

if __name__ == '__main__':
    unittest.main()
