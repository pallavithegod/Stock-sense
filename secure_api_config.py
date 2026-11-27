# -*- coding: utf-8 -*-
from utils import encoding
"""
UPDATED API Configuration for STOCKSENSE VIP-EDGE™
HuggingFace Edition with Your Specific APIs
Enterprise Security - Zero Hardcoded Credentials
"""

import os
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

# Import our security utilities
try:
    from security_utils import SecureCredentialManager, get_secure_api_key
    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False
    logging.warning("Security utilities not available - using basic credential management")

class SecureAPIConfig:
    """Secure API configuration with your specific APIs"""
    
    def __init__(self):
        """Initialize secure API configuration"""
        if SECURITY_ENABLED:
            self.credential_manager = SecureCredentialManager()
        else:
            self.credential_manager = None
    
    def get_api_key(self, service: str, required: bool = False) -> Optional[str]:
        """
        Securely get API key for your specific services
        
        Args:
            service: Service name 
            required: Whether to log warning if missing
        
        Returns:
            API key string or None
        """
        if SECURITY_ENABLED and self.credential_manager:
            return self.credential_manager.get_api_key(service, required)
        else:
            # Fallback - basic environment variable lookup
            env_mappings = {
                'alpha_vantage': 'ALPHA_VANTAGE_API_KEY',
                'twelve_data': 'TWELVE_DATA_API_KEY',
                'data_gov': 'DATA_GOV_API_KEY', 
                'news_api': 'NEWS_API_KEY',
                'gnews': 'GNEWS_API_KEY',
                'finnhub': 'FINNHUB_API_KEY',
                'fmp': 'FMP_API_KEY',
                'huggingface': 'HUGGINGFACEHUB_API_TOKEN'
            }
            env_var = env_mappings.get(service.lower(), f"{service.upper()}_API_KEY")
            return os.getenv(env_var)
    
    def is_service_configured(self, service: str) -> bool:
        """Check if API service is properly configured"""
        key = self.get_api_key(service)
        return key is not None and len(key) > 10
    
    def get_available_services(self) -> List[str]:
        """Get list of your configured services"""
        services = []
        service_list = [
            'alpha_vantage', 'twelve_data', 'data_gov', 
            'news_api', 'gnews', 'finnhub', 'fmp', 'huggingface'
        ]
        
        for service in service_list:
            if self.is_service_configured(service):
                services.append(service)
        
        # YFinance is always available (no API key required)
        services.append('yfinance')
        return services
    
    def get_service_config(self, service: str) -> Dict[str, Any]:
        """Get complete configuration for your specific services"""
        service_configs = {
            'alpha_vantage': {
                'base_url': 'https://www.alphavantage.co/query',
                'rate_limit': 5,  # requests per minute for free tier
                'supports': ['stocks', 'forex', 'crypto', 'fundamentals', 'technical_indicators'],
                'free_tier': True,
                'description': 'Real-time and historical market data'
            },
            'twelve_data': {
                'base_url': 'https://api.twelvedata.com',
                'rate_limit': 8,  # requests per minute for free tier
                'supports': ['stocks', 'forex', 'crypto', 'etf', 'indices'],
                'free_tier': True,
                'description': 'Financial market data and analysis'
            },
            'data_gov': {
                'base_url': 'https://api.data.gov',
                'rate_limit': 1000,  # requests per hour
                'supports': ['economic_data', 'government_data', 'statistics'],
                'free_tier': True,
                'description': 'Government economic and statistical data'
            },
            'news_api': {
                'base_url': 'https://newsapi.org/v2',
                'rate_limit': 100,  # requests per day for free tier
                'supports': ['news', 'headlines', 'sources'],
                'free_tier': True,
                'description': 'Real-time news and headlines'
            },
            'gnews': {
                'base_url': 'https://gnews.io/api/v4',
                'supports': ['news', 'headlines', 'search'],
                'description': 'GNews news and headline API'
            },
            'finnhub': {
                'base_url': 'https://finnhub.io/api/v1',
                'rate_limit': 60,  # requests per minute for free tier
                'supports': ['stocks', 'forex', 'crypto', 'news', 'earnings', 'financials'],
                'free_tier': True,
                'description': 'Comprehensive financial market data'
            },
            'fmp': {
                'base_url': 'https://financialmodelingprep.com/api/v3',
                'rate_limit': 250,  # requests per day for free tier
                'supports': ['stocks', 'financials', 'ratios', 'dcf', 'earnings'],
                'free_tier': True,
                'description': 'Financial statements and company analysis'
            },
            'huggingface': {
                'base_url': 'https://api-inference.huggingface.co',
                'rate_limit': 1000,  # requests per day for free tier
                'supports': ['nlp', 'sentiment', 'summarization', 'qa', 'text_generation'],
                'free_tier': True,
                'description': 'Free AI/ML models for text analysis'
            },
            'yfinance': {
                'rate_limit': 100,  # Conservative estimate
                'supports': ['stocks', 'etf', 'indices', 'options', 'futures'],
                'free_tier': True,
                'description': 'Yahoo Finance data (no API key required)'
            }
        }
        
        config = service_configs.get(service.lower(), {})
        
        # Add API key if available
        api_key = self.get_api_key(service)
        if api_key:
            config['api_key'] = api_key
            config['configured'] = True
        else:
            config['configured'] = False
            
        return config
    
    def get_security_status(self) -> Dict[str, Any]:
        """Get overall API security status"""
        if SECURITY_ENABLED and self.credential_manager:
            return self.credential_manager.get_system_health()
        else:
            configured_services = self.get_available_services()
            return {
                'health_score': len(configured_services) * 12,
                'max_score': 100,
                'status': 'GOOD' if len(configured_services) >= 5 else 'FAIR' if len(configured_services) >= 3 else 'POOR',
                'configured_services': configured_services,
                'security_features': False
            }
    
    def get_api_summary(self) -> Dict[str, Any]:
        """Get summary of your API configuration"""
        available_services = self.get_available_services()
        total_free_apis = len(available_services)
        
        categories = {
            'financial_data': ['alpha_vantage', 'twelve_data', 'finnhub', 'fmp', 'yfinance'],
            'news_sentiment': ['news_api'],
            'government_data': ['data_gov'], 
            'ai_analysis': ['huggingface']
        }
        
        configured_by_category = {}
        for category, services in categories.items():
            configured_by_category[category] = len([s for s in services if s in available_services])
        
        return {
            'total_apis': total_free_apis,
            'total_cost': 0.0,  # All free APIs
            'configured_by_category': configured_by_category,
            'primary_data_source': 'yfinance' if 'yfinance' in available_services else available_services[0] if available_services else None,
            'ai_enabled': 'huggingface' in available_services,
            'news_enabled': 'news_api' in available_services,
            'comprehensive_coverage': total_free_apis >= 6
        }

