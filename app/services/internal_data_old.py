"""Internal data processing service for CSV files."""
import pandas as pd
from pathlib import Path
from typing import Optional, Dict, Any
from app.models.pricing import InternalData
from app.utils.logger import get_logger

logger = get_logger(__name__)


class InternalDataProcessor:
    """Service for processing internal sales data from CSV files."""
    
    def __init__(self, csv_path: Optional[str] = None):
        """
        Initialize the processor.
        
        Args:
            csv_path: Path to CSV file with internal data
        """
        self.csv_path = csv_path
        self.data: Optional[pd.DataFrame] = None
        self.category_stats: Dict[str, Dict[str, float]] = {}
        
        if csv_path and Path(csv_path).exists():
            self.load_data(csv_path)
    
    def load_data(self, csv_path: str) -> None:
        """
        Load internal data from CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Expected CSV columns:
            - upc: UPC code
            - internal_price: Current internal price
            - sell_through_rate: Sell-through rate (0-1)
            - days_on_shelf: Days product has been on shelf
            - category: Product category
        """
        try:
            self.data = pd.read_csv(csv_path)
            self.csv_path = csv_path
            
            # Validate required columns
            required_columns = [
                "upc", "internal_price", "sell_through_rate", 
                "days_on_shelf", "category"
            ]
            missing_columns = set(required_columns) - set(self.data.columns)
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Clean data
            self.data["upc"] = self.data["upc"].astype(str).str.strip()
            self.data["category"] = self.data["category"].astype(str).str.strip()
            
            # Calculate category statistics
            self._calculate_category_stats()
            
            logger.info(
                f"Loaded {len(self.data)} records from {csv_path}. "
                f"Categories: {len(self.category_stats)}"
            )
            
        except Exception as e:
            logger.error(f"Error loading CSV file {csv_path}: {str(e)}")
            raise
    
    def _calculate_category_stats(self) -> None:
        """Calculate aggregate statistics by category."""
        if self.data is None or self.data.empty:
            return
        
        self.category_stats = {}
        
        for category in self.data["category"].unique():
            category_data = self.data[self.data["category"] == category]
            
            self.category_stats[category] = {
                "avg_price": float(category_data["internal_price"].mean()),
                "median_price": float(category_data["internal_price"].median()),
                "avg_sell_through": float(category_data["sell_through_rate"].mean()),
                "avg_days_on_shelf": float(category_data["days_on_shelf"].mean()),
                "count": int(len(category_data))
            }
    
    def get_internal_data(self, upc: str) -> Optional[InternalData]:
        """
        Get internal data for a specific UPC.
        
        Args:
            upc: UPC code to look up
            
        Returns:
            InternalData or None if not found
        """
        if self.data is None or self.data.empty:
            logger.debug(f"No internal data available for UPC: {upc}")
            return None
        
        # Clean UPC for comparison
        upc_clean = str(upc).strip()
        
        # Find matching record
        matches = self.data[self.data["upc"] == upc_clean]
        
        if matches.empty:
            logger.debug(f"No internal data found for UPC: {upc}")
            return None
        
        # Get first match (in case of duplicates)
        record = matches.iloc[0]
        
        try:
            internal_data = InternalData(
                internal_price=float(record["internal_price"]),
                sell_through_rate=float(record["sell_through_rate"]),
                days_on_shelf=int(record["days_on_shelf"]),
                category=str(record["category"])
            )
            
            logger.debug(f"Found internal data for UPC {upc}: {internal_data.category}")
            return internal_data
            
        except Exception as e:
            logger.error(f"Error creating InternalData for UPC {upc}: {str(e)}")
            return None
    
    def get_category_stats(self, category: str) -> Optional[Dict[str, float]]:
        """
        Get aggregate statistics for a category.
        
        Args:
            category: Category name
            
        Returns:
            Dictionary with category statistics or None if not found
        """
        return self.category_stats.get(category)
    
    def get_all_categories(self) -> list[str]:
        """Get list of all categories in the data."""
        return list(self.category_stats.keys())
