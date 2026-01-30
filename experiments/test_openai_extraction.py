"""
Test sending eBay HTML directly to OpenAI to extract pricing data.
This shows how much data OpenAI can extract vs direct scraping.
"""
import sys
sys.path.append('/Users/1di/coding_challenge')

import asyncio
from openai import OpenAI
from app.config import settings


async def test_openai_extraction():
    """Test OpenAI extraction on saved HTML."""
    print("=" * 80)
    print("🤖 Testing OpenAI HTML Analysis")
    print("=" * 80)
    
    # Load the HTML we scraped
    try:
        with open('experiments/ebay_search_raw.html', 'r', encoding='utf-8') as f:
            html = f.read()
        print(f"✅ Loaded HTML: {len(html):,} characters")
    except FileNotFoundError:
        print("❌ No HTML file found. Run ebay_html_scraper.py first.")
        return
    
    # Extract just the body (like our production code does)
    import re
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL | re.IGNORECASE)
    if body_match:
        body_html = body_match.group(1)
        print(f"📄 Extracted body: {len(body_html):,} characters")
    else:
        body_html = html
        print("⚠️  No body tag found, using full HTML")
    
    # Truncate if too long (OpenAI has limits)
    max_chars = 100000
    if len(body_html) > max_chars:
        body_html = body_html[:max_chars]
        print(f"✂️  Truncated to {max_chars:,} characters")
    
    # Call OpenAI
    client = OpenAI(api_key=settings.openai_api_key)
    
    prompt = """You are analyzing eBay search results HTML. Extract ALL pricing information you can find.

For each listing found, extract:
- Product title
- Price (in USD)
- Condition
- Whether it was sold or is active
- Sold date if available

Return a JSON array of listings. Extract as many as possible.

HTML to analyze:
""" + body_html[:50000]  # First 50k chars for context
    
    print("\n🔄 Sending to OpenAI...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        result = response.choices[0].message.content
        print("\n" + "=" * 80)
        print("📊 OpenAI RESULTS")
        print("=" * 80)
        print(result)
        
        # Try to parse as JSON
        import json
        try:
            listings = json.loads(result)
            print(f"\n✅ Successfully parsed {len(listings)} listings")
            
            # Calculate stats
            if listings and isinstance(listings, list):
                prices = [item.get('price', 0) for item in listings if item.get('price')]
                if prices:
                    print(f"\n📈 Statistics:")
                    print(f"   Total items: {len(listings)}")
                    print(f"   Price range: ${min(prices):.2f} - ${max(prices):.2f}")
                    print(f"   Median: ${sorted(prices)[len(prices)//2]:.2f}")
                    print(f"   Average: ${sum(prices)/len(prices):.2f}")
                    
                    sold_items = [item for item in listings if item.get('is_sold')]
                    print(f"   Sold items: {len(sold_items)}")
        except json.JSONDecodeError:
            print("\n⚠️  Response is not valid JSON, but OpenAI provided analysis above")
        
    except Exception as e:
        print(f"❌ Error calling OpenAI: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_openai_extraction())
