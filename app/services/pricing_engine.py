"""Pricing recommendation engine."""
from typing import Optional, Tuple
from app.models.pricing import (
    InternalData, 
    MarketData, 
    PriceRecommendationResponse
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PricingEngine:
    """
    Engine for generating pricing recommendations.
    
    Combines market data and internal sales data to recommend optimal prices.
    """
    
    # Thresholds for decision-making
    HIGH_SELL_THROUGH_THRESHOLD = 0.7
    STALE_INVENTORY_DAYS = 60
    LOW_MARKET_SAMPLE_SIZE = 5
    PRICE_VARIANCE_THRESHOLD = 0.30  # 30% difference
    
    # Category-specific margin adjustments
    CATEGORY_MARGINS = {
        "Electronics": 0.15,      # 15% margin
        "Clothing": 0.40,         # 40% margin
        "Books": 0.30,            # 30% margin
        "Toys": 0.35,             # 35% margin
        "Home & Garden": 0.25,    # 25% margin
        "Sports": 0.30,           # 30% margin
        "Default": 0.25           # Default 25% margin
    }
    
    def generate_recommendation(
        self,
        upc: str,
        market_data: Optional[MarketData],
        internal_data: Optional[InternalData]
    ) -> PriceRecommendationResponse:
        """
        Generate a pricing recommendation.
        
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
            warnings=["No data available for this UPC"]
        )
    
    def _market_only_recommendation(
        self,
        upc: str,
        market_data: MarketData,
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation based only on market data."""
        
        # Check if we have enough market data
        if market_data.sample_size < self.LOW_MARKET_SAMPLE_SIZE:
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
            warnings=warnings
        )
    
    def _internal_only_recommendation(
        self,
        upc: str,
        internal_data: InternalData,
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation based only on internal data."""
        
        warnings.append("No market data available. Using internal data only.")
        
        recommended_price = internal_data.internal_price
        rationale_parts = [f"Based on internal data only (${internal_data.internal_price:.2f})."]
        
        # Adjust based on performance metrics
        if internal_data.sell_through_rate >= self.HIGH_SELL_THROUGH_THRESHOLD:
            rationale_parts.append(
                f"High sell-through rate ({internal_data.sell_through_rate:.2f}) "
                "indicates current price is working well."
            )
            confidence = 70
        elif internal_data.days_on_shelf > self.STALE_INVENTORY_DAYS:
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
            warnings=warnings
        )
    
    def _combined_recommendation(
        self,
        upc: str,
        market_data: MarketData,
        internal_data: InternalData,
        warnings: list[str]
    ) -> PriceRecommendationResponse:
        """Generate recommendation combining market and internal data."""
        
        # Determine weighting and confidence
        weighting, confidence = self._calculate_weighting_and_confidence(
            market_data, internal_data, warnings
        )
        
        # Calculate recommended price
        market_price = market_data.median_price or market_data.average_price or 0.0
        internal_price = internal_data.internal_price
        
        # Weighted average
        recommended_price = (
            (weighting * internal_price) + 
            ((1 - weighting) * market_price)
        )
        
        # Apply category-specific adjustments
        recommended_price = self._apply_category_adjustment(
            recommended_price, internal_data.category
        )
        
        # Check for significant price variance
        if market_price > 0:
            variance = abs(internal_price - market_price) / market_price
            if variance > self.PRICE_VARIANCE_THRESHOLD:
                warnings.append(
                    f"Large price difference detected: internal (${internal_price:.2f}) "
                    f"vs market (${market_price:.2f}). Variance: {variance:.1%}. "
                    "Please review."
                )
        
        # Build rationale
        rationale = self._build_rationale(
            weighting, confidence, market_data, internal_data, 
            market_price, recommended_price
        )
        
        return PriceRecommendationResponse(
            upc=upc,
            recommended_price=recommended_price,
            internal_vs_market_weighting=weighting,
            confidence_score=confidence,
            rationale=rationale,
            market_data=market_data,
            internal_data=internal_data,
            warnings=warnings
        )
    
    def _calculate_weighting_and_confidence(
        self,
        market_data: MarketData,
        internal_data: InternalData,
        warnings: list[str]
    ) -> Tuple[float, int]:
        """
        Calculate the weighting between internal and market data.
        
        Returns:
            Tuple of (weighting, confidence_score)
            weighting: 0-1, where 1 = all internal, 0 = all market
        """
        weighting = 0.5  # Start with equal weight
        confidence = 50
        
        # Factor 1: Sell-through rate
        if internal_data.sell_through_rate >= self.HIGH_SELL_THROUGH_THRESHOLD:
            # High sell-through → trust internal price more
            weighting += 0.20
            confidence += 15
            logger.debug(f"High sell-through: +0.20 to internal weighting")
        elif internal_data.sell_through_rate < 0.3:
            # Low sell-through → trust market more
            weighting -= 0.15
            confidence -= 5
            logger.debug(f"Low sell-through: -0.15 to internal weighting")
        
        # Factor 2: Days on shelf
        if internal_data.days_on_shelf > self.STALE_INVENTORY_DAYS:
            # Stale inventory → trust market more (need to move product)
            weighting -= 0.15
            confidence -= 10
            logger.debug(f"Stale inventory: -0.15 to internal weighting")
        elif internal_data.days_on_shelf < 30:
            # Fresh inventory → trust internal slightly more
            weighting += 0.05
            confidence += 5
            logger.debug(f"Fresh inventory: +0.05 to internal weighting")
        
        # Factor 3: Market sample size
        if market_data.sample_size < self.LOW_MARKET_SAMPLE_SIZE:
            # Low market data → trust internal more
            weighting += 0.20
            confidence -= 15
            warnings.append(
                f"Low market sample size ({market_data.sample_size}). "
                "Giving more weight to internal data."
            )
            logger.debug(f"Low market sample: +0.20 to internal weighting")
        elif market_data.sample_size > 20:
            # High market data → trust market more
            weighting -= 0.10
            confidence += 10
            logger.debug(f"High market sample: -0.10 to internal weighting")
        
        # Ensure weighting is between 0 and 1
        weighting = max(0.0, min(1.0, weighting))
        
        # Ensure confidence is between 0 and 100
        confidence = max(0, min(100, confidence))
        
        return weighting, confidence
    
    def _apply_category_adjustment(
        self,
        price: float,
        category: str
    ) -> float:
        """
        Apply category-specific margin adjustments.
        
        Args:
            price: Base price
            category: Product category
            
        Returns:
            Adjusted price
        """
        # Get margin for category (or default)
        margin = self.CATEGORY_MARGINS.get(category, self.CATEGORY_MARGINS["Default"])
        
        # This is a simplified adjustment
        # In production, you might have more sophisticated category logic
        logger.debug(f"Category {category}: margin={margin}")
        
        return price
    
    def _build_rationale(
        self,
        weighting: float,
        confidence: int,
        market_data: MarketData,
        internal_data: InternalData,
        market_price: float,
        recommended_price: float
    ) -> str:
        """Build human-readable rationale for the recommendation."""
        
        parts = []
        
        # Weighting explanation
        if weighting > 0.65:
            parts.append(
                f"Strong emphasis on internal data ({weighting:.0%} weight) "
                f"due to good performance metrics."
            )
        elif weighting < 0.35:
            parts.append(
                f"Strong emphasis on market data ({1-weighting:.0%} weight) "
                f"due to performance concerns or strong market signals."
            )
        else:
            parts.append(
                f"Balanced approach: {weighting:.0%} internal, "
                f"{1-weighting:.0%} market data."
            )
        
        # Performance metrics
        parts.append(
            f"Internal: ${internal_data.internal_price:.2f}, "
            f"sell-through: {internal_data.sell_through_rate:.2f}, "
            f"{internal_data.days_on_shelf} days on shelf."
        )
        
        # Market data
        parts.append(
            f"Market: median ${market_price:.2f} "
            f"from {market_data.sample_size} listings."
        )
        
        # Recommendation
        parts.append(f"Recommended: ${recommended_price:.2f}.")
        
        return " ".join(parts)
