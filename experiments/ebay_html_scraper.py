"""
Experimental eBay HTML scraper using Playwright to extract more pricing information.

This tests if we can get better data by parsing eBay's HTML with browser automation
instead of relying on OpenAI's web search results.
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
import json
from typing import List, Dict, Optional
import re
import time


def fetch_ebay_search_with_playwright(search_term: str) -> tuple[str, List[Dict]]:
    """Fetch eBay search results using Playwright."""
    print(f"🔍 Launching browser for: {search_term}")
    
    with sync_playwright() as p:
        # Launch browser (non-headless for debugging)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()
        
        # Navigate to eBay sold listings
        base_url = "https://www.ebay.com/sch/i.html"
        search_url = f"{base_url}?_nkw={search_term.replace(' ', '+')}&_sacat=0&LH_Sold=1&LH_Complete=1&_sop=12"
        
        print(f"📄 Loading: {search_url}")
        page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
        
        # Wait for JavaScript to fully render the page
        print("⏳ Waiting for JavaScript to load listings...")
        time.sleep(5)  # Give JS time to render
        
        # Wait specifically for listing items to appear
        try:
            page.wait_for_selector('.s-item__info', timeout=10000)
            print("✅ Listings rendered")
        except PlaywrightTimeout:
            print("⚠️  Listings selector not found, trying alternative...")
            try:
                page.wait_for_selector('[class*="s-item"]', timeout=5000)
                print("✅ Found items with alternative selector")
            except PlaywrightTimeout:
                print("❌ No items found after waiting")
                print("❌ No items found after waiting")
        
        # Take screenshot AFTER waiting
        page.screenshot(path='experiments/ebay_page.png')
        print("📸 Screenshot saved to experiments/ebay_page.png")
        
        # Check page title
        page_title = page.title()
        print(f"📌 Page title: {page_title}")
        
        if "security" in page_title.lower() or "captcha" in page_title.lower():
            print("🚫 Got blocked by eBay security")
            browser.close()
            return "", []
        
        # Scroll to load more items
        for i in range(3):
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(0.3)
        
        # Get HTML
        html = page.content()
        
        # Try multiple extraction strategies
        print("🔎 Trying extraction strategy 1: JavaScript evaluation...")
        listings = page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll('.s-item'));
            console.log('Found items:', items.length);
            return items.map(item => {
                try {
                    // Title
                    const titleElem = item.querySelector('.s-item__title');
                    const title = titleElem ? titleElem.textContent.trim() : null;
                    
                    // Skip banner items
                    if (!title || title.toLowerCase().includes('shop on ebay')) {
                        return null;
                    }
                    
                    // Price
                    const priceElem = item.querySelector('.s-item__price');
                    let price = null;
                    if (priceElem) {
                        const priceText = priceElem.textContent.trim();
                        const match = priceText.match(/\\$?([\\d,]+\\.?\\d*)/);
                        if (match) {
                            price = parseFloat(match[1].replace(',', ''));
                        }
                    }
                    
                    // Condition
                    const conditionElem = item.querySelector('.SECONDARY_INFO');
                    const condition = conditionElem ? conditionElem.textContent.trim() : 'Unknown';
                    
                    // Shipping
                    const shippingElem = item.querySelector('.s-item__shipping');
                    const shipping = shippingElem ? shippingElem.textContent.trim() : null;
                    
                    // Link
                    const linkElem = item.querySelector('a.s-item__link');
                    const link = linkElem ? linkElem.href : null;
                    
                    // Sold status
                    const soldElem = item.querySelector('.s-item__title--tag, .POSITIVE');
                    const isSold = soldElem && soldElem.textContent.toLowerCase().includes('sold');
                    
                    // Sold date
                    const dateElem = item.querySelector('.s-item__ended-date, .s-item__endedDate');
                    const soldDate = dateElem ? dateElem.textContent.trim() : null;
                    
                    if (price) {
                        return {
                            title: title,
                            price: price,
                            condition: condition,
                            shipping: shipping,
                            is_sold: isSold,
                            sold_date: soldDate,
                            link: link
                        };
                    }
                    return null;
                } catch (e) {
                    console.error('Error parsing item:', e);
                    return null;
                }
            }).filter(item => item !== null);
        }""")
        
        print(f"✅ Extracted {len(listings)} listings from page")
        
        # Wait so user can see the browser (for debugging)
        print("⏸️  Pausing for 3 seconds...")
        time.sleep(3)
        
        browser.close()
        
        return html, listings


def analyze_listings(listings: List[Dict]) -> Dict:
    """Analyze extracted listings to get pricing statistics."""
    if not listings:
        return {
            'count': 0,
            'median_price': None,
            'average_price': None,
            'min_price': None,
            'max_price': None,
            'sold_count': 0,
            'sold_median': None,
            'sold_average': None,
            'listings': []
        }
    
    prices = [item['price'] for item in listings]
    sold_prices = [item['price'] for item in listings if item['is_sold']]
    
    prices.sort()
    median_idx = len(prices) // 2
    median = prices[median_idx] if prices else None
    
    sold_prices_sorted = sorted(sold_prices) if sold_prices else []
    sold_median = sold_prices_sorted[len(sold_prices_sorted)//2] if sold_prices_sorted else None
    
    return {
        'count': len(listings),
        'median_price': median,
        'average_price': sum(prices) / len(prices) if prices else None,
        'min_price': min(prices) if prices else None,
        'max_price': max(prices) if prices else None,
        'sold_count': len(sold_prices),
        'sold_median': sold_median,
        'sold_average': sum(sold_prices) / len(sold_prices) if sold_prices else None,
        'listings': listings[:15]  # Sample of first 15
    }


def test_ebay_scraper(search_term: str):
    """Test the eBay scraper with a search term."""
    print("=" * 60)
    print(f"Testing eBay Playwright Scraper")
    print("=" * 60)
    
    try:
        # Fetch with Playwright
        html, listings = fetch_ebay_search_with_playwright(search_term)
        
        # Save HTML for inspection
        with open('experiments/ebay_search_raw.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"💾 Saved raw HTML to experiments/ebay_search_raw.html")
        
        # Analyze
        stats = analyze_listings(listings)
        
        # Print results
        print("\n" + "=" * 60)
        print("📊 RESULTS")
        print("=" * 60)
        print(f"Total listings found: {stats['count']}")
        print(f"Sold listings: {stats['sold_count']}")
        if stats['min_price']:
            print(f"All items price range: ${stats['min_price']:.2f} - ${stats['max_price']:.2f}")
            print(f"All items median: ${stats['median_price']:.2f}")
            print(f"All items average: ${stats['average_price']:.2f}")
        if stats.get('sold_median'):
            print(f"Sold items median: ${stats['sold_median']:.2f}")
            print(f"Sold items average: ${stats['sold_average']:.2f}")
        
        print("\n📦 Sample listings:")
        for i, listing in enumerate(stats['listings'][:8], 1):
            sold_tag = "✅ SOLD" if listing['is_sold'] else "🔴 Active"
            print(f"\n{i}. {sold_tag}")
            print(f"   Title: {listing['title'][:70]}...")
            print(f"   Price: ${listing['price']:.2f}")
            print(f"   Condition: {listing['condition']}")
            if listing['sold_date']:
                print(f"   Sold: {listing['sold_date']}")
        
        # Save JSON
        with open('experiments/ebay_results.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2)
        print(f"\n💾 Saved results to experiments/ebay_results.json")
        
        return stats
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # Test with Nike Sneakers
    test_ebay_scraper("Nike Sneakers")
