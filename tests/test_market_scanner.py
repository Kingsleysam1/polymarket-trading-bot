"""
Unit Tests for Multi-Market Scanner

Tests market discovery, filtering, and token extraction.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from core.market_scanner import MultiMarketScanner


@pytest.mark.asyncio
async def test_scanner_initialization():
    """Test market scanner initialization"""
    scanner = MultiMarketScanner(
        gamma_api_url="https://gamma-api.polymarket.com",
        keywords=["BTC", "5min"],
        exclude_keywords=["test"],
        max_markets=25
    )
    
    assert scanner.max_markets == 25
    assert len(scanner.active_markets) == 0
    assert scanner.running == False


@pytest.mark.asyncio
async def test_market_filtering():
    """Test market keyword filtering"""
    scanner = MultiMarketScanner(
        gamma_api_url="https://gamma-api.polymarket.com",
        keywords=["btc", "5min"],
        exclude_keywords=["test"],
        max_markets=25
    )
    
    # Test matching market
    market1 = {
        "question": "Will BTC go up in the next 5min?",
        "description": "Bitcoin price prediction",
        "slug": "btc-5min-prediction"
    }
    assert scanner._matches_criteria(market1) == True
    
    # Test non-matching market (no timeframe)
    market2 = {
        "question": "Will BTC reach $100k?",
        "description": "Bitcoin price prediction",
        "slug": "btc-100k"
    }
    assert scanner._matches_criteria(market2) == False
    
    # Test excluded market
    market3 = {
        "question": "Test BTC 5min market",
        "description": "Test market",
        "slug": "test-btc-5min"
    }
    assert scanner._matches_criteria(market3) == False


@pytest.mark.asyncio
async def test_token_extraction():
    """Test YES/NO token extraction"""
    scanner = MultiMarketScanner(
        gamma_api_url="https://gamma-api.polymarket.com",
        keywords=["BTC"],
        exclude_keywords=[],
        max_markets=25
    )
    
    # Test with tokens array
    market = {
        "tokens": [
            {"token_id": "token_yes", "outcome": "YES"},
            {"token_id": "token_no", "outcome": "NO"}
        ]
    }
    
    yes_token, no_token = scanner._extract_tokens(market)
    assert yes_token == "token_yes"
    assert no_token == "token_no"


@pytest.mark.asyncio
async def test_get_stats():
    """Test scanner statistics"""
    scanner = MultiMarketScanner(
        gamma_api_url="https://gamma-api.polymarket.com",
        keywords=["BTC"],
        exclude_keywords=[],
        max_markets=25
    )
    
    stats = scanner.get_stats()
    
    assert "active_markets" in stats
    assert "max_markets" in stats
    assert "running" in stats
    assert stats["active_markets"] == 0
    assert stats["max_markets"] == 25


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
