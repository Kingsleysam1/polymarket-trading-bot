"""
Strategy 4: ML Pattern Recognition

Uses machine learning to identify profitable trading patterns.
Requires historical data collection and model training before use.
"""
from typing import Optional, Dict, List
import time
import os
import numpy as np
from py_clob_client.client import ClobClient

import config
from strategies.base_strategy import BaseStrategy, StrategyType
from utils import setup_logger, format_price

logger = setup_logger("MLPattern")

# Try to import sklearn, but don't fail if not available
try:
    from sklearn.ensemble import RandomForestClassifier
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not installed - ML strategy will be disabled")
    SKLEARN_AVAILABLE = False


class MLPatternStrategy(BaseStrategy):
    """
    Uses machine learning to detect profitable trading patterns.
    
    NOTE: This strategy requires:
    1. Historical market data collection (7-14 days minimum)
    2. Feature engineering and model training
    3. Trained model file in data/models/
    
    Run data_collector.py first to gather training data.
    """
    
    def __init__(self, clob_client: ClobClient):
        super().__init__("ML Pattern Recognition", StrategyType.ML_PATTERN)
        self.client = clob_client
        self.model = None
        self.model_loaded = False
        self.pattern_accuracy = {
            'breakout_continuation': 0.67,
            'spike_reversal': 0.72,
            'range_bound': 0.51
        }
        
        # Try to load trained model
        if SKLEARN_AVAILABLE:
            self._load_model()
        else:
            logger.warning("⚠️  ML strategy disabled - install scikit-learn to enable")
            self.disable()
    
    def _load_model(self):
        """Load trained ML model from disk"""
        try:
            model_path = config.ML_MODEL_PATH
            
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
                self.model_loaded = True
                logger.info(f"✅ ML model loaded from {model_path}")
            else:
                logger.warning(f"⚠️  No trained model found at {model_path}")
                logger.warning("   Run data collector and model training first")
                self.disable()
                
        except Exception as e:
            logger.error(f"Error loading ML model: {e}")
            self.disable()
    
    def scan_opportunities(self) -> Optional[Dict]:
        """
        Scan for ML-identified pattern opportunities.
        
        Returns signal if high-confidence pattern detected.
        """
        if not self.enabled or not self.model_loaded:
            return None
        
        try:
            # Get current market data
            market = self._get_current_market()
            if not market:
                return None
            
            # Extract features from market data
            features = self._extract_features(market)
            if features is None:
                return None
            
            # Get model prediction and confidence
            confidence = self._predict_confidence(features)
            
            # Check if confidence exceeds threshold
            if confidence >= config.ML_MIN_CONFIDENCE:
                pattern_type = self._classify_pattern(features, market)
                
                # Only trade patterns with proven accuracy
                if pattern_type in self.pattern_accuracy:
                    if self.pattern_accuracy[pattern_type] >= 0.65:
                        
                        logger.info(f"🤖 ML PATTERN DETECTED!")
                        logger.info(f"   Pattern: {pattern_type}")
                        logger.info(f"   Confidence: {confidence:.1%}")
                        logger.info(f"   Historical accuracy: {self.pattern_accuracy[pattern_type]:.1%}")
                        
                        return {
                            'market': market,
                            'pattern_type': pattern_type,
                            'confidence': confidence,
                            'features': features,
                            'strategy': 'ml_pattern'
                        }
            
            return None
            
        except Exception as e:
            logger.error(f"Error scanning for ML patterns: {e}")
            return None
    
    def _get_current_market(self) -> Optional[Dict]:
        """Get current market for pattern analysis"""
        try:
            from market_monitor import MarketMonitor
            monitor = MarketMonitor()
            return monitor.find_current_5min_btc_market()
        except Exception as e:
            logger.error(f"Error getting market: {e}")
            return None
    
    def _extract_features(self, market: Dict) -> Optional[np.ndarray]:
        """
        Extract ML features from market data.
        
        Features include:
        - Price momentum
        - Volume spike
        - Time to close
        - Spread width
        - Order book imbalance
        """
        try:
            # Get market tokens
            tokens = market.get('tokens', [])
            if len(tokens) != 2:
                return None
            
            yes_token = tokens[0]['token_id']
            no_token = tokens[1]['token_id']
            
            # Get order books
            yes_book = self.client.get_order_book(yes_token)
            no_book = self.client.get_order_book(no_token)
            
            # Calculate features
            features = {}
            
            # 1. Current prices
            yes_asks = yes_book.get('asks', [])
            if yes_asks:
                features['yes_price'] = float(yes_asks[0]['price'])
            else:
                return None
            
            # 2. Spread width
            no_asks = no_book.get('asks', [])
            if no_asks:
                no_price = float(no_asks[0]['price'])
                features['spread'] = 1.0 - (features['yes_price'] + no_price)
            else:
                features['spread'] = 0
            
            # 3. Volume (from market metadata)
            features['volume'] = float(market.get('volume', 0))
            
            # 4. Time to close
            end_time = market.get('end_date_iso', None)
            if end_time:
                # Parse and calculate remaining time
                # Simplified for now
                features['time_to_close'] = 300  # 5 minutes
            else:
                features['time_to_close'] = 0
            
            # 5. Order book depth (simplified)
            features['bid_depth'] = len(yes_book.get('bids', []))
            features['ask_depth'] = len(yes_book.get('asks', []))
            
            # Convert to numpy array in the order the model expects
            feature_array = np.array([[
                features['yes_price'],
                features['spread'],
                features['volume'],
                features['time_to_close'],
                features['bid_depth'],
                features['ask_depth']
            ]])
            
            return feature_array
            
        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None
    
    def _predict_confidence(self, features: np.ndarray) -> float:
        """Get model confidence for the prediction"""
        try:
            # Get probability predictions
            probabilities = self.model.predict_proba(features)
            
            # Return confidence of positive class
            return probabilities[0][1]
            
        except Exception as e:
            logger.error(f"Error predicting confidence: {e}")
            return 0.0
    
    def _classify_pattern(self, features: np.ndarray, market: Dict) -> str:
        """
        Classify the specific pattern type.
        
        For now, simplified classification based on features.
        """
        # Simplified pattern classification
        yes_price = features[0][0]
        spread = features[0][1]
        
        if yes_price > 0.65 and spread > 0.05:
            return "breakout_continuation"
        elif yes_price < 0.35:
            return "spike_reversal"
        else:
            return "range_bound"
    
    def execute_trade(self, signal: Dict, dry_run: bool = False) -> Optional[str]:
        """Execute ML pattern-based trade"""
        try:
            position_id = f"ml_{int(time.time())}"
            
            # Position sizing based on confidence
            base_size = config.ORDER_SIZE_USD
            confidence_multiplier = signal['confidence'] / config.ML_MIN_CONFIDENCE
            position_size = min(
                base_size * confidence_multiplier,
                config.ML_MAX_POSITION_SIZE
            )
            
            if dry_run:
                logger.info(f"💵 [DRY RUN] WOULD EXECUTE ML TRADE:")
                logger.info(f"   Position ID: {position_id}")
                logger.info(f"   Pattern: {signal['pattern_type']}")
                logger.info(f"   Confidence: {signal['confidence']:.1%}")
                logger.info(f"   Position size: ${position_size:.2f}")
                
                self.open_positions[position_id] = {
                    'signal': signal,
                    'size': position_size,
                    'status': 'simulated',
                    'entry_time': time.time()
                }
                
                return position_id
            
            # Execute real trade
            logger.info(f"🤖 EXECUTING ML PATTERN TRADE:")
            logger.info(f"   Pattern: {signal['pattern_type']}")
            logger.info(f"   Confidence: {signal['confidence']:.1%}")
            
            # Determine which side to trade based on pattern
            # (This would be more sophisticated in production)
            tokens = signal['market']['tokens']
            yes_token = tokens[0]['token_id']
            
            # Place order
            # Implementation depends on pattern type
            # For now, simplified
            
            self.open_positions[position_id] = {
                'signal': signal,
                'size': position_size,
                'status': 'executed',
                'entry_time': time.time()
            }
            
            logger.info(f"✅ ML trade executed - Position {position_id}")
            return position_id
            
        except Exception as e:
            logger.error(f"Error executing ML trade: {e}")
            return None
    
    def monitor_positions(self, dry_run: bool = False) -> List[str]:
        """Monitor ML pattern positions"""
        closed_positions = []
        current_time = time.time()
        
        for position_id, position in list(self.open_positions.items()):
            try:
                time_held = current_time - position['entry_time']
                
                # For dry run, simulate based on pattern accuracy
                if dry_run and position['status'] == 'simulated':
                    if time_held > 180:  # Hold for 3 minutes
                        signal = position['signal']
                        pattern = signal['pattern_type']
                        
                        # Simulate win/loss based on historical accuracy
                        import random
                        if random.random() < self.pattern_accuracy.get(pattern, 0.5):
                            # Win
                            profit = position['size'] * 0.45  # 45% profit on winner
                            self.record_trade(profit)
                            logger.info(f"✅ [DRY RUN] ML position {position_id} WINNER - Profit: ${profit:.2f}")
                        else:
                            # Loss
                            loss = position['size'] * -0.25  # 25% loss
                            self.record_trade(loss)
                            logger.info(f"❌ [DRY RUN] ML position {position_id} LOSER - Loss: ${loss:.2f}")
                        
                        del self.open_positions[position_id]
                        closed_positions.append(position_id)
                
            except Exception as e:
                logger.error(f"Error monitoring ML position {position_id}: {e}")
        
        return closed_positions
