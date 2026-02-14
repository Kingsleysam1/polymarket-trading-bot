"""
Bot State Manager - Shared state between bot and web dashboard
"""
import time
import json
from datetime import datetime
from threading import Lock


class BotStateManager:
    """Thread-safe state manager for sharing bot data with web dashboard"""
    
    def __init__(self):
        self.lock = Lock()
        self.state = {
            "status": "initializing",
            "current_market": None,
            "last_update": time.time(),
            "open_positions": [],
            "recent_trades": [],
            "performance": {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "net_profit": 0.0,
                "win_rate": 0.0,
                "uptime_seconds": 0
            },
            "current_spread": None,
            "last_opportunity": None,
            "errors": []
        }
        self.start_time = time.time()
    
    def update_status(self, status: str):
        """Update bot status"""
        with self.lock:
            self.state["status"] = status
            self.state["last_update"] = time.time()
    
    def update_market(self, market_data: dict):
        """Update current market information"""
        with self.lock:
            self.state["current_market"] = {
                "question": market_data.get("question", "Unknown"),
                "market_id": market_data.get("id", ""),
                "end_time": market_data.get("end_date_iso", ""),
                "updated_at": datetime.now().isoformat()
            }
            self.state["last_update"] = time.time()
    
    def update_spread(self, spread_data: dict):
        """Update current spread information"""
        with self.lock:
            self.state["current_spread"] = spread_data
            self.state["last_update"] = time.time()
    
    def add_position(self, position_data: dict):
        """Add a new open position"""
        with self.lock:
            self.state["open_positions"].append({
                **position_data,
                "opened_at": datetime.now().isoformat()
            })
            self.state["last_update"] = time.time()
    
    def remove_position(self, position_id: str, profit: float):
        """Close a position and record trade"""
        with self.lock:
            # Remove from open positions
            self.state["open_positions"] = [
                p for p in self.state["open_positions"] 
                if p.get("position_id") != position_id
            ]
            
            # Add to recent trades
            trade = {
                "position_id": position_id,
                "profit": profit,
                "closed_at": datetime.now().isoformat(),
                "result": "win" if profit > 0 else "loss"
            }
            self.state["recent_trades"].insert(0, trade)
            
            # Keep only last 50 trades
            self.state["recent_trades"] = self.state["recent_trades"][:50]
            
            # Update performance
            self.state["performance"]["total_trades"] += 1
            if profit > 0:
                self.state["performance"]["winning_trades"] += 1
            else:
                self.state["performance"]["losing_trades"] += 1
            
            self.state["performance"]["net_profit"] += profit
            
            total = self.state["performance"]["total_trades"]
            wins = self.state["performance"]["winning_trades"]
            self.state["performance"]["win_rate"] = wins / total if total > 0 else 0
            
            self.state["last_update"] = time.time()
    
    def log_opportunity(self, opportunity_data: dict):
        """Log last detected opportunity"""
        with self.lock:
            self.state["last_opportunity"] = {
                **opportunity_data,
                "detected_at": datetime.now().isoformat()
            }
            self.state["last_update"] = time.time()
    
    def add_error(self, error_msg: str):
        """Log an error"""
        with self.lock:
            error = {
                "message": error_msg,
                "timestamp": datetime.now().isoformat()
            }
            self.state["errors"].insert(0, error)
            # Keep only last 20 errors
            self.state["errors"] = self.state["errors"][:20]
            self.state["last_update"] = time.time()
    
    def get_state(self) -> dict:
        """Get current bot state (thread-safe)"""
        with self.lock:
            # Calculate uptime
            self.state["performance"]["uptime_seconds"] = int(time.time() - self.start_time)
            return json.loads(json.dumps(self.state))  # Deep copy


# Global instance
bot_state = BotStateManager()