# Backward compatibility with original APIConfig class
class APIConfig(SecureAPIConfig):
    """Backward compatible API configuration with your APIs"""
    
    @property 
    def ALPHA_VANTAGE_KEY(self) -> Optional[str]:
        return self.get_api_key('alpha_vantage')
    
    @property
    def TWELVE_DATA_KEY(self) -> Optional[str]:
        return self.get_api_key('twelve_data')
    
    @property
    def DATA_GOV_KEY(self) -> Optional[str]:
        return self.get_api_key('data_gov')
    
    @property
    def NEWS_API_KEY(self) -> Optional[str]:
        return self.get_api_key('news_api')
    
    @property
    def FINNHUB_KEY(self) -> Optional[str]:
        return self.get_api_key('finnhub')
    
    @property
    def FMP_KEY(self) -> Optional[str]:
        return self.get_api_key('fmp')
    
    @property
    def HUGGINGFACE_TOKEN(self) -> Optional[str]:
        return self.get_api_key('huggingface')

class SystemSettings:
    """Enhanced system settings for your configuration"""
    
    APP_NAME = "StockSense"
    APP_VERSION = "2.1.0-HF"  # HuggingFace Edition
    APP_DESCRIPTION = "Free AI-Powered Financial Intelligence Platform"
    
    # Your optimized settings
    DEFAULT_REFRESH_INTERVAL = 60  # Slower refresh for free APIs
    MAX_CONCURRENT_STOCKS = 10     # Conservative for rate limits
    CACHE_DURATION = 900           # 15 minutes - longer caching
    MAX_HISTORICAL_PERIOD = "2y"   # Reasonable for analysis
    
    # Rate limiting for your free APIs
    RATE_LIMITS = {
        'alpha_vantage': {'requests_per_minute': 5, 'daily_limit': None},
        'twelve_data': {'requests_per_minute': 8, 'daily_limit': None},
        'data_gov': {'requests_per_hour': 1000, 'daily_limit': None},
        'news_api': {'requests_per_day': 100, 'monthly_limit': None},
        'finnhub': {'requests_per_minute': 60, 'daily_limit': None},
        'fmp': {'requests_per_day': 250, 'monthly_limit': None},
        'huggingface': {'requests_per_day': 1000, 'monthly_limit': None}
    }
    
    @classmethod
    def validate_configuration(cls) -> Dict[str, Any]:
        """Validate your specific configuration"""
        api_config = SecureAPIConfig()
        
        validation = {
            'api_services': api_config.get_available_services(),
            'api_summary': api_config.get_api_summary(),
            'total_score': 0,
            'recommendations': []
        }
        
        # Calculate score based on your setup
        summary = validation['api_summary']
        score = 0
        
        # Financial data coverage (40 points)
        financial_apis = summary['configured_by_category'].get('financial_data', 0)
        score += min(financial_apis * 10, 40)
        
        # AI capabilities (20 points)
        if summary['ai_enabled']:
            score += 20
        
        # News/sentiment (15 points) 
        if summary['news_enabled']:
            score += 15
        
        # Government data (10 points)
        if summary['configured_by_category'].get('government_data', 0) > 0:
            score += 10
        
        # Comprehensive coverage bonus (15 points)
        if summary['comprehensive_coverage']:
            score += 15
        
        validation['total_score'] = score
        
        # Generate recommendations
        if financial_apis < 3:
            validation['recommendations'].append("Configure more financial data APIs for redundancy")
        
        if not summary['ai_enabled']:
            validation['recommendations'].append("Configure HuggingFace API for AI analysis")
        
        if not summary['news_enabled']:
            validation['recommendations'].append("Configure News API for sentiment analysis")
        
        return validation

