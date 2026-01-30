"""
eBay HTML Scraper V2 - Using correct selectors from actual eBay HTML structure
Tests direct Playwright HTML scraping vs OpenAI web_search extraction
"""
import os
import json
import time
from playwright.sync_api import sync_playwright


def fetch_ebay_search_with_playwright(search_query="Nike Sneakers", max_results=20):
    """
    Scrape eBay sold listings using Playwright with CORRECT selectors
    
    eBay uses:
    - .s-card for main item containers
    - .s-card__title .su-styled-text for titles
    - .s-card__price for prices
    - .s-card__subtitle for condition
    - .s-card__caption for sold status
    """
    print(f"\n{'='*60}")
    print(f"🎯 EBAY PLAYWRIGHT SCRAPER V2 - Correct Selectors")
    print(f"{'='*60}")
    print(f"🔍 Searching for: {search_query}")
    print(f"📊 Max results: {max_results}")
    
    with sync_playwright() as p:
        print("\n🌐 Launching Chromium browser (non-headless for debugging)...")
        browser = p.chromium.launch(headless=False)
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        
        page = context.new_page()
        
        # Build eBay search URL for sold listings
        search_url = (
            f"https://www.ebay.com/sch/i.html"
            f"?_nkw={search_query.replace(' ', '+')}"
            f"&_sacat=0"
            f"&LH_Sold=1"
            f"&LH_Complete=1"
            f"&_sop=12"
        )
        
        print(f"📍 URL: {search_url}")
        print("⏳ Loading page...")
        
        page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        
        # Wait for listings to load
        print("⏳ Waiting for listings to load...")
        try:
            page.wait_for_selector('.s-card', timeout=10000)
            print("✅ Found .s-card selector!")
        except:
            print("⚠️  Timeout waiting for .s-card, trying anyway...")
        
        # Additional wait for JS rendering
        print("⏳ Waiting 5 seconds for JavaScript to render content...")
        time.sleep(5)
        
        # Check page title
        title = page.title()
        print(f"📄 Page title: {title}")
        
        # Take screenshot for debugging
        screenshot_path = "experiments/ebay_page_v2.png"
        page.screenshot(path=screenshot_path)
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Check for security blocks
        if "security measure" in title.lower() or "verify" in title.lower():
            print("🚫 Got blocked by eBay security")
            browser.close()
            return "", []
        
        # Scroll to load more items
        for i in range(3):
            page.evaluate("window.scrollBy(0, 1000)")
            time.sleep(0.3)
        
        # Get HTML
        html = page.content()
        
        # Extract listings using JavaScript with CORRECT selectors
        print("\n🔎 Extracting listings with correct selectors...")
        listings = page.evaluate("""() => {
            const items = Array.from(document.querySelectorAll('.s-card'));
            console.log('Found .s-card items:', items.length);
            
            return items.map(item => {
                try {
                    // Title - .s-card__title .su-styled-text
                    const titleElem = item.querySelector('.s-card__title .su-styled-text');
                    const title = titleElem ? titleElem.textContent.trim() : null;
                    
                    // Skip invalid items
                    if (!title || title.toLowerCase().includes('shop on ebay')) {
                        return null;
                    }
                    
                    // Price - .s-card__price
                    const priceElem = item.querySelector('.s-card__price');
                    let price = null;
                    if (priceElem) {
                        const priceText = priceElem.textContent.trim();
                        // Match S/. 464.94, $100.50, etc
                        const match = priceText.match(/[S$£€]\/?\s*\.?\s*([\d,]+\.?\d*)/);
                        if (match) {
                            price = parseFloat(match[1].replace(',', ''));
                        }
                    }
                    
                    // Condition - .s-card__subtitle .su-styled-text
                    const conditionElem = item.querySelector('.s-card__subtitle .su-styled-text');
                    const condition = conditionElem ? conditionElem.textContent.trim() : 'Unknown';
                    
                    // Shipping - search in attribute rows
                    let shipping = null;
                    const attrRows = item.querySelectorAll('.s-card__attribute-row .su-styled-text');
                    attrRows.forEach(el => {
                        const text = el.textContent.trim();
                        if (text.includes('envío') || text.includes('shipping') || text.includes('por el envío')) {
                            shipping = text;
                        }
                    });
                    
                    // Link - a.s-card__link
                    const linkElem = item.querySelector('a.s-card__link');
                    const link = linkElem ? linkElem.href : null;
                    
                    // Sold status - .s-card__caption .su-styled-text
                    const soldElem = item.querySelector('.s-card__caption .su-styled-text');
                    const isSold = soldElem && (soldElem.textContent.includes('Vendido') || soldElem.textContent.includes('Sold'));
                    
                    // Sold date from caption
                    const soldDate = soldElem ? soldElem.textContent.trim() : null;
                    
                    if (price) {
                        return {
                            title: title,
                            price: price,
                            condition: condition,
                            shipping: shipping,
                            link: link,
                            sold: isSold,
                            sold_date: soldDate
                        };
                    }
                    return null;
                } catch (e) {
                    console.error('Error extracting item:', e);
                    return null;
                }
            }).filter(item => item !== null);
        }""")
        
        # Filter and limit
        valid_listings = [l for l in listings if l][:max_results]
        
        print(f"\n{'='*60}")
        print(f"✅ Extracted {len(valid_listings)} valid listings")
        print(f"{'='*60}")
        
        if valid_listings:
            print("\n📋 Sample listings:")
            for i, listing in enumerate(valid_listings[:5], 1):
                print(f"\n{i}. {listing['title'][:60]}...")
                print(f"   💰 Price: ${listing['price']}")
                print(f"   📦 Condition: {listing['condition']}")
                print(f"   🚚 Shipping: {listing.get('shipping', 'N/A')}")
                print(f"   📅 {listing.get('sold_date', 'N/A')}")
        
        # Save HTML for analysis
        html_path = "experiments/ebay_search_v2.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n💾 HTML saved: {html_path} ({len(html):,} chars)")
        
        browser.close()
        print("\n🎉 Scraping complete!\n")
        
        return html, valid_listings


