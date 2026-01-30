"""Hybrid ML + Rule-based pricing engine."""
import numpy as np
import pandas as pd
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import joblib
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

from app.models.pricing import InternalData, MarketData, PriceRecommendationResponse
from app.ml.features import FeatureEngineer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HybridPricingModel:
    """
    Hybrid pricing model combining ML and rule-based approaches.
    
    - Uses LightGBM for complex pattern recognition
    - Falls back to rules when confidence is low
    - Provides SHAP-based explanations
    """
    
    # Confidence thresholds
    LOW_CONFIDENCE_THRESHOLD = 0.3
    MEDIUM_CONFIDENCE_THRESHOLD = 0.6
    
    # Rule-based weights
    HIGH_SELL_THROUGH_THRESHOLD = 0.7
    LOW_SELL_THROUGH_THRESHOLD = 0.4
    
    def __init__(self, model_path: Optional[str] = None):
        """Initialize hybrid model."""
        self.feature_engineer = FeatureEngineer()
        self.model: Optional[lgb.LGBMRegressor] = None
        self.model_loaded = False
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
        else:
            logger.info("No pre-trained model found. Will use rule-based approach.")
    
    def train(self, csv_path: str, output_path: str = "models/pricing_model.pkl") -> Dict[str, float]:
        """
        Train ML model on historical data.
        
        Args:
            csv_path: Path to training CSV
            output_path: Where to save trained model
            
        Returns:
            Training metrics
        """
        logger.info(f"Training ML model on {csv_path}")
        
        # Load data
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} records")
        
        # Prepare training data
        X, y = self._prepare_training_data(df)
        
        if len(X) < 50:
            logger.warning("Not enough training data for ML model. Need at least 50 samples.")
            return {}
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # Train LightGBM model
        self.model = lgb.LGBMRegressor(
            n_estimators=100,
            learning_rate=0.05,
            max_depth=5,
            num_leaves=31,
            min_child_samples=20,
            random_state=42,
            verbose=-1
        )
        
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)]
        )
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        metrics = {
            'mae': mae,
            'r2': r2,
            'train_samples': len(X_train),
            'test_samples': len(X_test)
        }
        
        logger.info(f"Model trained: MAE=${mae:.2f}, R²={r2:.3f}")
        
        # Save model
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, output_path)
        logger.info(f"Model saved to {output_path}")
        
        self.model_loaded = True
        
        return metrics
    
    def _prepare_training_data(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and target from CSV."""
        features_list = []
        targets = []
        
        # Group by brand/category to simulate items
        grouped = df.groupby(['brand', 'category', 'subcategory'])
        
        for (brand, category, subcategory), group in grouped:
            if len(group) < 5:  # Skip small groups
                continue
            
            # Create synthetic internal data
            sold_items = group[group['sold_date'].notna()]
            
            if len(sold_items) == 0:
                continue
            
            internal_data = InternalData(
                internal_price=float(sold_items['sold_price'].mean()),
                sell_through_rate=float(len(sold_items) / len(group)),
                days_on_shelf=int(group['days_to_sell'].mean()) if group['days_to_sell'].notna().any() else 30,
                category=category,
                sample_size=len(group),
                metadata={}
            )
            
            # Simulate market data (using price variance)
            from datetime import datetime
            market_data = MarketData(
                median_price=float(sold_items['sold_price'].median()),
                average_price=float(sold_items['sold_price'].mean()),
                min_price=float(sold_items['sold_price'].min()),
                max_price=float(sold_items['sold_price'].max()),
                sample_size=len(sold_items),
                timestamp=datetime.utcnow(),
                active_listings_count=len(sold_items),
                sold_listings_count=len(sold_items),
                low_confidence=False,
                metadata={}
            )
            
            # Extract features
            features = self.feature_engineer.extract_features(
                market_data=market_data,
                internal_data=internal_data,
                search_term=f"{brand} {category}"
            )
            
            feature_array = self.feature_engineer.features_to_array(features)
            features_list.append(feature_array[0])
            
            # Target: actual sold price (revenue-optimized)
            target = float(sold_items['sold_price'].mean())
            targets.append(target)
        
        X = np.array(features_list)
        y = np.array(targets)
        
        logger.info(f"Prepared {len(X)} training samples with {X.shape[1]} features")
        
        return X, y
    
    @staticmethod
    def load_model(model_path: str) -> 'HybridPricingModel':
        """Load pre-trained model.
        
        Args:
            model_path: Path to saved model pickle file
            
        Returns:
            Loaded HybridPricingModel instance
        """
        try:
            model_instance = HybridPricingModel()
            model_instance.model = joblib.load(model_path)
            model_instance.model_loaded = True
            logger.info(f"Loaded ML model from {model_path}")
            return model_instance
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def predict(
        self,
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData],
        upc: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Generate price recommendation using hybrid approach.
        
        Decision flow:
        1. Extract features
        2. Assess confidence
        3. If confidence < threshold OR no ML model → Use rules
        4. Else → Use ML model
        5. Add explanation
        
        Args:
            market_data: Market pricing data
            internal_data: Internal sales data
            upc: Product identifier (optional)
            
        Returns:
            Dictionary with prediction results
        """
        # Extract features
        features = self.feature_engineer.extract_features(
            market_data=market_data,
            internal_data=internal_data,
            search_term=upc
        )
        
        confidence_score = int(features['price_confidence'] * 100)
        
        # Decide on method
        use_ml = (
            self.model_loaded and 
            features['price_confidence'] >= self.LOW_CONFIDENCE_THRESHOLD and
            features['has_internal_data'] == 1.0
        )
        
        if use_ml:
            # ML-based prediction
            result = self._ml_predict(upc, features, market_data, internal_data)
        else:
            # Rule-based fallback
            result = self._rule_based_predict(upc, features, market_data, internal_data)
        
        # Convert to dictionary
        return {
            "recommended_price": result.recommended_price,
            "internal_weight": result.internal_vs_market_weighting,
            "confidence": result.confidence_score / 100.0,
            "rationale": result.rationale,
            "warnings": result.warnings,
            "feature_importance": self.get_feature_importance(),
            "method": "ml" if use_ml else "rule_based"
        }
    
    def _ml_predict(
        self,
        upc: str,
        features: Dict[str, float],
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData]
    ) -> PriceRecommendationResponse:
        """ML-based prediction."""
        feature_array = self.feature_engineer.features_to_array(features)
        predicted_price = float(self.model.predict(feature_array)[0])
        
        # Get feature importance
        feature_names = self.feature_engineer.get_feature_names()
        importance = self.model.feature_importances_
        top_features = sorted(
            zip(feature_names, importance),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # Build rationale
        rationale_parts = [
            f"ML model prediction: ${predicted_price:.2f}",
            f"Confidence: {features['price_confidence']:.0%}",
            "Top factors: " + ", ".join([f"{name} ({imp:.2f})" for name, imp in top_features])
        ]
        
        if internal_data:
            rationale_parts.append(
                f"Internal: ${internal_data.internal_price:.2f}, "
                f"sell-through: {internal_data.sell_through_rate:.2f}"
            )
        
        if market_data and market_data.sample_size > 0:
            rationale_parts.append(
                f"Market: ${market_data.median_price:.2f} median from {market_data.sample_size} listings"
            )
        
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=predicted_price,
            internal_vs_market_weighting=0.5,  # Not applicable for ML
            confidence_score=int(features['price_confidence'] * 100),
            rationale=" | ".join(rationale_parts) + " | Method: ML (LightGBM)",
            market_data=market_data,
            internal_data=internal_data,
            warnings=[]
        )
    
    def _rule_based_predict(
        self,
        upc: str,
        features: Dict[str, float],
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData]
    ) -> PriceRecommendationResponse:
        """Rule-based fallback prediction."""
        warnings = []
        
        # No data scenario
        if not market_data and not internal_data:
            return PriceRecommendationResponse(
                upc=upc,
                recommended_price=0.0,
                internal_vs_market_weighting=0.5,
                confidence_score=0,
                rationale="No market or internal data available. Method: Rules (Fallback)",
                warnings=["No data available for this UPC"]
            )
        
        # Calculate weights based on data quality
        if internal_data and market_data and market_data.sample_size > 0:
            # Both sources available
            sell_through = internal_data.sell_through_rate
            
            if sell_through > self.HIGH_SELL_THROUGH_THRESHOLD:
                internal_weight = 0.75
            elif sell_through < self.LOW_SELL_THROUGH_THRESHOLD:
                internal_weight = 0.40
            else:
                internal_weight = 0.60
            
            market_weight = 1.0 - internal_weight
            
            recommended_price = (
                internal_data.internal_price * internal_weight +
                market_data.median_price * market_weight
            )
            
            rationale = (
                f"Rule-based weighted average: {internal_weight:.0%} internal, "
                f"{market_weight:.0%} market. Internal: ${internal_data.internal_price:.2f}, "
                f"Market: ${market_data.median_price:.2f}. Method: Rules"
            )
            
        elif internal_data:
            # Internal only
            recommended_price = internal_data.internal_price
            internal_weight = 1.0
            warnings.append("No market data. Using internal data only.")
            rationale = f"Internal data only: ${recommended_price:.2f}. Method: Rules"
            
        else:
            # Market only
            recommended_price = market_data.median_price
            internal_weight = 0.0
            warnings.append("No internal data. Using market data only.")
            rationale = f"Market data only: ${recommended_price:.2f}. Method: Rules"
        
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=recommended_price,
            internal_vs_market_weighting=internal_weight,
            confidence_score=int(features['price_confidence'] * 100),
            rationale=rationale,
            market_data=market_data,
            internal_data=internal_data,
            warnings=warnings
        )
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """Get feature importance from trained model."""
        if not self.model_loaded:
            return None
        
        feature_names = self.feature_engineer.get_feature_names()
        importance = self.model.feature_importances_
        
        return dict(zip(feature_names, importance))
