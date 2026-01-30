"""
Compare OpenAI web search vs direct HTML scraping for eBay data.
"""
import sys
sys.path.append('/Users/1di/coding_challenge')

import asyncio
from experiments.ebay_html_scraper import test_ebay_scraper
from app.services.ebay_client import eBayClient


async def compare_methods(search_term: str):
    """Compare both methods side by side."""
    print("\n" + "=" * 80)
    print("🔬 EXPERIMENT: OpenAI vs Direct HTML Scraping")
    print("=" * 80)
    
    # Method 1: HTML Scraping
    print("\n\n🌐 METHOD 1: Direct HTML Scraping")
    print("-" * 80)
    html_results = test_ebay_scraper(search_term)
    
    # Method 2: OpenAI Web Search
    print("\n\n🤖 METHOD 2: OpenAI Web Search")
    print("-" * 80)
    ebay_client = eBayClient()
    openai_results = await ebay_client.search_sold_items(search_term)
    
    if openai_results:
        print(f"✅ OpenAI found {openai_results.sample_size} listings")
        print(f"   Median: ${openai_results.median_price:.2f}" if openai_results.median_price else "N/A")
        print(f"   Range: ${openai_results.min_price:.2f} - ${openai_results.max_price:.2f}" if openai_results.min_price else "N/A")
        print(f"   Sold: {openai_results.sold_listings_count}")
    else:
        print("❌ OpenAI found no results")
    
    # Comparison
    print("\n\n📊 COMPARISON")
    print("=" * 80)
    
    if html_results and openai_results:
        print(f"{'Metric':<30} {'HTML Scraping':<25} {'OpenAI Search':<25}")
        print("-" * 80)
        print(f"{'Total listings':<30} {html_results['count']:<25} {openai_results.sample_size:<25}")
        print(f"{'Sold listings':<30} {html_results['sold_count']:<25} {openai_results.sold_listings_count:<25}")
        
        if html_results['median_price']:
            print(f"{'Median price':<30} ${html_results['median_price']:<24.2f} ${openai_results.median_price or 0:<24.2f}")
        if html_results['min_price']:
            print(f"{'Price range':<30} ${html_results['min_price']:.2f}-${html_results['max_price']:.2f}{'':>12} ${openai_results.min_price or 0:.2f}-${openai_results.max_price or 0:.2f}")
        
        print("\n💡 INSIGHTS:")
        if html_results['count'] > openai_results.sample_size:
            print(f"   ✅ HTML scraping found {html_results['count'] - openai_results.sample_size} MORE listings")
        elif html_results['count'] < openai_results.sample_size:
            print(f"   ✅ OpenAI found {openai_results.sample_size - html_results['count']} MORE listings")
        else:
            print(f"   ⚖️  Both methods found the same number of listings")
        
        if html_results['median_price'] and openai_results.median_price:
            price_diff = abs(html_results['median_price'] - openai_results.median_price)
            price_diff_pct = (price_diff / html_results['median_price']) * 100
            print(f"   📈 Price difference: ${price_diff:.2f} ({price_diff_pct:.1f}%)")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    search_term = "Nike Sneakers"
    asyncio.run(compare_methods(search_term))
