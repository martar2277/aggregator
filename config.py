"""
Configuration Management
Centralized configuration with environment variable support
"""

import os
from typing import Dict, List
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
# In Codespaces, GitHub Secrets are automatically available as env vars
load_dotenv(override=False)  # Don't override existing env vars (e.g., from GitHub Secrets)


class Config:
    """
    Application configuration
    Reads from environment variables with sensible defaults
    """

    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # LLM Settings
    # DEFAULT_LLM_PROVIDER options: "openai", "gemini", "anthropic"
    DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")

    # Model per provider
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "")  # Auto-selected based on provider
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))

    # Default models for each provider
    DEFAULT_MODELS = {
        "openai": "gpt-4o-mini",        # Cheapest, fast
        "gemini": "gemini-1.5-flash",   # Very cheap, fast
        "anthropic": "claude-3-haiku-20240307"  # Good quality, reasonable price
    }

    # Directory Settings
    DATA_DIR = os.getenv("DATA_DIR", "data")
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "outputs")
    LOG_DIR = os.getenv("LOG_DIR", "logs")

    # Fetcher Settings
    MAX_ARTICLES_PER_SOURCE = int(os.getenv("MAX_ARTICLES_PER_SOURCE", "10"))

    # Default RSS Sources - Estonian and International
    DEFAULT_SOURCES: Dict[str, str] = {
        "ERR": "https://www.err.ee/rss",
        "Postimees": "https://www.postimees.ee/rss",
        "Delfi": "https://www.delfi.ee/rss",
    }

    # International/EU Sources
    INTERNATIONAL_SOURCES: Dict[str, str] = {
        "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
        "Reuters": "https://www.reutersagency.com/feed/",
        "EU Commission": "https://ec.europa.eu/commission/presscorner/api/files/feed/en.xml",
        "Guardian": "https://www.theguardian.com/international/rss",
        "DW": "https://rss.dw.com/xml/rss-en-all",
    }

    # Topic-specific sources (can be expanded)
    TECH_SOURCES: Dict[str, str] = {
        "TechCrunch": "https://techcrunch.com/feed/",
        "Ars Technica": "http://feeds.arstechnica.com/arstechnica/index",
        "Wired": "https://www.wired.com/feed/rss",
    }

    @classmethod
    def validate(cls) -> List[str]:
        """
        Validate required configuration
        Returns list of missing/invalid configs
        """
        errors = []

        # Check that at least one LLM API key is set
        if not any([cls.ANTHROPIC_API_KEY, cls.OPENAI_API_KEY, cls.GEMINI_API_KEY]):
            errors.append("No LLM API keys found. Set at least one: ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY")

        # Validate directories can be created
        for dir_name in [cls.DATA_DIR, cls.OUTPUT_DIR, cls.LOG_DIR]:
            try:
                Path(dir_name).mkdir(exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create directory {dir_name}: {e}")

        return errors

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """
        Get list of available LLM providers based on configured API keys

        Returns:
            List of provider names that have API keys configured
        """
        providers = []
        if cls.ANTHROPIC_API_KEY:
            providers.append("anthropic")
        if cls.OPENAI_API_KEY:
            providers.append("openai")
        if cls.GEMINI_API_KEY:
            providers.append("gemini")
        return providers

    @classmethod
    def get_sources_by_category(cls, category: str) -> Dict[str, str]:
        """
        Get sources by category

        Args:
            category: One of 'default', 'international', 'tech', 'all'

        Returns:
            Dictionary of source name -> URL
        """
        if category == 'default':
            return cls.DEFAULT_SOURCES
        elif category == 'international':
            return cls.INTERNATIONAL_SOURCES
        elif category == 'tech':
            return cls.TECH_SOURCES
        elif category == 'all':
            all_sources = {}
            all_sources.update(cls.DEFAULT_SOURCES)
            all_sources.update(cls.INTERNATIONAL_SOURCES)
            all_sources.update(cls.TECH_SOURCES)
            return all_sources
        else:
            return cls.DEFAULT_SOURCES

    @classmethod
    def get_all_source_urls(cls) -> List[str]:
        """Get list of all configured source URLs"""
        return list(cls.get_sources_by_category('all').values())

    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging)"""
        print("=== Configuration ===")
        print(f"LLM Provider: {cls.DEFAULT_LLM_PROVIDER}")
        print(f"LLM Model: {cls.DEFAULT_LLM_MODEL or 'Auto-selected'}")
        print(f"Max Tokens: {cls.MAX_TOKENS}")
        print(f"Data Directory: {cls.DATA_DIR}")
        print(f"Output Directory: {cls.OUTPUT_DIR}")
        print(f"Log Directory: {cls.LOG_DIR}")
        print(f"Max Articles/Source: {cls.MAX_ARTICLES_PER_SOURCE}")
        print(f"\nAPI Keys:")
        print(f"  Anthropic: {'Set' if cls.ANTHROPIC_API_KEY else 'NOT SET'}")
        print(f"  OpenAI:    {'Set' if cls.OPENAI_API_KEY else 'NOT SET'}")
        print(f"  Gemini:    {'Set' if cls.GEMINI_API_KEY else 'NOT SET'}")
        print(f"\nAvailable Providers: {', '.join(cls.get_available_providers())}")
        print("=====================")
