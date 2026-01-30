"""
Test the new Playwright + ScrapFly scraper locally
"""
import asyncio
import sys
sys.path.append('/Users/1di/coding_challenge')

from app.services.ebay_scraper import eBayScrapFlyClient, eBayPlaywrightClient
from app.config import Settings

settings = Settings()


async def test_scrapers():
    print("\n" + "="*80)
    print("🧪 TESTING NEW EBAY SCRAPERS")
    print("="*80)
    
    search_term = "Nike Sneakers"
    
    # Test 1: Playwright (no ScrapFly)
    print("\n\n🎭 TEST 1: Playwright Direct Scraping")
    print("-"*80)
    playwright_client = eBayPlaywrightClient()
    
    try:
        result = await playwright_client.get_market_pricing(search_term, max_results=20)
        print(f"\n✅ Playwright Results:")
        print(f"   Sample size: {result.sample_size}")
        if result.median_price:
            print(f"   Median price: ${result.median_price:.2f}")
            print(f"   Price range: ${result.min_price:.2f} - ${result.max_price:.2f}")
        print(f"   Sold listings: {result.sold_listings_count}")
    except Exception as e:
        print(f"❌ Playwright failed: {e}")
    
    # Test 2: ScrapFly (if API key available)
    if settings.scrapfly_api_key and settings.use_scrapfly:
        print("\n\n🚀 TEST 2: ScrapFly Scraping")
        print("-"*80)
        scrapfly_client = eBayScrapFlyClient(scrapfly_api_key=settings.scrapfly_api_key)
        
        try:
            result = await scrapfly_client.get_market_pricing(search_term, max_results=20)
            print(f"\n✅ ScrapFly Results:")
            print(f"   Sample size: {result.sample_size}")
            if result.median_price:
                print(f"   Median price: ${result.median_price:.2f}")
                print(f"   Price range: ${result.min_price:.2f} - ${result.max_price:.2f}")
            print(f"   Sold listings: {result.sold_listings_count}")
        except Exception as e:
            print(f"❌ ScrapFly failed: {e}")
    else:
        print("\n\n⚠️  ScrapFly API key not configured, skipping ScrapFly test")
    
    print("\n" + "="*80)
    print("✅ Testing complete!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_scrapers())
