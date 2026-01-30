"""Pricing models for API requests and responses."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime


class InternalData(BaseModel):
    """Internal sales data for a product."""
    
    internal_price: float = Field(..., gt=0, description="Internal price in dollars")
    sell_through_rate: float = Field(..., ge=0, le=1, description="Sell-through rate (0-1)")
    days_on_shelf: int = Field(..., ge=0, description="Days product has been on shelf")
    category: str = Field(..., description="Product category")
    sample_size: int = Field(default=0, description="Number of items in sample")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator("internal_price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        """Ensure price is reasonable."""
        if v > 100000:
            raise ValueError("Price seems unreasonably high")
        return round(v, 2)


class MarketData(BaseModel):
    """Market pricing data from eBay."""
    
    median_price: Optional[float] = Field(None, description="Median price from market")
    average_price: Optional[float] = Field(None, description="Average price from market")
    min_price: Optional[float] = Field(None, description="Minimum price from market")
    max_price: Optional[float] = Field(None, description="Maximum price from market")
    sample_size: int = Field(0, description="Number of listings analyzed")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Data collection timestamp")
    active_listings_count: int = Field(0, description="Number of active listings")
    sold_listings_count: int = Field(0, description="Number of sold listings")
    low_confidence: bool = Field(False, description="Whether confidence is low due to small sample")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")
    
    @field_validator("median_price", "average_price", "min_price", "max_price")
    @classmethod
    def round_prices(cls, v: Optional[float]) -> Optional[float]:
        """Round prices to 2 decimals."""
        return round(v, 2) if v is not None else None


class PriceRecommendationRequest(BaseModel):
    """Request model for price recommendation."""
    
    upc: str = Field(..., description="UPC code, product name, brand, or search term")
    internal_data: Optional[InternalData] = Field(None, description="Optional internal sales data")
    
    @field_validator("upc")
    @classmethod
    def validate_upc_format(cls, v: str) -> str:
        """Basic validation - accept any non-empty string."""
        print(f"🔍 VALIDATING UPC FIELD: '{v}'")
        if not v or not v.strip():
            print(f"❌ VALIDATION FAILED: Empty string")
            raise ValueError("Search term cannot be empty")
        print(f"✅ VALIDATION PASSED: '{v}'")
        return v.strip()


class PriceRecommendationResponse(BaseModel):
    """Response model for price recommendation."""
    
    upc: str = Field(..., description="UPC code")
    recommended_price: float = Field(..., description="Recommended price in dollars")
    internal_vs_market_weighting: float = Field(
        ..., 
        ge=0, 
        le=1, 
        description="Weight given to internal data (0=all market, 1=all internal)"
    )
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence score (0-100)")
    rationale: str = Field(..., description="Explanation of the recommendation")
    market_data: Optional[MarketData] = Field(None, description="Market data used")
    internal_data: Optional[InternalData] = Field(None, description="Internal data used")
    warnings: list[str] = Field(default_factory=list, description="Any warnings or alerts")
    feature_importance: Optional[dict] = Field(None, description="ML feature importance scores")
    prediction_method: str = Field(default="rule_based", description="Method used: ml, rule_based, or hybrid")
    
    @field_validator("recommended_price")
    @classmethod
    def round_recommended_price(cls, v: float) -> float:
        """Round recommended price to 2 decimals."""
        return round(v, 2)


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field("1.0.0", description="API version")
