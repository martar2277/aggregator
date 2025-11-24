"""
RSS Fetcher Component
Fetches articles from RSS feeds with error handling
"""

import feedparser
from datetime import datetime
from typing import Dict, List
from core.base import Fetcher
from core.errors import FetchError


class RSSFetcher(Fetcher):
    """
    Fetches articles from RSS feeds
    Handles various RSS formats and provides robust error handling
    """

    def __init__(self, max_articles: int = 10, **kwargs):
        super().__init__(**kwargs)
        self.max_articles = max_articles

    def fetch(self, source: str) -> List[Dict]:
        """
        Fetch articles from an RSS feed

        Args:
            source: URL of the RSS feed

        Returns:
            List of article dictionaries

        Raises:
            FetchError: If fetching fails
        """
        start_time = datetime.now()

        if self.logger:
            self.logger.log_fetch_start(source)

        try:
            # Parse the RSS feed
            feed = feedparser.parse(source)

            # Check for parsing errors
            if feed.bozo and not feed.entries:
                # bozo=1 means there was a parsing error
                error_msg = getattr(feed, 'bozo_exception', 'Unknown parsing error')
                raise FetchError(source, f"RSS parsing failed: {error_msg}")

            # Check if feed has entries
            if not feed.entries:
                raise FetchError(source, "No entries found in RSS feed")

            # Extract articles
            articles = []
            for entry in feed.entries[:self.max_articles]:
                article = self._parse_entry(entry, source)
                if article:
                    articles.append(article)

            if not articles:
                raise FetchError(source, "No valid articles could be extracted")

            if self.logger:
                self.logger.log_fetch_success(source, len(articles), start_time)

            return articles

        except FetchError:
            # Re-raise our custom errors
            raise

        except Exception as e:
            # Wrap unexpected errors
            error = FetchError(source, f"Unexpected error: {str(e)}", e)
            if self.logger:
                self.logger.log_fetch_error(source, error, start_time)
            raise error

    def _parse_entry(self, entry, source: str) -> Dict:
        """
        Parse a single RSS entry into a standardized article dictionary

        Args:
            entry: feedparser entry object
            source: Source URL for reference

        Returns:
            Article dictionary or None if parsing fails
        """
        try:
            article = {
                'title': entry.get('title', 'No title'),
                'summary': self._get_summary(entry),
                'link': entry.get('link', ''),
                'published': self._get_published_date(entry),
                'source': source,
                'source_name': self._extract_source_name(source),
                'authors': self._get_authors(entry),
                'tags': self._get_tags(entry),
            }

            # Validate that we have at least title and link
            if not article['title'] or not article['link']:
                return None

            return article

        except Exception as e:
            # Log but don't fail - just skip this entry
            if self.logger:
                self.logger.log_info(f"Warning: Failed to parse entry from {source}: {e}")
            return None

    def _get_summary(self, entry) -> str:
        """Extract summary/description from entry"""
        # Try multiple possible fields
        if hasattr(entry, 'summary'):
            return entry.summary
        elif hasattr(entry, 'description'):
            return entry.description
        elif hasattr(entry, 'content') and entry.content:
            return entry.content[0].get('value', '')
        else:
            return ''

    def _get_published_date(self, entry) -> str:
        """Extract and normalize published date"""
        if hasattr(entry, 'published'):
            return entry.published
        elif hasattr(entry, 'updated'):
            return entry.updated
        elif hasattr(entry, 'created'):
            return entry.created
        else:
            return datetime.now().isoformat()

    def _get_authors(self, entry) -> List[str]:
        """Extract author names"""
        authors = []
        if hasattr(entry, 'author'):
            authors.append(entry.author)
        elif hasattr(entry, 'authors'):
            authors.extend([a.get('name', '') for a in entry.authors if a.get('name')])
        return authors

    def _get_tags(self, entry) -> List[str]:
        """Extract tags/categories"""
        tags = []
        if hasattr(entry, 'tags'):
            tags.extend([t.get('term', '') for t in entry.tags if t.get('term')])
        return tags

    def _extract_source_name(self, url: str) -> str:
        """Extract a readable source name from URL"""
        try:
            # Simple extraction from domain
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www. and .com/.org/etc
            domain = domain.replace('www.', '')
            parts = domain.split('.')
            return parts[0].upper() if parts else url
        except:
            return url
