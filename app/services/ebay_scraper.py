"""
eBay scraper using Playwright + ScrapFly for production-grade web scraping
Replaces OpenAI web_search with direct HTML extraction
"""
import asyncio
import json
import re
from typing import Optional, List, Dict
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from scrapfly import ScrapflyClient, ScrapeConfig, ScrapeApiResponse

from app.models.pricing import MarketData
from app.utils.logger import get_logger

logger = get_logger(__name__)


class eBayScrapFlyClient:
    """eBay scraper using Playwright with ScrapFly anti-bot protection"""
    
    def __init__(self, scrapfly_api_key: str):
        """
        Initialize eBay scraper with ScrapFly
        
        Args:
            scrapfly_api_key: ScrapFly API key for anti-bot protection
        """
        self.scrapfly = ScrapflyClient(key=scrapfly_api_key)
        logger.info("eBay ScrapFly client initialized")
    
    async def get_market_pricing(self, search_term: str, max_results: int = 30) -> MarketData:
        """
        Get market pricing data from eBay sold listings
        
        Args:
            search_term: Product to search (e.g., "Nike Sneakers")
            max_results: Maximum number of listings to extract
            
        Returns:
            MarketData with aggregated pricing information
        """
        logger.info(f"Fetching eBay market data for: {search_term}")
        
        try:
            # Build eBay sold listings URL
            encoded_query = quote_plus(search_term)
            url = (
                f"https://www.ebay.com/sch/i.html"
                f"?_nkw={encoded_query}"
                f"&_sacat=0"
                f"&LH_Sold=1"
                f"&LH_Complete=1"
                f"&_sop=12"
                f"&_ipg=60"
            )
            
            logger.info(f"Scraping URL: {url}")
            
            # Use ScrapFly to bypass anti-bot protection
            result = await asyncio.to_thread(
                self.scrapfly.scrape,
                ScrapeConfig(
                    url=url,
                    render_js=True,  # Enable JavaScript rendering
                    country='US',
                    asp=True,  # Anti-scraping protection
                    retry=False,  # Disable retry to allow custom timeout
                    timeout=60000  # 60 seconds
                )
            )
            
            # Extract listings from HTML
            html = result.content
            listings = self._extract_listings_from_html(html, max_results)
            
            if not listings:
                logger.warning(f"No listings found for: {search_term}")
                return MarketData(
                    median_price=None,
                    average_price=None,
                    min_price=None,
                    max_price=None,
                    sample_size=0,
                    sold_listings_count=0
                )
            
            # Calculate statistics
            prices = [l['price'] for l in listings if l.get('price')]
            sold_count = sum(1 for l in listings if l.get('sold'))
            
            market_data = MarketData(
                median_price=self._calculate_median(prices) if prices else None,
                average_price=sum(prices) / len(prices) if prices else None,
                min_price=min(prices) if prices else None,
                max_price=max(prices) if prices else None,
                sample_size=len(listings),
                sold_listings_count=sold_count
            )
            
            logger.info(
                f"Extracted {len(listings)} listings - "
                f"Median: ${market_data.median_price:.2f}" if market_data.median_price else "No price data"
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error scraping eBay for {search_term}: {str(e)}")
            # Return empty data on error
            return MarketData(
                median_price=None,
                average_price=None,
                min_price=None,
                max_price=None,
                sample_size=0,
                sold_listings_count=0
            )
    
    def _extract_listings_from_html(self, html: str, max_results: int) -> List[Dict]:
        """
        Extract listing data from eBay HTML
        
        Uses regex patterns to extract data from the HTML structure
        More reliable than BeautifulSoup for dynamic content
        """
        listings = []
        
        # Pattern to find .s-card items with all data
        # eBay structure: <li class="s-card...">...</li>
        card_pattern = r'<li[^>]*class="[^"]*s-card[^"]*"[^>]*>.*?</li>'
        cards = re.findall(card_pattern, html, re.DOTALL)
        
        for card_html in cards[:max_results]:
            try:
                listing = {}
                
                # Extract title
                title_match = re.search(r'<span class="su-styled-text[^"]*">([^<]+)</span>', card_html)
                if title_match:
                    listing['title'] = title_match.group(1).strip()
                else:
                    continue  # Skip if no title
                
                # Extract price - handles S/., $, €, £
                price_match = re.search(r'class="[^"]*s-card__price[^"]*"[^>]*>([^<]+)</span>', card_html)
                if price_match:
                    price_text = price_match.group(1).strip()
                    # Extract numeric value
                    numeric_match = re.search(r'[S$£€]\/?\s*\.?\s*([\d,]+\.?\d*)', price_text)
                    if numeric_match:
                        price_str = numeric_match.group(1).replace(',', '')
                        listing['price'] = float(price_str)
                
                # Extract condition
                condition_match = re.search(r'<span class="su-styled-text secondary[^"]*">([^<]+)</span>', card_html)
                if condition_match:
                    listing['condition'] = condition_match.group(1).strip()
                
                # Check if sold
                sold_match = re.search(r'Vendido|Sold', card_html)
                listing['sold'] = bool(sold_match)
                
                # Only add if we have price
                if listing.get('price'):
                    listings.append(listing)
                    
            except Exception as e:
                logger.debug(f"Error parsing listing: {e}")
                continue
        
        return listings
    
    @staticmethod
    def _calculate_median(numbers: List[float]) -> float:
        """Calculate median of a list of numbers"""
        if not numbers:
            return 0.0
        sorted_nums = sorted(numbers)
        n = len(sorted_nums)
        if n % 2 == 0:
            return (sorted_nums[n//2 - 1] + sorted_nums[n//2]) / 2
        return sorted_nums[n//2]


class eBayPlaywrightClient:
    """
    Fallback eBay scraper using pure Playwright (no ScrapFly)
    Used when ScrapFly quota is exceeded or for local testing
    """
    
    async def get_market_pricing(self, search_term: str, max_results: int = 30) -> MarketData:
        """
        Get market pricing using Playwright directly
        
        Args:
            search_term: Product to search
            max_results: Max listings to extract
            
        Returns:
            MarketData with pricing information
        """
        logger.info(f"Fetching eBay data with Playwright for: {search_term}")
        
        async with async_playwright() as p:
            try:
                # Launch browser
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                # Build URL
                encoded_query = quote_plus(search_term)
                url = (
                    f"https://www.ebay.com/sch/i.html"
                    f"?_nkw={encoded_query}"
                    f"&_sacat=0"
                    f"&LH_Sold=1"
                    f"&LH_Complete=1"
                    f"&_sop=12"
                )
                
                # Navigate
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for listings
                try:
                    await page.wait_for_selector('.s-card', timeout=10000)
                except PlaywrightTimeout:
                    logger.warning("Timeout waiting for .s-card selector")
                
                # Additional wait for JS
                await asyncio.sleep(3)
                
                # Extract listings with JavaScript
                listings = await page.evaluate("""() => {
                    const items = Array.from(document.querySelectorAll('.s-card'));
                    
                    return items.map(item => {
                        try {
                            const titleElem = item.querySelector('.s-card__title .su-styled-text');
                            const title = titleElem ? titleElem.textContent.trim() : null;
                            
                            if (!title || title.toLowerCase().includes('shop on ebay')) {
                                return null;
                            }
                            
                            const priceElem = item.querySelector('.s-card__price');
                            let price = null;
                            if (priceElem) {
                                const priceText = priceElem.textContent.trim();
                                const match = priceText.match(/[S$£€]\/?\s*\.?\s*([\d,]+\.?\d*)/);
                                if (match) {
                                    price = parseFloat(match[1].replace(',', ''));
                                }
                            }
                            
                            const conditionElem = item.querySelector('.s-card__subtitle .su-styled-text');
                            const condition = conditionElem ? conditionElem.textContent.trim() : 'Unknown';
                            
                            const soldElem = item.querySelector('.s-card__caption .su-styled-text');
                            const isSold = soldElem && (soldElem.textContent.includes('Vendido') || soldElem.textContent.includes('Sold'));
                            
                            if (price) {
                                return {
                                    title: title,
                                    price: price,
                                    condition: condition,
                                    sold: isSold
                                };
                            }
                            return null;
                        } catch (e) {
                            return null;
                        }
                    }).filter(item => item !== null);
                }""")
                
                await browser.close()
                
                # Filter and limit
                valid_listings = [l for l in listings if l][:max_results]
                
                if not valid_listings:
                    logger.warning(f"No listings found for: {search_term}")
                    return MarketData(
                        median_price=None,
                        average_price=None,
                        min_price=None,
                        max_price=None,
                        sample_size=0,
                        sold_listings_count=0
                    )
                
                # Calculate statistics
                prices = [l['price'] for l in valid_listings]
                sold_count = sum(1 for l in valid_listings if l.get('sold'))
                
                sorted_prices = sorted(prices)
                median = sorted_prices[len(sorted_prices) // 2] if sorted_prices else None
                
                market_data = MarketData(
                    median_price=median,
                    average_price=sum(prices) / len(prices) if prices else None,
                    min_price=min(prices) if prices else None,
                    max_price=max(prices) if prices else None,
                    sample_size=len(valid_listings),
                    sold_listings_count=sold_count
                )
                
                logger.info(f"Extracted {len(valid_listings)} listings with Playwright")
                return market_data
                
            except Exception as e:
                logger.error(f"Playwright scraping error: {str(e)}")
                return MarketData(
                    median_price=None,
                    average_price=None,
                    min_price=None,
                    max_price=None,
                    sample_size=0,
                    sold_listings_count=0
                )
