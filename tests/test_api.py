"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.internal_data import InternalDataProcessor
from app.services.ebay_client import eBayClient
from app.services.pricing_engine import PricingEngine


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestRootEndpoint:
    """Test root endpoint."""
    
    def test_root(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestPriceRecommendationEndpoint:
    """Test price recommendation endpoint."""
    
    def test_valid_upc_no_internal_data(self, client):
        """Test recommendation with valid UPC, no internal data."""
        request_data = {
            "upc": "012345678905"
        }
        
        response = client.post("/price-recommendation", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "upc" in data
        assert "recommended_price" in data
        assert "confidence_score" in data
        assert "rationale" in data
    
    def test_valid_upc_with_internal_data(self, client):
        """Test recommendation with valid UPC and internal data."""
        request_data = {
            "upc": "012345678905",
            "internal_data": {
                "internal_price": 29.99,
                "sell_through_rate": 0.75,
                "days_on_shelf": 45,
                "category": "Electronics"
            }
        }
        
        response = client.post("/price-recommendation", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["upc"] == "012345678905"
        assert data["recommended_price"] > 0
        assert 0 <= data["internal_vs_market_weighting"] <= 1
        assert 0 <= data["confidence_score"] <= 100
    
    def test_invalid_upc_format(self, client):
        """Test with invalid UPC format."""
        request_data = {
            "upc": "invalid"
        }
        
        response = client.post("/price-recommendation", json=request_data)
        assert response.status_code == 400
    
    def test_invalid_upc_checksum(self, client):
        """Test with invalid UPC checksum."""
        request_data = {
            "upc": "012345678906"  # Wrong checksum
        }
        
        response = client.post("/price-recommendation", json=request_data)
        assert response.status_code == 400
    
    def test_invalid_internal_data(self, client):
        """Test with invalid internal data."""
        request_data = {
            "upc": "012345678905",
            "internal_data": {
                "internal_price": -10.00,  # Invalid: negative price
                "sell_through_rate": 0.75,
                "days_on_shelf": 45,
                "category": "Electronics"
            }
        }
        
        response = client.post("/price-recommendation", json=request_data)
        assert response.status_code == 422  # Validation error


class TestCacheEndpoints:
    """Test cache management endpoints."""
    
    def test_cache_stats(self, client):
        """Test cache stats endpoint."""
        response = client.get("/cache/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "cache_type" in data
        assert "ttl" in data
    
    def test_cache_clear(self, client):
        """Test cache clear endpoint."""
        response = client.delete("/cache/clear")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "success"
