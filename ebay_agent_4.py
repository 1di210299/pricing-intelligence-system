import asyncio
import re
import statistics
import logging
import argparse
import json
import sys
import random
from playwright.async_api import async_playwright

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("EbayPricingAgent")

class EbayPricingAgent:
    """
    Milestone 3.5: Stateful / Persistent Session Edition
    ----------------------------------------------------
    Designed for Integration:
    Allows the browser to stay open across multiple separate search calls
    to prevent eBay from detecting "rapid browser restarts".
    """
    
    def __init__(self, headless=False):
        self.headless = headless
        self.base_url = "https://www.ebay.com/sch/i.html"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def start_session(self):
        """Initializes the browser session. Call this ONCE before your loop."""
        if self.page: return # Already started
        
        logger.info("Starting Persistent Browser Session...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu'
            ]
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1366, 'height': 768},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        await self.page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9'
        })

    async def close_session(self):
        """Closes the browser. Call this ONCE after your loop."""
        if self.browser:
            logger.info("Closing Browser Session.")
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.page = None

    def _clean_price(self, price_str):
        if not price_str: return None
        clean = price_str.replace(",", "").replace("US", "").replace("$", "").replace("RM", "").strip()
        match = re.search(r"(\d+\.?\d*)", clean)
        return float(match.group(1)) if match else None

    def _normalize_condition(self, text):
        if not text: return "Unknown"
        text = text.lower()
        if "brand new" in text or "new" in text or "sealed" in text:
            return "New"
        elif "pre-owned" in text or "used" in text or "refurbished" in text or "open box" in text:
            return "Used"
        return "Unknown"

    def _is_relevant(self, title, keyword):
        if not title: return False
        title_lower = title.lower()
        keyword_terms = keyword.lower().split()
        for term in keyword_terms:
            if len(term) < 2: continue 
            if term in title_lower: return True
        return False

    def _calculate_group_stats(self, prices):
        if not prices: return None
        prices.sort()
        if len(prices) >= 4:
            mid = len(prices) // 2
            q1 = statistics.median(prices[:mid])
            q3 = statistics.median(prices[mid:])
            iqr = q3 - q1
            lower = q1 - (1.5 * iqr)
            upper = q3 + (1.5 * iqr)
            clean_prices = [p for p in prices if lower <= p <= upper]
        else:
            clean_prices = prices
        if not clean_prices: return None
        return {
            "count": len(clean_prices),
            "min": min(clean_prices),
            "max": max(clean_prices),
            "avg": round(statistics.mean(clean_prices), 2),
            "median": round(statistics.median(clean_prices), 2)
        }

    async def _handle_popups(self):
        try:
            selectors = ["button[aria-label='Close']", ".x-overlay__close", "button.onetrust-close-btn-handler"]
            for s in selectors:
                if await self.page.locator(s).is_visible(timeout=500):
                    await self.page.click(s)
        except: pass

    async def get_pricing_data(self, keyword, limit=60):
        """
        Main Search Method.
        Requires start_session() to be called first.
        """
        # Auto-start if user forgot to call start_session()
        if not self.page:
            await self.start_session()

        logger.info(f"Searching for: {keyword}")
        
        try:
            target_url = f"{self.base_url}?_nkw={keyword}&LH_Sold=1&LH_Complete=1&_ipg=60"
            await self.page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            await self._handle_popups()
            
            # Crucial: Human Delay between searches
            await asyncio.sleep(random.uniform(2, 4))

            results = []
            links = await self.page.locator("a[href*='/itm/']").all()
            
            if len(links) == 0:
                logger.warning(f"No links found for '{keyword}'. Possible bot block.")
                return {"status": "error", "message": "No data/Blocked"}

            for i, link in enumerate(links):
                if len(results) >= limit: break
                try:
                    title = await link.inner_text(timeout=1000)
                    title = title.replace("Opens in a new window or tab", "").strip()
                    if "Shop on eBay" in title or len(title) < 5: continue
                    if not self._is_relevant(title, keyword): continue

                    url = await link.get_attribute("href")
                    container = link.locator("xpath=./ancestor::li | ./ancestor::div[contains(@class, 's-item')]").first
                    full_text = await container.inner_text(timeout=1000)
                    
                    price = None
                    match = re.search(r"(US\s?)?(\$|RM|MYR)\s?[\d,]+(?:\.\d{2})?", full_text)
                    if match: price = self._clean_price(match.group(0))
                    if price is None: continue

                    condition_raw = "Unknown"
                    try:
                        sec_info = container.locator(".SECONDARY_INFO")
                        if await sec_info.count() > 0: condition_raw = await sec_info.first.inner_text()
                        else:
                            if "New" in full_text: condition_raw = "Brand New"
                            elif "Pre-Owned" in full_text: condition_raw = "Pre-Owned"
                    except: pass
                    
                    condition_group = self._normalize_condition(condition_raw)
                    results.append({
                        "title": title, "price": price, 
                        "condition_group": condition_group, "url": url
                    })
                except: continue
            
            if not results: return {"status": "no_data", "data": None}

            new_items = [r['price'] for r in results if r['condition_group'] == 'New']
            used_items = [r['price'] for r in results if r['condition_group'] == 'Used']

            return {
                "status": "success",
                "keyword": keyword,
                "pricing": {
                    "overall": self._calculate_group_stats([r['price'] for r in results]),
                    "new_condition": self._calculate_group_stats(new_items),
                    "used_condition": self._calculate_group_stats(used_items)
                }
            }
        except Exception as e:
            logger.error(f"Error: {e}")
            return {"status": "error", "message": str(e)}

# --- DEMONSTRATION OF INTEGRATION USAGE ---
async def integration_demo():
    # 1. Initialize ONCE
    agent = EbayPricingAgent(headless=False)
    await agent.start_session()
    
    # 2. Loop through your own list (passed one by one)
    my_items = ["Sony PlayStation 5", "Canon R8", "iPhone 13"]
    
    for item in my_items:
        # Pass ONE string at a time, as Zahra requested
        data = await agent.get_pricing_data(item)
        print(f"Result for {item}: {data.get('status')}")
    
    # 3. Close ONCE
    await agent.close_session()

if __name__ == "__main__":
    asyncio.run(integration_demo())