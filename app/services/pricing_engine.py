"""Pricing recommendation engine with ML hybrid approach."""
from typing import Optional, Dict, Any
from pathlib import Path
from app.models.pricing import (
    InternalData, 
    MarketData, 
    PriceRecommendationResponse
)
from app.ml.model import HybridPricingModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PricingEngine:
    """
    Hybrid ML + Rule-based pricing engine.
    
    Combines ML predictions with rule-based fallbacks for optimal pricing.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the pricing engine.
        
        Args:
            model_path: Path to trained ML model (optional)
        """
        self.model = None
        self.use_ml = False
        
        # Try to load ML model if path provided or default exists
        if model_path is None:
            model_path = "models/pricing_model.pkl"
        
        model_file = Path(model_path)
        if model_file.exists():
            try:
                self.model = HybridPricingModel.load_model(str(model_file))
                self.use_ml = True
                logger.info(f"✅ Loaded ML model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load ML model: {e}. Using rule-based fallback.")
                self.use_ml = False
        else:
            logger.info(f"ML model not found at {model_path}. Using rule-based approach.")

    
    def generate_recommendation(
        self,
        upc: str,
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData]
    ) -> PriceRecommendationResponse:
        """
        Generate a pricing recommendation using ML or rules.
        
        Args:
            upc: UPC code
            market_data: Market pricing data from eBay
            internal_data: Internal sales data
            
        Returns:
            PriceRecommendationResponse with recommendation
        """
        warnings = []
        
        # Check if we have any data
        if not market_data and not internal_data:
            return self._no_data_response(upc)
        
        # Use ML model if available
        if self.use_ml and self.model:
            try:
                result = self.model.predict(market_data, internal_data)
                
                # Convert to response format
                return PriceRecommendationResponse(
                    upc=upc,
                    recommended_price=result["recommended_price"],
                    internal_vs_market_weighting=result.get("internal_weight", 0.5),
                    confidence_score=int(result["confidence"] * 100),
                    rationale=result["rationale"],
                    market_data=market_data,
                    internal_data=internal_data,
                    warnings=result.get("warnings", []),
                    feature_importance=result.get("feature_importance"),
                    prediction_method=result.get("method", "unknown")
                )
            except Exception as e:
                logger.error(f"ML prediction failed: {e}. Falling back to rules.")
                warnings.append(f"ML prediction failed: {str(e)}")
        
        # Fallback to rule-based approach
        return self._rule_based_recommendation(upc, market_data, internal_data, warnings)
    
    def _rule_based_recommendation(
        self,
        upc: str,
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData],
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation using simple rules."""
        
        # Market-only scenario
        if market_data and not internal_data:
            return self._market_only_recommendation(upc, market_data, warnings)
        
        # Internal-only scenario
        if internal_data and not market_data:
            return self._internal_only_recommendation(upc, internal_data, warnings)
        
        # Combined scenario (both sources available)
        return self._combined_recommendation(
            upc, market_data, internal_data, warnings
        )
    
    def _no_data_response(self, upc: str) -> PriceRecommendationResponse:
        """Handle case where no data is available."""
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=0.0,
            internal_vs_market_weighting=0.5,
            confidence_score=0,
            rationale="No market or internal data available. Cannot generate recommendation.",
            warnings=["No data available for this UPC"],
            prediction_method="no_data"
        )
    
    def _market_only_recommendation(
        self,
        upc: str,
        market_data: MarketData,
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation based only on market data."""
        
        # Check if we have enough market data
        LOW_MARKET_SAMPLE_SIZE = 5
        if market_data.sample_size < LOW_MARKET_SAMPLE_SIZE:
            warnings.append(
                f"Low market sample size ({market_data.sample_size}). "
                "Recommendation may not be reliable."
            )
            confidence = max(20, market_data.sample_size * 10)
        else:
            confidence = min(75, 50 + market_data.sample_size * 2)
        
        # Use median price as base (more robust than average)
        recommended_price = market_data.median_price or market_data.average_price or 0.0
        
        median_str = f"${market_data.median_price:.2f}" if market_data.median_price else "N/A"
        rationale = (
            f"Based on market data only. "
            f"Median market price: {median_str} "
            f"from {market_data.sample_size} listings. "
            f"No internal data available for comparison."
        )
        
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=recommended_price,
            internal_vs_market_weighting=0.0,  # All market
            confidence_score=confidence,
            rationale=rationale,
            market_data=market_data,
            warnings=warnings,
            prediction_method="market_only"
        )
    
    def _internal_only_recommendation(
        self,
        upc: str,
        internal_data: InternalData,
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation based only on internal data."""
        
        warnings.append("No market data available. Using internal data only.")
        
        HIGH_SELL_THROUGH_THRESHOLD = 0.7
        STALE_INVENTORY_DAYS = 60
        
        recommended_price = internal_data.internal_price
        rationale_parts = [f"Based on internal data only (${internal_data.internal_price:.2f})."]
        
        # Adjust based on performance metrics
        if internal_data.sell_through_rate >= HIGH_SELL_THROUGH_THRESHOLD:
            rationale_parts.append(
                f"High sell-through rate ({internal_data.sell_through_rate:.2f}) "
                "indicates current price is working well."
            )
            confidence = 70
        elif internal_data.days_on_shelf > STALE_INVENTORY_DAYS:
            # Suggest price reduction for stale inventory
            reduction_factor = 0.90  # 10% reduction
            recommended_price = internal_data.internal_price * reduction_factor
            rationale_parts.append(
                f"Product has been on shelf for {internal_data.days_on_shelf} days. "
                f"Suggesting 10% price reduction to ${recommended_price:.2f}."
            )
            confidence = 60
        else:
            rationale_parts.append(
                f"Moderate sell-through ({internal_data.sell_through_rate:.2f}). "
                "Maintaining current price."
            )
            confidence = 65
        
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=recommended_price,
            internal_vs_market_weighting=1.0,  # All internal
            confidence_score=confidence,
            rationale=" ".join(rationale_parts),
            internal_data=internal_data,
            warnings=warnings,
            prediction_method="internal_only"
        )
    
    def _combined_recommendation(
        self,
        upc: str,
        market_data: MarketData,
        internal_data: InternalData,
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation combining market and internal data using simple rules."""
        
        HIGH_SELL_THROUGH_THRESHOLD = 0.7
        STALE_INVENTORY_DAYS = 60
        LOW_MARKET_SAMPLE_SIZE = 5
        
        # Simple weighting logic
        weighting = 0.5  # Start with equal weight
        confidence = 50
        
        # Adjust based on sell-through
        if internal_data.sell_through_rate >= HIGH_SELL_THROUGH_THRESHOLD:
            weighting += 0.20
            confidence += 15
        elif internal_data.sell_through_rate < 0.3:
            weighting -= 0.15
            confidence -= 5
        
        # Adjust based on inventory age
        if internal_data.days_on_shelf > STALE_INVENTORY_DAYS:
            weighting -= 0.15
            confidence -= 10
        elif internal_data.days_on_shelf < 30:
            weighting += 0.05
            confidence += 5
        
        # Adjust based on market sample size
        if market_data.sample_size < LOW_MARKET_SAMPLE_SIZE:
            weighting += 0.20
            confidence -= 15
            warnings.append(f"Low market sample size ({market_data.sample_size}).")
        elif market_data.sample_size > 20:
            weighting -= 0.10
            confidence += 10
        
        # Clamp values
        weighting = max(0.0, min(1.0, weighting))
        confidence = max(0, min(100, confidence))
        
        # Calculate recommended price
        market_price = market_data.median_price or market_data.average_price or 0.0
        internal_price = internal_data.internal_price
        
        recommended_price = (weighting * internal_price) + ((1 - weighting) * market_price)
        
        # Build rationale
        if weighting > 0.65:
            weight_desc = f"Strong emphasis on internal data ({weighting:.0%} weight)"
        elif weighting < 0.35:
            weight_desc = f"Strong emphasis on market data ({1-weighting:.0%} weight)"
        else:
            weight_desc = f"Balanced: {weighting:.0%} internal, {1-weighting:.0%} market"
        
        rationale = (
            f"{weight_desc}. "
            f"Internal: ${internal_price:.2f}, sell-through: {internal_data.sell_through_rate:.2f}. "
            f"Market: median ${market_price:.2f} from {market_data.sample_size} listings. "
            f"Recommended: ${recommended_price:.2f}."
        )
        
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=recommended_price,
            internal_vs_market_weighting=weighting,
            confidence_score=confidence,
            rationale=rationale,
            market_data=market_data,
            internal_data=internal_data,
            warnings=warnings,
            prediction_method="rule_based"
        )
