#!/usr/bin/env python3
"""Train the hybrid ML pricing model."""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.model import HybridPricingModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """Train and save the pricing model."""
    logger.info("🚀 Starting ML model training...")
    
    # Initialize model
    model = HybridPricingModel()
    
    # Train on internal data
    csv_path = "data/thrift_sales_12_weeks_with_subcategory.csv"
    output_path = "models/pricing_model.pkl"
    
    try:
        metrics = model.train(csv_path, output_path)
        
        logger.info("✅ Training completed successfully!")
        logger.info(f"📊 Metrics:")
        logger.info(f"  - MAE: ${metrics['mae']:.2f}")
        logger.info(f"  - R²: {metrics['r2']:.3f}")
        logger.info(f"  - Training samples: {metrics['train_samples']}")
        logger.info(f"  - Test samples: {metrics['test_samples']}")
        
        # Display feature importance
        importance = model.get_feature_importance()
        if importance:
            logger.info("\n📈 Top 10 Most Important Features:")
            sorted_features = sorted(
                importance.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
            for i, (feature, imp) in enumerate(sorted_features, 1):
                logger.info(f"  {i}. {feature}: {imp:.4f}")
        
        logger.info(f"\n💾 Model saved to: {output_path}")
        
    except Exception as e:
        logger.error(f"❌ Training failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
