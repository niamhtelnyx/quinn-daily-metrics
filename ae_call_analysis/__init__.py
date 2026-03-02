"""
AE Call Analysis System
Automated analysis of Fellow.app call recordings with Salesforce integration
"""

__version__ = "1.0.0"
__author__ = "Telnyx AI Team"

from .config.settings import get_config
from .database.database import get_db

__all__ = ["get_config", "get_db"]