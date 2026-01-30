#!/usr/bin/env python3
"""
Test script for pricing intelligence system with real data.
This script tests the integration with eBay scraping and internal thrift sales data.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ebay_client import eBayClient
from app.services.internal_data import InternalDataProcessor
from app.services.pricing_engine import PricingEngine


async def test_pricing_system():
    """Test the pricing system with real data."""
    
    print("=" * 80)
    print("PRICING INTELLIGENCE SYSTEM - INTEGRATION TEST")
    print("=" * 80)
    print()
    
    # Initialize services
    print("1. Initializing services...")
    ebay_client = eBayClient(headless=False)  # Set to True for production
    internal_processor = InternalDataProcessor("thrift_sales_12_weeks_with_subcategory.csv")
    pricing_engine = PricingEngine()
    
    # Start eBay session
    await ebay_client.start_session()
    
    # Test cases based on real internal data
    test_cases = [
        {"search_term": "Nike Sneakers", "description": "Nike brand sneakers"},
        {"search_term": "Adidas Jacket", "description": "Adidas jacket"},
        {"search_term": "Levi's Jeans", "description": "Levi's jeans"},
        {"search_term": "Columbia Jacket", "description": "Columbia outdoor jacket"},
    ]
    
    print(f"Loaded {len(internal_processor.data)} internal sales records")
    print()
    
    # Run tests
    for i, test_case in enumerate(test_cases, 1):
        search_term = test_case["search_term"]
        description = test_case["description"]
        
        print(f"\n{'=' * 80}")
        print(f"TEST CASE {i}: {description}")
        print(f"Search term: {search_term}")
        print("=" * 80)
        
        try:
            # Get internal data
            print(f"\n📊 Searching internal data for '{search_term}'...")
            internal_data = internal_processor.search_by_keywords(search_term)
            
            if internal_data:
                print(f"✓ Found internal data:")
                print(f"  - Internal price: ${internal_data.internal_price:.2f}")
                print(f"  - Sell-through rate: {internal_data.sell_through_rate:.2%}")
                print(f"  - Days on shelf: {internal_data.days_on_shelf} days")
                print(f"  - Category: {internal_data.category}")
                print(f"  - Sample size: {internal_data.sample_size} items")
            else:
                print("✗ No internal data found")
            
            # Get market data from eBay
            print(f"\n🔍 Scraping eBay for '{search_term}'...")
            market_data = await ebay_client.get_market_pricing(search_term)
            
            if market_data and market_data.sample_size > 0:
                print(f"✓ Found market data:")
                print(f"  - Median price: ${market_data.median_price:.2f}")
                print(f"  - Average price: ${market_data.average_price:.2f}")
                print(f"  - Price range: ${market_data.min_price:.2f} - ${market_data.max_price:.2f}")
                print(f"  - Sample size: {market_data.sample_size} listings")
                print(f"  - Low confidence: {market_data.low_confidence}")
            else:
                print("✗ No market data found or scraping failed")
            
            # Generate pricing recommendation
            print(f"\n💡 Generating pricing recommendation...")
            recommendation = pricing_engine.generate_recommendation(
                upc=search_term,  # Using search term as identifier
                market_data=market_data if market_data and market_data.sample_size > 0 else None,
                internal_data=internal_data
            )
            
            print(f"\n{'─' * 80}")
            print("RECOMMENDATION:")
            print(f"{'─' * 80}")
            print(f"💰 Recommended Price: ${recommendation.recommended_price:.2f}")
            print(f"📊 Confidence Score: {recommendation.confidence_score}/100")
            print(f"⚖️  Internal/Market Weighting: {recommendation.internal_vs_market_weighting:.2f}")
            print(f"   (1.0 = all internal, 0.0 = all market)")
            print(f"\n📝 Rationale:")
            print(f"   {recommendation.rationale}")
            
            if recommendation.warnings:
                print(f"\n⚠️  Warnings:")
                for warning in recommendation.warnings:
                    print(f"   - {warning}")
            
        except Exception as e:
            print(f"\n❌ Error in test case {i}: {str(e)}")
            import traceback
            traceback.print_exc()
        
        print()
        
        # Wait between tests to avoid rate limiting
        if i < len(test_cases):
            print("⏳ Waiting 5 seconds before next test...")
            await asyncio.sleep(5)
    
    # Close eBay session
    await ebay_client.close_session()
    
    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


async def test_internal_data_only():
    """Quick test of internal data processing without eBay."""
    
    print("\n" + "=" * 80)
    print("INTERNAL DATA PROCESSOR - QUICK TEST")
    print("=" * 80)
    print()
    
    processor = InternalDataProcessor("thrift_sales_12_weeks_with_subcategory.csv")
    
    if processor.data is None or processor.data.empty:
        print("❌ Failed to load internal data")
        return
    
    print(f"✓ Loaded {len(processor.data)} records")
    print()
    
    # Test searches
    test_searches = [
        "Nike",
        "Adidas",
        "Sneakers",
        "Columbia",
        "Levi's"
    ]
    
    for search_term in test_searches:
        print(f"\nSearching for: '{search_term}'")
        result = processor.search_by_keywords(search_term)
        
        if result:
            print(f"  ✓ Found {result.sample_size} items")
            print(f"    Price: ${result.internal_price:.2f}")
            print(f"    Sell-through: {result.sell_through_rate:.2%}")
            print(f"    Days on shelf: {result.days_on_shelf}")
        else:
            print(f"  ✗ No results found")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test pricing intelligence system")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with internal data only (no eBay scraping)"
    )
    
    args = parser.parse_args()
    
    if args.quick:
        asyncio.run(test_internal_data_only())
    else:
        print("\n⚠️  This will open a browser and scrape eBay.")
        print("⚠️  Make sure you have playwright installed: playwright install chromium")
        print()
        response = input("Continue? (y/n): ")
        if response.lower() == 'y':
            asyncio.run(test_pricing_system())
        else:
            print("Test cancelled.")
