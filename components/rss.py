"""
RSS Fetcher Component
Fetches articles from RSS feeds with error handling and LLM-based relevance filtering
"""

import feedparser
from datetime import datetime
from typing import Dict, List, Optional
from core.base import Fetcher, Processor
from core.errors import FetchError


class RSSFetcher(Fetcher):
    """
    Fetches articles from RSS feeds
    Handles various RSS formats and provides robust error handling
    """

    def __init__(self, max_articles: int = 10, topic_filter: str = None,
                 llm_processor: Optional[Processor] = None, **kwargs):
        super().__init__(**kwargs)
        self.max_articles = max_articles
        self.topic_filter = topic_filter
        self.llm_processor = llm_processor

    def execute(self, data):
        """Execute method required by Component base class"""
        return self.fetch(data)

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

            # Extract and filter articles
            articles = []
            for entry in feed.entries:  # Check all entries, not just max_articles
                article = self._parse_entry(entry, source)
                if article:
                    # Apply topic filter if specified
                    if self.topic_filter and not self._matches_topic(article):
                        continue
                    articles.append(article)
                    if len(articles) >= self.max_articles:
                        break

            if not articles:
                if self.topic_filter:
                    raise FetchError(source, f"No articles found matching topic: {self.topic_filter}")
                else:
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

    def _matches_topic(self, article: Dict) -> bool:
        """
        Check if article matches the topic filter using LLM-based semantic matching

        Args:
            article: Article dictionary

        Returns:
            True if article is relevant to topic
        """
        if not self.topic_filter:
            return True

        # If no LLM processor provided, fallback to keyword matching
        if not self.llm_processor:
            return self._keyword_match(article)

        # Use LLM for semantic relevance check
        return self._llm_match(article)

    def _keyword_match(self, article: Dict) -> bool:
        """
        Fallback keyword-based matching

        Args:
            article: Article dictionary

        Returns:
            True if article matches keywords
        """
        searchable = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        keywords = self.topic_filter.lower().split()
        matches = sum(1 for keyword in keywords if keyword in searchable)
        threshold = max(1, len(keywords) // 2)
        return matches >= threshold

    def _llm_match(self, article: Dict) -> bool:
        """
        LLM-based semantic relevance matching

        Args:
            article: Article dictionary

        Returns:
            True if LLM determines article is relevant to topic
        """
        try:
            # Extract article excerpt (first 100 words or 3 sentences)
            excerpt = self._extract_excerpt(article)

            # Build relevance check prompt
            prompt = f"""Does the following article excerpt discuss the topic: "{self.topic_filter}"?

Article Title: {article.get('title', 'No title')}
Article Excerpt: {excerpt}

Answer with only "YES" if the article is relevant to the topic, or "NO" if it is not relevant.
Your answer:"""

            # Call LLM (reusing the processor's client)
            response = self._call_llm_for_filter(prompt)

            # Parse response
            answer = response.strip().upper()
            is_relevant = answer.startswith('YES')

            if self.logger:
                relevance_str = "relevant" if is_relevant else "not relevant"
                self.logger.log_info(f"  LLM filter: '{article.get('title', 'No title')[:50]}...' -> {relevance_str}")

            return is_relevant

        except Exception as e:
            # On error, log and fallback to keyword matching
            if self.logger:
                self.logger.log_info(f"  LLM filter error, using keyword fallback: {e}")
            return self._keyword_match(article)

    def _extract_excerpt(self, article: Dict) -> str:
        """
        Extract a short excerpt from article (first 100 words or 3 sentences)

        Args:
            article: Article dictionary

        Returns:
            Excerpt string
        """
        summary = article.get('summary', '')
        if not summary:
            return ''

        # Try to get first 3 sentences
        import re
        sentences = re.split(r'[.!?]+', summary)
        excerpt = '. '.join(sentences[:3]).strip()

        # Limit to ~100 words
        words = excerpt.split()
        if len(words) > 100:
            excerpt = ' '.join(words[:100]) + '...'

        return excerpt

    def _call_llm_for_filter(self, prompt: str) -> str:
        """
        Call the LLM for relevance filtering (lightweight call)

        Args:
            prompt: Filter prompt

        Returns:
            LLM response string
        """
        # Import here to avoid circular dependency
        from components.openai_llm import OpenAIProcessor
        from components.gemini_llm import GeminiProcessor
        from components.llm import ClaudeLLMProcessor

        # Use appropriate API based on processor type
        if isinstance(self.llm_processor, OpenAIProcessor):
            response = self.llm_processor.client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheaper model for filtering
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,  # We only need YES/NO
                temperature=0
            )
            return response.choices[0].message.content

        elif isinstance(self.llm_processor, GeminiProcessor):
            response = self.llm_processor.client.generate_content(
                prompt,
                generation_config={"max_output_tokens": 10, "temperature": 0}
            )
            return response.text

        elif isinstance(self.llm_processor, ClaudeLLMProcessor):
            response = self.llm_processor.client.messages.create(
                model="claude-3-haiku-20240307",  # Use cheaper model for filtering
                max_tokens=10,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        else:
            # Unknown processor, fallback to keyword
            raise Exception("Unknown LLM processor type")

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
