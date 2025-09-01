"""
LEGACY Price Cache Manager - DO NOT USE FOR NEW DEVELOPMENT

AIDEV-NOTE-CLAUDE: This class is now only a base class for EnhancedPriceCacheManager.
Its purpose is to maintain architectural consistency and prevent import errors in
legacy parts of the codebase.

All cache logic has been centralized in:
data_fetching.enhanced_price_cache_manager.EnhancedPriceCacheManager
"""
import os
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class PriceCacheManager:
    """
    Manages price data caching. This is a LEGACY class.
    For all new development, use data_fetching.enhanced_price_cache_manager.
    """
    def __init__(self, cache_dir: str = "price_cache", config: Optional[Dict] = None, **kwargs):
        # This constructor remains for backward compatibility but does little.
        self.cache_dir = cache_dir
        self.config = config or {}
        
    def get_price_data(self, *args, **kwargs) -> List[Dict]:
        """ DEPRECATED """
        logger.error("FATAL: Call made to DEPRECATED PriceCacheManager.get_price_data. The system should be calling EnhancedPriceCacheManager instead.")
        raise NotImplementedError("This method is deprecated. Please update the caller to use EnhancedPriceCacheManager.")

    def refresh_offline_cache(self, *args, **kwargs):
        """ DEPRECATED """
        logger.error("FATAL: Call made to DEPRECATED PriceCacheManager.refresh_offline_cache. Use EnhancedPriceCacheManager.refresh_offline_processed_cache instead.")
        raise NotImplementedError("This method is deprecated. Please update the caller to use EnhancedPriceCacheManager.")

    def validate_offline_cache_completeness(self, *args, **kwargs):
        """ DEPRECATED """
        logger.error("FATAL: Call made to DEPRECATED PriceCacheManager.validate_offline_cache_completeness.")
        raise NotImplementedError("This method is deprecated.")