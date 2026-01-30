"""Tests for pricing engine."""
import pytest
from datetime import datetime
from app.services.pricing_engine import PricingEngine
from app.models.pricing import MarketData, InternalData


class TestPricingEngine:
    """Test cases for pricing engine."""
    
    @pytest.fixture
    def engine(self):
        """Create pricing engine instance."""
        return PricingEngine()
    
    @pytest.fixture
    def market_data_good(self):
        """Market data with good sample size."""
        return MarketData(
            median_price=28.50,
            average_price=29.00,
            sample_size=15,
            timestamp=datetime.utcnow(),
            active_listings_count=10,
            sold_listings_count=5
        )
    
    @pytest.fixture
    def market_data_low_sample(self):
        """Market data with low sample size."""
        return MarketData(
            median_price=28.50,
            average_price=29.00,
            sample_size=3,
            timestamp=datetime.utcnow(),
            active_listings_count=2,
            sold_listings_count=1
        )
    
    @pytest.fixture
    def internal_data_good(self):
        """Internal data with good performance."""
        return InternalData(
            internal_price=30.00,
            sell_through_rate=0.75,
            days_on_shelf=30,
            category="Electronics"
        )
    
    @pytest.fixture
    def internal_data_stale(self):
        """Internal data with stale inventory."""
        return InternalData(
            internal_price=30.00,
            sell_through_rate=0.30,
            days_on_shelf=80,
            category="Electronics"
        )
    
    def test_no_data(self, engine):
        """Test recommendation with no data."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=None,
            internal_data=None
        )
        
        assert result.recommended_price == 0.0
        assert result.confidence_score == 0
        assert len(result.warnings) > 0
    
    def test_market_only_good_sample(self, engine, market_data_good):
        """Test recommendation with only market data (good sample)."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=market_data_good,
            internal_data=None
        )
        
        assert result.recommended_price == 28.50  # median price
        assert result.internal_vs_market_weighting == 0.0  # all market
        assert result.confidence_score > 50
    
    def test_market_only_low_sample(self, engine, market_data_low_sample):
        """Test recommendation with only market data (low sample)."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=market_data_low_sample,
            internal_data=None
        )
        
        assert result.recommended_price == 28.50
        assert result.confidence_score < 50  # lower confidence
        assert any("Low market sample" in w for w in result.warnings)
    
    def test_internal_only_good(self, engine, internal_data_good):
        """Test recommendation with only internal data (good performance)."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=None,
            internal_data=internal_data_good
        )
        
        assert result.recommended_price == 30.00
        assert result.internal_vs_market_weighting == 1.0  # all internal
        assert result.confidence_score >= 60
    
    def test_internal_only_stale(self, engine, internal_data_stale):
        """Test recommendation with stale inventory."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=None,
            internal_data=internal_data_stale
        )
        
        # Should recommend price reduction
        assert result.recommended_price < 30.00
        assert result.internal_vs_market_weighting == 1.0
    
    def test_combined_high_sell_through(
        self, engine, market_data_good, internal_data_good
    ):
        """Test combined recommendation with high sell-through."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=market_data_good,
            internal_data=internal_data_good
        )
        
        # Should weight internal data more heavily (high sell-through)
        assert result.internal_vs_market_weighting > 0.5
        assert result.confidence_score > 60
        # Price should be between market and internal
        assert 28.50 <= result.recommended_price <= 30.00
    
    def test_combined_stale_inventory(
        self, engine, market_data_good, internal_data_stale
    ):
        """Test combined recommendation with stale inventory."""
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=market_data_good,
            internal_data=internal_data_stale
        )
        
        # Should weight market data more heavily (stale inventory)
        assert result.internal_vs_market_weighting < 0.5
    
    def test_price_variance_warning(self, engine, market_data_good):
        """Test warning for large price variance."""
        # Create internal data with significantly different price
        internal_data = InternalData(
            internal_price=50.00,  # Much higher than market
            sell_through_rate=0.60,
            days_on_shelf=30,
            category="Electronics"
        )
        
        result = engine.generate_recommendation(
            upc="012345678905",
            market_data=market_data_good,
            internal_data=internal_data
        )
        
        # Should have warning about price variance
        assert any("price difference" in w.lower() for w in result.warnings)
