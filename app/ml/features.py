"""Feature engineering for ML pricing model."""
import pandas as pd
import numpy as np
from typing import Dict, Optional
from app.models.pricing import MarketData, InternalData


class FeatureEngineer:
    """Extract and engineer features for ML model."""
    
    def __init__(self):
        """Initialize feature engineer."""
        self.category_mapping = {}
        
    def extract_features(
        self,
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData],
        search_term: str
    ) -> Dict[str, float]:
        """
        Extract features from market and internal data.
        
        Returns dictionary of features for ML model.
        """
        features = {}
        
        # Market features
        if market_data and market_data.sample_size > 0:
            features['market_median_price'] = market_data.median_price or 0.0
            features['market_min_price'] = market_data.min_price or 0.0
            features['market_max_price'] = market_data.max_price or 0.0
            features['market_sample_size'] = float(market_data.sample_size)
            features['market_price_range'] = (
                (market_data.max_price or 0.0) - (market_data.min_price or 0.0)
            )
            features['market_price_std'] = (
                features['market_price_range'] / 4.0 if features['market_price_range'] > 0 else 0.0
            )
            features['has_market_data'] = 1.0
        else:
            features['market_median_price'] = 0.0
            features['market_min_price'] = 0.0
            features['market_max_price'] = 0.0
            features['market_sample_size'] = 0.0
            features['market_price_range'] = 0.0
            features['market_price_std'] = 0.0
            features['has_market_data'] = 0.0
        
        # Internal features
        if internal_data:
            features['internal_price'] = internal_data.internal_price
            features['sell_through_rate'] = internal_data.sell_through_rate
            features['days_on_shelf'] = float(internal_data.days_on_shelf)
            features['internal_sample_size'] = float(internal_data.sample_size)
            features['has_internal_data'] = 1.0
            
            # Inventory velocity (items sold per day)
            if internal_data.days_on_shelf > 0:
                sold_items = internal_data.metadata.get('sold_items', 0)
                features['inventory_velocity'] = sold_items / max(internal_data.days_on_shelf, 1)
            else:
                features['inventory_velocity'] = 0.0
            
            # Category encoding (simplified one-hot)
            category = internal_data.category.lower()
            features['category_shoes'] = 1.0 if 'shoe' in category else 0.0
            features['category_tops'] = 1.0 if 'top' in category or 'shirt' in category else 0.0
            features['category_bottoms'] = 1.0 if 'bottom' in category or 'pant' in category else 0.0
            features['category_outerwear'] = 1.0 if 'jacket' in category or 'coat' in category else 0.0
        else:
            features['internal_price'] = 0.0
            features['sell_through_rate'] = 0.0
            features['days_on_shelf'] = 0.0
            features['internal_sample_size'] = 0.0
            features['has_internal_data'] = 0.0
            features['inventory_velocity'] = 0.0
            features['category_shoes'] = 0.0
            features['category_tops'] = 0.0
            features['category_bottoms'] = 0.0
            features['category_outerwear'] = 0.0
        
        # Interaction features
        if features['has_market_data'] == 1.0 and features['has_internal_data'] == 1.0:
            # Price comparison ratio
            if features['market_median_price'] > 0:
                features['price_vs_market_ratio'] = (
                    features['internal_price'] / features['market_median_price']
                )
            else:
                features['price_vs_market_ratio'] = 1.0
            
            # Demand signal: high sell-through + low market supply
            features['demand_signal'] = (
                features['sell_through_rate'] * 
                (1.0 / max(features['market_sample_size'], 1.0))
            )
        else:
            features['price_vs_market_ratio'] = 1.0
            features['demand_signal'] = 0.0
        
        # Data quality score
        market_quality = min(features['market_sample_size'] / 10.0, 1.0)
        internal_quality = min(features['internal_sample_size'] / 50.0, 1.0)
        features['data_quality_score'] = (market_quality + internal_quality) / 2.0
        
        # Price confidence based on data availability
        features['price_confidence'] = self._calculate_confidence(features)
        
        return features
    
    def _calculate_confidence(self, features: Dict[str, float]) -> float:
        """
        Calculate realistic confidence score based on data quality.
        
        Never returns 100% - there's always some uncertainty in pricing.
        Factors: sample size, price variance, data freshness, match quality.
        """
        confidence = 0.0
        
        # Market data confidence (max 0.45)
        if features['has_market_data'] == 1.0:
            # Base confidence from sample size (diminishing returns)
            sample_size = features['market_sample_size']
            market_conf = 0.45 * (1 - np.exp(-sample_size / 15.0))
            
            # Penalty for high price variance (unstable market)
            if features['market_median_price'] > 0:
                price_cv = features['market_price_std'] / features['market_median_price']
                if price_cv > 0.5:  # Coefficient of variation > 50%
                    market_conf *= 0.7
                elif price_cv > 0.3:
                    market_conf *= 0.85
            
            confidence += market_conf
        
        # Internal data confidence (max 0.45)
        if features['has_internal_data'] == 1.0:
            # Base confidence from sample size
            sample_size = features['internal_sample_size']
            internal_conf = 0.45 * (1 - np.exp(-sample_size / 50.0))
            
            # Adjust based on sell-through rate quality
            str_rate = features['sell_through_rate']
            if str_rate > 0.8 or str_rate < 0.2:
                # Extreme sell-through rates are less predictive
                internal_conf *= 0.9
            
            confidence += internal_conf
        
        # Small bonus for having both sources (max 0.10)
        if features['has_market_data'] == 1.0 and features['has_internal_data'] == 1.0:
            confidence += 0.10
        
        # Cap at 95% - never claim 100% certainty
        return min(confidence, 0.95)
    
    def get_feature_names(self) -> list:
        """Get ordered list of feature names."""
        return [
            'market_median_price',
            'market_min_price',
            'market_max_price',
            'market_sample_size',
            'market_price_range',
            'market_price_std',
            'has_market_data',
            'internal_price',
            'sell_through_rate',
            'days_on_shelf',
            'internal_sample_size',
            'has_internal_data',
            'inventory_velocity',
            'category_shoes',
            'category_tops',
            'category_bottoms',
            'category_outerwear',
            'price_vs_market_ratio',
            'demand_signal',
            'data_quality_score',
            'price_confidence'
        ]
    
    def features_to_array(self, features: Dict[str, float]) -> np.ndarray:
        """Convert feature dict to numpy array in correct order."""
        feature_names = self.get_feature_names()
        return np.array([features.get(name, 0.0) for name in feature_names]).reshape(1, -1)