def analyze_prices(listings):
    """Analyze price data from scraped listings"""
    if not listings:
        print("❌ No listings to analyze")
        return {}
    
    prices = [l['price'] for l in listings if l.get('price')]
    
    if not prices:
        print("❌ No valid prices found")
        return {}
    
    analysis = {
        'count': len(prices),
        'min': min(prices),
        'max': max(prices),
        'median': sorted(prices)[len(prices) // 2],
        'average': sum(prices) / len(prices),
        'sold_count': sum(1 for l in listings if l.get('sold'))
    }
    
    print(f"\n📊 PRICE ANALYSIS")
    print(f"{'='*60}")
    print(f"Total listings: {analysis['count']}")
    print(f"Sold listings: {analysis['sold_count']}")
    print(f"Price range: ${analysis['min']:.2f} - ${analysis['max']:.2f}")
    print(f"Median price: ${analysis['median']:.2f}")
    print(f"Average price: ${analysis['average']:.2f}")
    print(f"{'='*60}")
    
    return analysis


if __name__ == "__main__":
    # Scrape eBay
    html, listings = fetch_ebay_search_with_playwright("Nike Sneakers", max_results=30)
    
    # Analyze prices
    analysis = analyze_prices(listings)
    
    # Save results
    results = {
        'query': 'Nike Sneakers',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'listings_count': len(listings),
        'listings': listings,
        'analysis': analysis
    }
    
    results_path = 'experiments/ebay_results_v2.json'
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Results saved: {results_path}")
    print(f"\n✅ Extraction successful: {len(listings)} listings")
    print(f"📈 Ready to compare with OpenAI web_search method!")
