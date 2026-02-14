"""
Unit tests for strategy logic
"""
import pytest
from unittest.mock import Mock, MagicMock
from strategy import MakerStrategy
from utils import calculate_spread, calculate_profit_potential


def test_calculate_spread():
    """Test spread calculation"""
    # Perfect spread (costs $1.00)
    assert calculate_spread(0.50, 0.50) == 0.0
    
    # Wide spread (costs $0.90)
    assert calculate_spread(0.52, 0.38) == 0.10
    
    # Narrow spread (costs $0.98)
    assert calculate_spread(0.49, 0.49) == 0.02


def test_calculate_profit_potential():
    """Test profit calculation"""
    # $0.10 spread on $10 order with no fees
    profit = calculate_profit_potential(0.10, 10.0, fee_rate=0.0)
    assert profit == 1.0
    
    # $0.05 spread on $5 order
    profit = calculate_profit_potential(0.05, 5.0, fee_rate=0.0)
    assert profit == 0.25


def test_analyze_opportunity_no_spread():
    """Test that no signal is generated when spread is too narrow"""
    mock_client = Mock()
    
    # Mock order books with narrow spread
    mock_client.get_order_book.side_effect = [
        {
            "asks": [{"price": "0.50"}],
            "bids": [{"price": "0.49"}]
        },
        {
            "asks": [{"price": "0.49"}],
            "bids": [{"price": "0.48"}]
        }
    ]
    
    strategy = MakerStrategy(mock_client)
    signal = strategy.analyze_opportunity("token1", "token2")
    
    # Should return None because combined cost is $0.99 (spread = $0.01 < MIN_SPREAD)
    assert signal is None


def test_analyze_opportunity_wide_spread():
    """Test that signal is generated when spread is wide enough"""
    mock_client = Mock()
    
    # Mock order books with wide spread
    mock_client.get_order_book.side_effect = [
        {
            "asks": [{"price": "0.52"}],
            "bids": [{"price": "0.51"}]
        },
        {
            "asks": [{"price": "0.40"}],
            "bids": [{"price": "0.39"}]
        }
    ]
    
    strategy = MakerStrategy(mock_client)
    signal = strategy.analyze_opportunity("token1", "token2")
    
    # Should return signal because spread is $0.08 (> MIN_SPREAD of $0.05)
    assert signal is not None
    assert signal["spread"] == 0.08
    assert signal["yes_token_id"] == "token1"
    assert signal["no_token_id"] == "token2"


if __name__ == "__main__":
    print("Running strategy tests...")
    test_calculate_spread()
    print("✓ Spread calculation tests passed")
    
    test_calculate_profit_potential()
    print("✓ Profit calculation tests passed")
    
    test_analyze_opportunity_no_spread()
    print("✓ No spread opportunity test passed")
    
    test_analyze_opportunity_wide_spread()
    print("✓ Wide spread opportunity test passed")
    
    print("\n✅ All tests passed!")