def show_api_status():
    """Display comprehensive API status for your setup"""
    print("StockSense - API Configuration Status")
    print("=" * 70)
    
    config = SecureAPIConfig()
    summary = config.get_api_summary()
    
    print(f"📊 Configuration Summary:")
    print(f"  Total APIs Configured: {summary['total_apis']}")
    print(f"  Total Cost: ${summary['total_cost']} (All Free!)")
    print(f"  AI Analysis: {'✅' if summary['ai_enabled'] else '❌'}")
    print(f"  News/Sentiment: {'✅' if summary['news_enabled'] else '❌'}")
    print(f"  Comprehensive Coverage: {'✅' if summary['comprehensive_coverage'] else '❌'}")
    
    print(f"\n📈 APIs by Category:")
    categories = {
        'Financial Data': summary['configured_by_category'].get('financial_data', 0),
        'News & Sentiment': summary['configured_by_category'].get('news_sentiment', 0),
        'Government Data': summary['configured_by_category'].get('government_data', 0),
        'AI Analysis': summary['configured_by_category'].get('ai_analysis', 0)
    }
    
    for category, count in categories.items():
        status = "✅" if count > 0 else "❌"
        print(f"  {status} {category}: {count} API(s)")
    
    print(f"\n🔧 Service Details:")
    services = ['alpha_vantage', 'twelve_data', 'data_gov', 'news_api', 'finnhub', 'fmp', 'huggingface', 'yfinance']
    
    for service in services:
        service_config = config.get_service_config(service)
        status = "✅" if service_config.get('configured', service == 'yfinance') else "❌"
        rate_limit = service_config.get('rate_limit', 'N/A')
        description = service_config.get('description', 'Market data provider')
        print(f"  {status} {service.replace('_', ' ').title()}: {description} (Rate: {rate_limit})")
    
    # Security status
    security_status = config.get_security_status()
    print(f"\n🔒 Security Health: {security_status['status']} ({security_status['health_score']:.0f}/100)")
    
    # backend CLI/status output should be ASCII-safe
    status_label = 'Ready for Production' if summary['total_apis'] >= 5 else 'Basic Setup'
    print(f"\n[SYS] System Status: {status_label}")

if __name__ == "__main__":
    show_api_status()
