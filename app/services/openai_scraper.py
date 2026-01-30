"""
OpenAI-based web scraper for eBay pricing data.
Uses OpenAI's web search capabilities to extract market pricing information.
"""
import os
import json
from typing import Optional
from openai import OpenAI
from app.models.pricing import MarketData


class OpenAIEbayScraper:
    """Uses OpenAI API with web search to extract eBay pricing data."""
    
    def __init__(self):
        """Initialize OpenAI client with API key from environment."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        self.client = OpenAI(api_key=api_key)
        print("✅ OpenAI scraper initialized")
    
    async def search_ebay_prices(self, product_name: str) -> Optional[MarketData]:
        """
        Search eBay for sold listings and extract pricing data using OpenAI.
        
        Args:
            product_name: Name or description of the product to search
            
        Returns:
            MarketData object with pricing information, or None if search fails
        """
        print(f"🔍 Searching eBay with OpenAI for: {product_name}")
        
        try:
            # Create prompt for OpenAI to search and extract eBay data
            prompt = f"""Search eBay for SOLD listings of "{product_name}". 
            
Extract the following information from the search results:
1. Median sold price (in USD)
2. Minimum price from sold listings
3. Maximum price from sold listings  
4. Number of sold listings found

Return the data ONLY as a valid JSON object with this exact structure:
{{
    "median_price": <number or null>,
    "min_price": <number or null>,
    "max_price": <number or null>,
    "sample_size": <integer>
}}

Important: 
- Focus on COMPLETED/SOLD listings, not active listings
- Prices should be numeric values without currency symbols
- If no data found, return null for prices and 0 for sample_size
- Return ONLY the JSON object, no additional text"""

            print("🤖 Calling OpenAI API with web search...")
            
            # Call OpenAI Responses API with web search tool
            response = self.client.responses.create(
                model="gpt-4o",
                tools=[
                    {
                        "type": "web_search",
                        "filters": {
                            "allowed_domains": ["ebay.com"]
                        }
                    }
                ],
                tool_choice="auto",
                input=prompt
            )
            
            # Extract the response content
            content = response.output_text
            print(f"📥 OpenAI Response: {content}")
            
            # Parse JSON response
            # Remove markdown code blocks if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            
            # Create MarketData object
            market_data = MarketData(
                median_price=data.get("median_price"),
                min_price=data.get("min_price"),
                max_price=data.get("max_price"),
                sample_size=data.get("sample_size", 0)
            )
            
            print(f"✅ Extracted data: median=${market_data.median_price}, range=${market_data.min_price}-${market_data.max_price}, samples={market_data.sample_size}")
            
            return market_data
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON response: {e}")
            print(f"Raw content: {content}")
            return None
            
        except Exception as e:
            print(f"❌ OpenAI scraping error: {e}")
            return None
