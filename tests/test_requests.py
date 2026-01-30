#!/usr/bin/env python3
"""
Quick test script for the Price Intelligence API.

Run the API first with: uvicorn app.main:app --reload
Then run this script: python test_requests.py
"""
import requests
import json


API_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    print("\n=== Testing Health Endpoint ===")
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_price_recommendation_with_internal_data():
    """Test price recommendation with internal data."""
    print("\n=== Testing Price Recommendation (with internal data) ===")
    
    payload = {
        "upc": "012345678905",
        "internal_data": {
            "internal_price": 29.99,
            "sell_through_rate": 0.75,
            "days_on_shelf": 45,
            "category": "Electronics"
        }
    }
    
    response = requests.post(
        f"{API_URL}/price-recommendation",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response:")
        print(f"  UPC: {data['upc']}")
        print(f"  Recommended Price: ${data['recommended_price']:.2f}")
        print(f"  Internal/Market Weighting: {data['internal_vs_market_weighting']:.2f}")
        print(f"  Confidence Score: {data['confidence_score']}")
        print(f"  Rationale: {data['rationale']}")
        if data.get('warnings'):
            print(f"  Warnings: {data['warnings']}")
    else:
        print(f"Error: {response.text}")


def test_price_recommendation_upc_only():
    """Test price recommendation with UPC only (from CSV)."""
    print("\n=== Testing Price Recommendation (UPC only, from CSV) ===")
    
    payload = {
        "upc": "042100005264"  # This UPC is in the CSV
    }
    
    response = requests.post(
        f"{API_URL}/price-recommendation",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response:")
        print(f"  UPC: {data['upc']}")
        print(f"  Recommended Price: ${data['recommended_price']:.2f}")
        print(f"  Confidence Score: {data['confidence_score']}")
        print(f"  Rationale: {data['rationale']}")
    else:
        print(f"Error: {response.text}")


def test_invalid_upc():
    """Test with invalid UPC."""
    print("\n=== Testing Invalid UPC ===")
    
    payload = {
        "upc": "invalid_upc"
    }
    
    response = requests.post(
        f"{API_URL}/price-recommendation",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


def test_cache_stats():
    """Test cache stats endpoint."""
    print("\n=== Testing Cache Stats ===")
    response = requests.get(f"{API_URL}/cache/stats")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")


if __name__ == "__main__":
    print("=" * 60)
    print("Price Intelligence API - Test Script")
    print("=" * 60)
    
    try:
        test_health()
        test_price_recommendation_with_internal_data()
        test_price_recommendation_upc_only()
        test_invalid_upc()
        test_cache_stats()
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API")
        print("Make sure the API is running:")
        print("  uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
