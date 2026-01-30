"""eBay scraping client using OpenAI web search."""
import os
from typing import Optional
from dotenv import load_dotenv

from app.models.pricing import MarketData
from app.services.openai_scraper import OpenAIEbayScraper
from app.utils.logger import get_logger

# Load environment variables from .env file
load_dotenv()

logger = get_logger(__name__)


class eBayAPIError(Exception):
    """Custom exception for eBay API errors."""
    pass


class eBayClient:
    """Client for scraping eBay pricing data using OpenAI."""
    
    def __init__(self, headless: bool = True):
        """Initialize eBay scraping client with OpenAI."""
        self.scraper = OpenAIEbayScraper()
        self.session_started = True  # OpenAI doesn't need session management
        logger.info("eBay OpenAI scraping client initialized")
    
    async def start_session(self):
        """No-op for OpenAI (no session needed)."""
        self.session_started = True
        logger.info("eBay OpenAI client ready")
    
    async def close_session(self):
        """No-op for OpenAI (no session to close)."""
        self.session_started = False
        logger.info("eBay OpenAI client closed")
    
    
    async def get_market_pricing(self, search_term: str) -> MarketData:
        """
        Get market pricing data for a search term from eBay using OpenAI.
        
        Args:
            search_term: Product name or UPC to search for
            
        Returns:
            MarketData: Market pricing information
            
        Raises:
            eBayAPIError: If scraping fails
        """
        try:
            logger.info(f"Searching eBay with OpenAI for: {search_term}")
            print(f"🔍 Searching eBay with OpenAI for: {search_term}")
            
            # Use OpenAI to search eBay
            market_data = await self.scraper.search_ebay_prices(search_term)
            
            if market_data is None or market_data.sample_size == 0:
                print(f"⚠️ No eBay data found for: {search_term}")
                logger.warning(f"eBay search returned no data for {search_term}")
                return MarketData(
                    sample_size=0,
                    active_listings_count=0,
                    sold_listings_count=0,
                    low_confidence=True
                )
            
            print(f"✅ eBay data retrieved: median=${market_data.median_price}, samples={market_data.sample_size}")
            logger.info(
                f"Retrieved market data for '{search_term}': "
                f"median=${market_data.median_price}, samples={market_data.sample_size}"
            )
            
            return market_data
            
        except Exception as e:
            print(f"❌ Error fetching market data: {e}")
            logger.error(f"Error fetching market data for '{search_term}': {str(e)}")
            raise eBayAPIError(f"Failed to fetch market data: {str(e)}") from e
