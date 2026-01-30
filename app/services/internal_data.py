"""Internal data processing service for thrift sales CSV and PostgreSQL."""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.pricing import InternalData
from app.utils.logger import get_logger
from app.config import settings

logger = get_logger(__name__)


class InternalDataProcessor:
    """Service for processing internal thrift sales data from CSV or PostgreSQL."""
    
    def __init__(self, csv_path: Optional[str] = None, db_client=None):
        """
        Initialize the processor.
        
        Args:
            csv_path: Path to CSV file with internal data (used if database disabled)
            db_client: Database client instance (used if database enabled)
        """
        self.db_client = db_client
        self.use_database = settings.use_database and db_client is not None
        
        if csv_path is None:
            csv_path = "thrift_sales_12_weeks_with_subcategory.csv"
        
        self.csv_path = Path(csv_path)
        self.data: Optional[pd.DataFrame] = None
        self.category_stats: Dict[str, Dict[str, float]] = {}
        
        # Load CSV data if not using database
        if not self.use_database and self.csv_path.exists():
            self.load_data()
            logger.info("Using CSV data source")
        elif self.use_database:
            logger.info("Using PostgreSQL data source")
        else:
            logger.warning("No data source configured")
    
    def load_data(self) -> None:
        """
        Load internal data from CSV file.
        
        Expected CSV columns:
            - item_id: Unique item ID
            - department: Department (Mens, Womens, Children)
            - category: Category (Shoes, Tops, Bottoms, etc.)
            - subcategory: Subcategory (Sneakers, T-Shirt, etc.)
            - brand: Brand name
            - production_date: Date added to inventory
            - sold_date: Date sold (null if unsold)
            - days_to_sell: Days between production and sale
            - production_price: Initial price
            - sold_price: Final sold price (null if unsold)
        """
        try:
            self.data = pd.read_csv(self.csv_path)
            
            # Add computed column for sold status
            self.data['sold'] = self.data['sold_date'].notna()
            
            # Calculate sell-through rate per category
            self._compute_category_stats()
            
            logger.info(
                f"Loaded internal data: {len(self.data)} records, "
                f"{self.data['sold'].sum()} sold items"
            )
            
        except Exception as e:
            logger.error(f"Error loading internal data: {e}")
            self.data = pd.DataFrame()
    
    def _compute_category_stats(self) -> None:
        """Precompute statistics by category/subcategory."""
        if self.data.empty:
            return
        
        # Group by category and subcategory
        for (dept, cat, subcat), group in self.data.groupby(
            ['department', 'category', 'subcategory'], dropna=False
        ):
            sold_items = group[group['sold']]
            key = f"{dept}|{cat}|{subcat}"
            
            self.category_stats[key] = {
                "avg_production_price": float(group['production_price'].mean()),
                "avg_sold_price": float(sold_items['sold_price'].mean()) if not sold_items.empty else 0,
                "sell_through_rate": float(group['sold'].sum() / len(group)),
                "avg_days_to_sell": float(group['days_to_sell'].mean()) if group['days_to_sell'].notna().any() else 0,
                "sample_size": len(group)
            }
    
    async def search_by_brand(self, brand: str) -> Optional[InternalData]:
        """Search internal data by brand name."""
        if self.use_database:
            records = await self.db_client.search_by_brand(brand)
            if not records:
                return None
            return self._aggregate_records(records, f"Brand: {brand}")
        else:
            if self.data.empty:
                return None
            
            matches = self.data[
                self.data['brand'].str.lower() == brand.lower()
            ]
            
            if matches.empty:
                return None
            
            return self._aggregate_matches(matches, f"Brand: {brand}")
    
    async def search_by_category(self, department: str = None, category: str = None, 
                          subcategory: str = None) -> Optional[InternalData]:
        """Search internal data by category hierarchy."""
        if self.use_database:
            # For database, use the category search
            if category:
                records = await self.db_client.search_by_category(category)
                if not records:
                    return None
                return self._aggregate_records(records, category)
            return None
        else:
            if self.data.empty:
                return None
            
            matches = self.data.copy()
            
            if department:
                matches = matches[matches['department'].str.lower() == department.lower()]
            if category:
                matches = matches[matches['category'].str.lower() == category.lower()]
            if subcategory:
                matches = matches[matches['subcategory'].str.lower() == subcategory.lower()]
            
            if matches.empty:
                return None
            
            search_desc = "/".join(filter(None, [department, category, subcategory]))
            return self._aggregate_matches(matches, search_desc)
    
    async def search_by_keywords(self, search_term: str) -> Optional[InternalData]:
        """
        Search internal data by keywords (brand, category, subcategory).
        This is the main method used by the pricing engine.
        """
        if self.use_database:
            records = await self.db_client.search_by_keywords(search_term)
            if not records:
                logger.info(f"No internal data found for: {search_term}")
                print(f"❌ No internal data found for: {search_term}")
                return None
            
            print(f"✅ Found {len(records)} internal records for: {search_term}")
            return self._aggregate_records(records, search_term)
        else:
            if self.data.empty:
                return None
            
            search_lower = search_term.lower()
            
            # Split search term into words for better matching
            search_words = search_lower.split()
            
            # First try: exact matches on any field
            matches = self.data[
                (self.data['brand'].str.lower().str.contains(search_lower, na=False)) |
                (self.data['department'].str.lower().str.contains(search_lower, na=False)) |
                (self.data['category'].str.lower().str.contains(search_lower, na=False)) |
                (self.data['subcategory'].str.lower().str.contains(search_lower, na=False))
            ]
            
            # If no results, try word-by-word matching (e.g., "Nike Sneakers" -> "Nike" + "Sneakers")
            if matches.empty and len(search_words) > 1:
                print(f"🔍 Trying word-by-word search for: {search_words}")
                mask = pd.Series([False] * len(self.data))
                
                for word in search_words:
                    if len(word) > 2:  # Skip very short words
                        word_mask = (
                            (self.data['brand'].str.lower().str.contains(word, na=False)) |
                            (self.data['department'].str.lower().str.contains(word, na=False)) |
                            (self.data['category'].str.lower().str.contains(word, na=False)) |
                            (self.data['subcategory'].str.lower().str.contains(word, na=False))
                        )
                        mask = mask | word_mask
                
                matches = self.data[mask]
                
                # If still no results, try brand matching only (most common case)
                if matches.empty and len(search_words) > 0:
                    brand_word = search_words[0]  # Assume first word is brand
                    print(f"🔍 Trying brand-only search for: {brand_word}")
                    matches = self.data[
                        self.data['brand'].str.lower().str.contains(brand_word, na=False)
                    ]
            
            if matches.empty:
                logger.info(f"No internal data found for: {search_term}")
                print(f"❌ No internal data found for: {search_term}")
                return None
            
            print(f"✅ Found {len(matches)} internal records for: {search_term}")
            return self._aggregate_matches(matches, search_term)
    
    def _aggregate_records(self, records: List[Dict], identifier: str) -> InternalData:
        """Aggregate database records into InternalData model."""
        if not records:
            return None
        
        # Convert to pandas DataFrame for easier analysis
        df = pd.DataFrame(records)
        
        # Calculate sold status
        df['sold'] = df['sold_date'].notna()
        sold_items = df[df['sold']]
        
        # Calculate metrics
        avg_production_price = float(df['production_price'].mean())
        avg_sold_price = float(sold_items['sold_price'].mean()) if not sold_items.empty else avg_production_price
        sell_through_rate = float(df['sold'].sum() / len(df))
        days_on_shelf = float(df['days_to_sell'].mean()) if df['days_to_sell'].notna().any() else 0
        category = df['category'].mode()[0] if len(df) > 0 else "Unknown"
        
        internal_data = InternalData(
            internal_price=avg_sold_price if avg_sold_price > 0 else avg_production_price,
            sell_through_rate=sell_through_rate,
            days_on_shelf=int(days_on_shelf),
            category=category,
            sample_size=len(df),
            metadata={
                "production_price": avg_production_price,
                "sold_items": len(sold_items),
                "unsold_items": len(df) - len(sold_items),
                "departments": df['department'].unique().tolist(),
                "brands": df['brand'].unique().tolist()[:5],
                "subcategories": df['subcategory'].unique().tolist()[:5]
            }
        )
        
        print(
            f"📊 Internal data summary: {len(df)} items, "
            f"${internal_data.internal_price:.2f} avg, "
            f"{sell_through_rate:.1%} sell-through, "
            f"{len(sold_items)} sold/{len(df)} total"
        )
        
        logger.info(
            f"Found {len(df)} items for '{identifier}': "
            f"price=${internal_data.internal_price:.2f}, "
            f"sell_through={sell_through_rate:.2%}"
        )
        
        return internal_data
    
    def _aggregate_matches(self, matches: pd.DataFrame, identifier: str) -> InternalData:
        sold_items = matches[matches['sold']]
        
        # Calculate average prices
        avg_production_price = float(matches['production_price'].mean())
        avg_sold_price = float(sold_items['sold_price'].mean()) if not sold_items.empty else avg_production_price
        
        # Calculate sell-through rate
        sell_through_rate = float(matches['sold'].sum() / len(matches))
        
        # Calculate average days on shelf
        days_on_shelf = float(matches['days_to_sell'].mean()) if matches['days_to_sell'].notna().any() else 0
        
        # Get most common category info
        category = matches['category'].mode()[0] if len(matches) > 0 else "Unknown"
        
        internal_data = InternalData(
            internal_price=avg_sold_price if avg_sold_price > 0 else avg_production_price,
            sell_through_rate=sell_through_rate,
            days_on_shelf=int(days_on_shelf),
            category=category,
            sample_size=len(matches),
            metadata={
                "production_price": avg_production_price,
                "sold_items": len(sold_items),
                "unsold_items": len(matches) - len(sold_items),
                "departments": matches['department'].unique().tolist(),
                "brands": matches['brand'].unique().tolist()[:5],  # Top 5 brands
                "subcategories": matches['subcategory'].unique().tolist()[:5]
            }
        )
        
        print(
            f"📊 Internal data summary: {len(matches)} items, "
            f"${internal_data.internal_price:.2f} avg, "
            f"{sell_through_rate:.1%} sell-through, "
            f"{len(sold_items)} sold/{len(matches)} total"
        )
        
        logger.info(
            f"Found {len(matches)} items for '{identifier}': "
            f"price=${internal_data.internal_price:.2f}, "
            f"sell_through={sell_through_rate:.2%}"
        )
        
        return internal_data
    
    def get_category_metrics(self, category: str) -> Dict[str, Any]:
        """Get aggregated metrics for a category."""
        if self.data.empty:
            return {
                "avg_price": 0,
                "avg_sell_through": 0,
                "sample_size": 0
            }
        
        cat_data = self.data[
            self.data['category'].str.lower() == category.lower()
        ]
        
        if cat_data.empty:
            return {
                "avg_price": 0,
                "avg_sell_through": 0,
                "sample_size": 0
            }
        
        sold_items = cat_data[cat_data['sold']]
        
        return {
            "avg_price": float(sold_items['sold_price'].mean()) if not sold_items.empty else 0,
            "avg_production_price": float(cat_data['production_price'].mean()),
            "avg_sell_through": float(cat_data['sold'].sum() / len(cat_data)),
            "avg_days_to_sell": float(cat_data['days_to_sell'].mean()) if cat_data['days_to_sell'].notna().any() else 0,
            "sample_size": len(cat_data)
        }
