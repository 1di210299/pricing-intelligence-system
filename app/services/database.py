"""Database connection and query module."""
import asyncpg
from typing import List, Dict, Optional
from app.config import settings
from app.utils.logger import logger


class DatabaseClient:
    """PostgreSQL database client."""
    
    def __init__(self):
        """Initialize database client."""
        self.pool: Optional[asyncpg.Pool] = None
        
    async def connect(self):
        """Create database connection pool."""
        if not settings.database_url:
            raise ValueError("DATABASE_URL not configured")
        
        try:
            self.pool = await asyncpg.create_pool(
                settings.database_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("✅ Database connection pool created")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def search_by_keywords(self, search_term: str) -> List[Dict]:
        """Search for items by keywords in brand, category, or subcategory.
        
        Args:
            search_term: Search term (e.g., 'Nike Sneakers')
            
        Returns:
            List of matching sales records
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        # Normalize search term
        search_term = search_term.strip().lower()
        
        # Try exact match first
        query = """
            SELECT 
                item_id, department, category, subcategory, brand,
                production_date, sold_date, days_to_sell,
                production_price, sold_price
            FROM sales_data
            WHERE 
                LOWER(brand) LIKE $1
                OR LOWER(category) LIKE $1
                OR LOWER(subcategory) LIKE $1
        """
        
        pattern = f"%{search_term}%"
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, pattern)
            
            # If no results, try word-by-word search
            if not rows:
                words = search_term.split()
                if len(words) > 1:
                    logger.info(f"No exact match for '{search_term}', trying word-by-word search...")
                    
                    # Build dynamic query for OR conditions
                    conditions = []
                    params = []
                    for i, word in enumerate(words, 1):
                        word_pattern = f"%{word}%"
                        conditions.append(f"(LOWER(brand) LIKE ${i} OR LOWER(category) LIKE ${i} OR LOWER(subcategory) LIKE ${i})")
                        params.append(word_pattern)
                    
                    word_query = f"""
                        SELECT 
                            item_id, department, category, subcategory, brand,
                            production_date, sold_date, days_to_sell,
                            production_price, sold_price
                        FROM sales_data
                        WHERE {' OR '.join(conditions)}
                    """
                    
                    rows = await conn.fetch(word_query, *params)
            
            # Convert to list of dicts
            results = []
            for row in rows:
                results.append({
                    'item_id': row['item_id'],
                    'department': row['department'],
                    'category': row['category'],
                    'subcategory': row['subcategory'],
                    'brand': row['brand'],
                    'production_date': row['production_date'],
                    'sold_date': row['sold_date'],
                    'days_to_sell': row['days_to_sell'],
                    'production_price': row['production_price'],
                    'sold_price': row['sold_price']
                })
            
            logger.info(f"Found {len(results)} items matching '{search_term}'")
            return results
    
    async def search_by_brand(self, brand: str) -> List[Dict]:
        """Search for items by brand.
        
        Args:
            brand: Brand name
            
        Returns:
            List of matching sales records
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        query = """
            SELECT 
                item_id, department, category, subcategory, brand,
                production_date, sold_date, days_to_sell,
                production_price, sold_price
            FROM sales_data
            WHERE LOWER(brand) = LOWER($1)
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, brand)
            
            results = []
            for row in rows:
                results.append({
                    'item_id': row['item_id'],
                    'department': row['department'],
                    'category': row['category'],
                    'subcategory': row['subcategory'],
                    'brand': row['brand'],
                    'production_date': row['production_date'],
                    'sold_date': row['sold_date'],
                    'days_to_sell': row['days_to_sell'],
                    'production_price': row['production_price'],
                    'sold_price': row['sold_price']
                })
            
            logger.info(f"Found {len(results)} items for brand '{brand}'")
            return results
    
    async def search_by_category(self, category: str) -> List[Dict]:
        """Search for items by category.
        
        Args:
            category: Category name
            
        Returns:
            List of matching sales records
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        query = """
            SELECT 
                item_id, department, category, subcategory, brand,
                production_date, sold_date, days_to_sell,
                production_price, sold_price
            FROM sales_data
            WHERE LOWER(category) = LOWER($1)
        """
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, category)
            
            results = []
            for row in rows:
                results.append({
                    'item_id': row['item_id'],
                    'department': row['department'],
                    'category': row['category'],
                    'subcategory': row['subcategory'],
                    'brand': row['brand'],
                    'production_date': row['production_date'],
                    'sold_date': row['sold_date'],
                    'days_to_sell': row['days_to_sell'],
                    'production_price': row['production_price'],
                    'sold_price': row['sold_price']
                })
            
            logger.info(f"Found {len(results)} items for category '{category}'")
            return results
    
    async def get_statistics(self) -> Dict:
        """Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        query = """
            SELECT 
                COUNT(*) as total_records,
                COUNT(*) FILTER (WHERE sold_date IS NOT NULL) as sold_items,
                COUNT(DISTINCT brand) as unique_brands,
                COUNT(DISTINCT category) as unique_categories,
                COUNT(DISTINCT subcategory) as unique_subcategories
            FROM sales_data
        """
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query)
            
            return {
                'total_records': row['total_records'],
                'sold_items': row['sold_items'],
                'unique_brands': row['unique_brands'],
                'unique_categories': row['unique_categories'],
                'unique_subcategories': row['unique_subcategories']
            }


# Global database client instance
db_client = DatabaseClient()
