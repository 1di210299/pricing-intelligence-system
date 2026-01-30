"""eBay scraping client using ebay_agent_4."""
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

# Add parent directory to path to import ebay_agent_4
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.ebay_agent_4 import EbayPricingAgent

from app.models.pricing import MarketData
from app.utils.logger import get_logger

logger = get_logger(__name__)


class eBayAPIError(Exception):
    """Custom exception for eBay API errors."""
    pass


class eBayClient:
    """Client for scraping eBay pricing data using Playwright."""
    
    def __init__(self, headless: bool = True):
        """Initialize eBay scraping client."""
        self.agent = EbayPricingAgent(headless=headless)
        self.session_started = False
        logger.info("eBay scraping client initialized")
    
    async def start_session(self):
        """Start persistent browser session."""
        if not self.session_started:
            await self.agent.start_session()
            self.session_started = True
            logger.info("eBay agent session started")
    
    async def close_session(self):
        """Close browser session."""
        if self.session_started:
            await self.agent.close_session()
            self.session_started = False
            logger.info("eBay agent session closed")
    
    async def get_market_pricing(self, search_term: str) -> MarketData:
        """
        Get market pricing data for a search term from eBay.
        
        Args:
            search_term: Product name or UPC to search for
            
        Returns:
            MarketData: Market pricing information
            
        Raises:
            eBayAPIError: If scraping fails
        """
        try:
            # Ensure session is started
            if not self.session_started:
                await self.start_session()
            
            logger.info(f"Searching eBay for: {search_term}")
            result = await self.agent.get_pricing_data(search_term)
            
            if result.get("status") != "success":
                logger.warning(f"eBay search failed for {search_term}: {result.get('message')}")
                return MarketData(
                    sample_size=0,
                    active_listings_count=0,
                    sold_listings_count=0,
                    low_confidence=True
                )
            
            pricing = result.get("pricing", {})
            overall = pricing.get("overall")
            new_condition = pricing.get("new_condition")
            used_condition = pricing.get("used_condition")
            
            if not overall:
                return MarketData(
                    sample_size=0,
                    active_listings_count=0,
                    sold_listings_count=0,
                    low_confidence=True
                )
            
            # Build market data from scraped results
            market_data = MarketData(
                median_price=overall.get("median"),
                average_price=overall.get("avg"),
                min_price=overall.get("min"),
                max_price=overall.get("max"),
                sample_size=overall.get("count", 0),
                timestamp=datetime.utcnow(),
                active_listings_count=0,  # Scraper returns sold items
                sold_listings_count=overall.get("count", 0),
                low_confidence=overall.get("count", 0) < 5,
                metadata={
                    "new_condition": new_condition,
                    "used_condition": used_condition,
                    "keyword": result.get("keyword")
                }
            )
            
            logger.info(
                f"Retrieved market data for '{search_term}': "
                f"median=${market_data.median_price}, samples={market_data.sample_size}"
            )
            
            return market_data
            
        except Exception as e:
            logger.error(f"Error fetching market data for '{search_term}': {str(e)}")
            raise eBayAPIError(f"Failed to fetch market data: {str(e)}") from e
    
    def _search_active_listings(self, upc: str, max_results: int = 50) -> list[float]:
        """
        Search for active listings by UPC.
        
        Args:
            upc: UPC code
            max_results: Maximum number of results to fetch
            
        Returns:
            List of prices from active listings
        """
        if not self.app_id:
            logger.warning("Skipping eBay API call - no App ID configured")
            return []
        
        params = {
            "OPERATION-NAME": "findItemsByProduct",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": self.app_id,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "productId.@type": "UPC",
            "productId": upc,
            "paginationInput.entriesPerPage": str(max_results),
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._extract_prices_from_response(data)
            
        except requests.RequestException as e:
            logger.error(f"eBay API request failed: {str(e)}")
            # Return empty list instead of raising to allow graceful degradation
            return []
    
    def _search_completed_listings(self, upc: str, max_results: int = 50) -> list[float]:
        """
        Search for completed/sold listings by UPC.
        
        Args:
            upc: UPC code
            max_results: Maximum number of results to fetch
            
        Returns:
            List of prices from sold listings
        """
        if not self.app_id:
            logger.warning("Skipping eBay API call - no App ID configured")
            return []
        
        # Calculate date range (last 90 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        params = {
            "OPERATION-NAME": "findCompletedItems",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": self.app_id,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "productId.@type": "UPC",
            "productId": upc,
            "itemFilter(0).name": "SoldItemsOnly",
            "itemFilter(0).value": "true",
            "paginationInput.entriesPerPage": str(max_results),
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._extract_prices_from_response(data)
            
        except requests.RequestException as e:
            logger.error(f"eBay API request for completed items failed: {str(e)}")
            # Return empty list instead of raising to allow graceful degradation
            return []
    
    def _extract_prices_from_response(self, data: Dict[str, Any]) -> list[float]:
        """
        Extract prices from eBay API response.
        
        Args:
            data: JSON response from eBay API
            
        Returns:
            List of prices as floats
        """
        prices = []
        
        try:
            # Navigate the eBay API response structure
            search_result = data.get("findItemsByProductResponse", [{}])[0]
            search_result = search_result or data.get("findCompletedItemsResponse", [{}])[0]
            
            if not search_result:
                return prices
            
            items = search_result.get("searchResult", [{}])[0].get("item", [])
            
            for item in items:
                # Get selling price
                selling_status = item.get("sellingStatus", [{}])[0]
                current_price = selling_status.get("currentPrice", [{}])[0]
                
                if current_price and "__value__" in current_price:
                    try:
                        price = float(current_price["__value__"])
                        if price > 0:  # Only include positive prices
                            prices.append(price)
                    except (ValueError, TypeError):
                        continue
            
        except (KeyError, IndexError, TypeError) as e:
            logger.warning(f"Error parsing eBay response: {str(e)}")
        
        return prices
