"""FastAPI main application."""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.config import settings
from app.models.pricing import (
    PriceRecommendationRequest,
    PriceRecommendationResponse,
    HealthResponse,
    MarketData
)
from app.services.upc_validator import UPCValidator, UPCValidationError
from app.services.ebay_client import eBayClient, eBayAPIError
from app.services.internal_data import InternalDataProcessor
from app.services.pricing_engine import PricingEngine
from app.cache.cache_manager import cache
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Import database client if enabled
if settings.use_database:
    from app.services.database import db_client


# Global instances
internal_data_processor: Optional[InternalDataProcessor] = None
ebay_client: Optional[eBayClient] = None
pricing_engine: Optional[PricingEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global internal_data_processor, ebay_client, pricing_engine
    
    # Startup
    logger.info("Starting Price Intelligence API...")
    
    # Initialize database if enabled
    if settings.use_database:
        logger.info("Connecting to PostgreSQL database...")
        await db_client.connect()
        stats = await db_client.get_statistics()
        logger.info(f"Database statistics: {stats}")
    
    # Initialize services (lazy loading - browser starts on first request)
    ebay_client = eBayClient(headless=False)  # Browser will start on first search
    
    pricing_engine = PricingEngine()
    
    # Try to load internal data
    try:
        if settings.use_database:
            # Use database
            internal_data_processor = InternalDataProcessor(db_client=db_client)
            logger.info("Internal data processor initialized with PostgreSQL")
        else:
            # Use CSV
            internal_data_processor = InternalDataProcessor(
                csv_path="thrift_sales_12_weeks_with_subcategory.csv"
            )
            logger.info("Internal data processor initialized with CSV")
    except Exception as e:
        logger.warning(f"Could not load internal data: {str(e)}")
        internal_data_processor = InternalDataProcessor()
    
    logger.info("Price Intelligence API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Price Intelligence API...")
    if ebay_client:
        await ebay_client.close_session()
    logger.info("eBay session closed")
    
    if settings.use_database:
        await db_client.disconnect()
        logger.info("Database connection closed")


# Create FastAPI app
app = FastAPI(
    title="UPC Price Intelligence API",
    description="API for intelligent pricing recommendations based on UPC codes",
    version="1.0.0",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "message": "UPC Price Intelligence API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns service status and basic information.
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
    )


@app.post(
    "/price-recommendation",
    response_model=PriceRecommendationResponse,
    status_code=status.HTTP_200_OK,
    tags=["Pricing"]
)
async def get_price_recommendation(
    request: PriceRecommendationRequest
) -> PriceRecommendationResponse:
    """
    Get pricing recommendation for a UPC.
    
    This endpoint combines market data from eBay with optional internal
    sales data to provide an intelligent pricing recommendation.
    
    Args:
        request: Price recommendation request with UPC and optional internal data
        
    Returns:
        PriceRecommendationResponse with recommendation and rationale
        
    Raises:
        HTTPException: If UPC validation fails or other errors occur
    """
    print("\n" + "="*50)
    print("🚀 RECEIVED REQUEST")
    print("="*50)
    print(f"Request body: {request}")
    print(f"UPC received: {request.upc}")
    print(f"Internal data: {request.internal_data}")
    
    try:
        # Validate UPC
        try:
            print(f"\n🔍 Validating UPC: {request.upc}")
            validated_upc = UPCValidator.validate(request.upc)
            upc_code = validated_upc.code
            print(f"✅ UPC validated successfully: {upc_code}")
        except UPCValidationError as e:
            print(f"⚠️  UPC validation failed: {str(e)}")
            print(f"📝 Using original search term: {request.upc}")
            upc_code = request.upc  # Use as search term instead
        
        # Get internal data (from request or data source)
        internal_data = request.internal_data
        
        if not internal_data and internal_data_processor:
            # Try to get from CSV using keyword search
            # Use UPC as search term, or extract product name from request
            search_term = upc_code
            internal_data = await internal_data_processor.search_by_keywords(search_term)
            if internal_data:
                logger.info(f"Found internal data for search term '{search_term}' in CSV")
        
        # Get market data (with caching)
        market_data = await get_cached_market_data(upc_code)
        
        # Generate recommendation
        recommendation = pricing_engine.generate_recommendation(
            upc=upc_code,
            market_data=market_data,
            internal_data=internal_data
        )
        
        # Log the decision for audit
        log_pricing_decision(recommendation)
        
        logger.info(
            f"Generated recommendation for UPC {upc_code}: "
            f"${recommendation.recommended_price:.2f} "
            f"(confidence: {recommendation.confidence_score})"
        )
        
        return recommendation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing recommendation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


async def get_cached_market_data(upc: str) -> Optional[MarketData]:
    """
    Get market data with caching.
    
    Args:
        upc: UPC code
        
    Returns:
        MarketData or None if not available
    """
    # Check cache first
    cache_key = cache.get_cache_key("market_data", upc)
    cached_data = cache.get(cache_key)
    
    if cached_data:
        logger.info(f"Using cached market data for UPC: {upc}")
        try:
            return MarketData(**cached_data)
        except Exception as e:
            logger.warning(f"Error deserializing cached data: {str(e)}")
            # Continue to fetch fresh data
    
    # Fetch from eBay
    try:
        market_data = await ebay_client.get_market_pricing(upc)
        
        # Cache the result (only if we got meaningful data)
        if market_data and market_data.sample_size > 0:
            cache.set(
                cache_key,
                market_data.model_dump(),
                ttl=settings.cache_ttl
            )
            logger.info(f"Cached market data for UPC: {upc}")
        
        return market_data
        
    except eBayAPIError as e:
        logger.warning(f"eBay API error for UPC {upc}: {str(e)}")
        # Return None to allow graceful degradation
        return None


def log_pricing_decision(recommendation: PriceRecommendationResponse) -> None:
    """
    Log pricing decision for audit purposes.
    
    Args:
        recommendation: The pricing recommendation to log
    """
    log_entry = {
        "timestamp": recommendation.market_data.timestamp.isoformat() if recommendation.market_data else None,
        "upc": recommendation.upc,
        "recommended_price": recommendation.recommended_price,
        "weighting": recommendation.internal_vs_market_weighting,
        "confidence": recommendation.confidence_score,
        "market_median": recommendation.market_data.median_price if recommendation.market_data else None,
        "market_sample_size": recommendation.market_data.sample_size if recommendation.market_data else 0,
        "internal_price": recommendation.internal_data.internal_price if recommendation.internal_data else None,
        "warnings": recommendation.warnings
    }
    
    # Log as JSON for easy parsing
    logger.info(f"PRICING_DECISION: {json.dumps(log_entry)}")


@app.get("/cache/stats", tags=["Cache"])
async def get_cache_stats():
    """Get cache statistics (development endpoint)."""
    # This is a simple implementation
    # In production, you'd want more detailed stats
    return {
        "cache_type": "redis" if cache.use_redis else "memory",
        "ttl": cache.ttl
    }


@app.delete("/cache/clear", tags=["Cache"])
async def clear_cache():
    """Clear all cached data (development endpoint)."""
    cache.clear()
    logger.info("Cache cleared via API")
    return {"status": "success", "message": "Cache cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )
