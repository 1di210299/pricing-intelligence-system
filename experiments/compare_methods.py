"""
Compare Playwright vs OpenAI web_search results
Uses pre-generated results to avoid async conflicts
"""
import json
import sys
sys.path.append('/Users/1di/coding_challenge')


def load_playwright_results():
    """Load results from Playwright scraper V2"""
    try:
        with open('experiments/ebay_results_v2.json', 'r') as f:
            data = json.load(f)
        
        return {
            'method': 'Playwright Direct HTML',
            'count': data['listings_count'],
            'median': data['analysis'].get('median'),
            'average': data['analysis'].get('average'),
            'min': data['analysis'].get('min'),
            'max': data['analysis'].get('max'),
            'sold_count': data['analysis'].get('sold_count'),
            'listings': data['listings']
        }
    except FileNotFoundError:
        print("❌ Run ebay_html_scraper_v2.py first to generate Playwright results")
        return None


async def test_openai_method():
    """Test OpenAI web_search method"""
    from app.services.ebay_client import eBayClient
    
    print("\n🤖 Testing OpenAI web_search method...")
    client = eBayClient()
    results = await client.get_market_pricing("Nike Sneakers")
    
    if results and results.sample_size > 0:
        return {
            'method': 'OpenAI web_search',
            'count': results.sample_size,
            'median': results.median_price,
            'average': results.average_price,
            'min': results.min_price,
            'max': results.max_price,
            'sold_count': results.sold_listings_count,
            'listings': []  # OpenAI returns aggregated data, not individual listings
        }
    return None


def compare_results(playwright_res, openai_res):
    """Print comparison table"""
    print("\n" + "="*80)
    print("📊 COMPARISON: Playwright vs OpenAI web_search")
    print("="*80)
    
    if not playwright_res or not openai_res:
        print("❌ Missing results, cannot compare")
        return
    
    print(f"\n{'Metric':<30} {'Playwright HTML':<25} {'OpenAI web_search':<25}")
    print("-"*80)
    print(f"{'Total listings':<30} {playwright_res['count']:<25} {openai_res['count']:<25}")
    print(f"{'Sold listings':<30} {playwright_res['sold_count']:<25} {openai_res['sold_count']:<25}")
    
    if playwright_res['median'] and openai_res['median']:
        print(f"{'Median price':<30} ${playwright_res['median']:<24.2f} ${openai_res['median']:<24.2f}")
    
    if playwright_res['average'] and openai_res['average']:
        print(f"{'Average price':<30} ${playwright_res['average']:<24.2f} ${openai_res['average']:<24.2f}")
    
    if playwright_res['min'] and openai_res['min']:
        print(f"{'Min price':<30} ${playwright_res['min']:<24.2f} ${openai_res['min']:<24.2f}")
        print(f"{'Max price':<30} ${playwright_res['max']:<24.2f} ${openai_res['max']:<24.2f}")
    
    print("\n" + "="*80)
    print("💡 ANALYSIS")
    print("="*80)
    
    # Comparison insights
    diff_count = playwright_res['count'] - openai_res['count']
    if diff_count > 0:
        print(f"\n✅ Playwright extracted {diff_count} MORE listings ({playwright_res['count']} vs {openai_res['count']})")
    elif diff_count < 0:
        print(f"\n✅ OpenAI extracted {abs(diff_count)} MORE listings ({openai_res['count']} vs {playwright_res['count']})")
    else:
        print(f"\n⚖️  Both methods found same number of listings ({playwright_res['count']})")
    
    # Price comparison
    if playwright_res['median'] and openai_res['median']:
        price_diff = abs(playwright_res['median'] - openai_res['median'])
        price_diff_pct = (price_diff / playwright_res['median']) * 100
        print(f"\n📈 Median price difference: ${price_diff:.2f} ({price_diff_pct:.1f}%)")
        
        if price_diff_pct < 5:
            print("   ✅ Prices are very close (< 5% difference)")
        elif price_diff_pct < 10:
            print("   ⚠️  Moderate price difference (5-10%)")
        else:
            print("   ⚠️  Significant price difference (> 10%)")
    
    # Recommend ion
    print("\n" + "="*80)
    print("🎯 RECOMMENDATION")
    print("="*80)
    
    if playwright_res['count'] >= openai_res['count'] * 1.5:
        print("\n✅ USE PLAYWRIGHT: Extracts significantly more data (50%+ more listings)")
        print("   Benefits:")
        print("   - More comprehensive market data")
        print("   - Better price accuracy with larger sample")
        print("   - No OpenAI API costs")
        print("\n   Trade-offs:")
        print("   - Requires browser automation")
        print("   - May need periodic selector updates if eBay changes HTML")
        print("   - Slightly higher infrastructure cost")
    
    elif openai_res['count'] >= playwright_res['count'] * 1.5:
        print("\n✅ KEEP OPENAI: More reliable and extracts more data")
        print("   Benefits:")
        print("   - Handles dynamic content automatically")
        print("   - Less maintenance (no selector updates)")
        print("   - Cleaner code")
        print("\n   Trade-offs:")
        print("   - OpenAI API costs per request")
    
    else:
        print("\n⚖️  BOTH METHODS SIMILAR: Choose based on priorities")
        print("\n   Choose PLAYWRIGHT if:")
        print("   - Want to minimize API costs")
        print("   - Have infrastructure for browser automation")
        print("   - Need maximum control over data extraction")
        print("\n   Choose OPENAI if:")
        print("   - Want simpler, more maintainable code")
        print("   - Already using OpenAI for other features")
        print("   - Prefer reliability over marginal cost savings")
    
    print("\n" + "="*80)


async def run_comparison():
    """Main comparison function"""
    print("\n🔬 EBAY SCRAPING COMPARISON EXPERIMENT")
    print("="*80)
    print("Comparing: Playwright HTML scraping vs OpenAI web_search API")
    print("="*80)
    
    # Load Playwright results
    print("\n📂 Loading Playwright results...")
    playwright_res = load_playwright_results()
    if playwright_res:
        print(f"✅ Loaded {playwright_res['count']} listings from Playwright")
    
    # Test OpenAI method
    openai_res = await test_openai_method()
    if openai_res:
        print(f"✅ Retrieved {openai_res['count']} listings from OpenAI")
    
    # Compare
    if playwright_res and openai_res:
        compare_results(playwright_res, openai_res)
    else:
        print("\n❌ Cannot complete comparison - missing results")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_comparison())
