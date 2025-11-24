"""
LLM Processor Component
Processes articles using Claude API for synthesis
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from anthropic import Anthropic, APIError, APIConnectionError, RateLimitError
from core.base import Processor
from core.errors import ProcessError, ConfigError


class ClaudeLLMProcessor(Processor):
    """
    Processes articles using Claude (Anthropic) LLM
    Handles API calls, cost tracking, and error handling
    """

    # Token pricing (as of 2024) - adjust as needed
    PRICING = {
        'claude-3-haiku-20240307': {
            'input': 0.25 / 1_000_000,   # $0.25 per 1M input tokens
            'output': 1.25 / 1_000_000   # $1.25 per 1M output tokens
        },
        'claude-3-5-sonnet-20241022': {
            'input': 3.0 / 1_000_000,    # $3 per 1M input tokens
            'output': 15.0 / 1_000_000   # $15 per 1M output tokens
        }
    }

    def __init__(self, model: str = "claude-3-haiku-20240307",
                 max_tokens: int = 4096, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.max_tokens = max_tokens

        # Initialize Anthropic client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ConfigError("ANTHROPIC_API_KEY",
                            "Anthropic API key not found in environment variables")

        self.client = Anthropic(api_key=api_key)

    def process(self, articles: List[Dict]) -> str:
        """
        Process articles and generate synthesis using Claude

        Args:
            articles: List of article dictionaries

        Returns:
            Synthesized analysis as string

        Raises:
            ProcessError: If processing fails
        """
        start_time = datetime.now()

        if self.logger:
            self.logger.log_process_start(f"Claude-{self.model}", len(articles))

        try:
            # Build the prompt
            prompt = self._build_prompt(articles)

            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract synthesis
            synthesis = response.content[0].text

            # Calculate cost
            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)

            if self.logger:
                self.logger.log_process_success(
                    f"Claude-{self.model}",
                    start_time,
                    tokens_used=input_tokens + output_tokens,
                    cost=cost
                )

            return synthesis

        except RateLimitError as e:
            error = ProcessError("Claude", "Rate limit exceeded. Please wait and retry.", e)
            if self.logger:
                self.logger.log_process_error("Claude", error, start_time)
            raise error

        except APIConnectionError as e:
            error = ProcessError("Claude", "Failed to connect to Anthropic API", e)
            if self.logger:
                self.logger.log_process_error("Claude", error, start_time)
            raise error

        except APIError as e:
            error = ProcessError("Claude", f"API error: {str(e)}", e)
            if self.logger:
                self.logger.log_process_error("Claude", error, start_time)
            raise error

        except Exception as e:
            error = ProcessError("Claude", f"Unexpected error: {str(e)}", e)
            if self.logger:
                self.logger.log_process_error("Claude", error, start_time)
            raise error

    def _build_prompt(self, articles: List[Dict]) -> str:
        """
        Build the prompt for Claude based on articles

        Args:
            articles: List of article dictionaries

        Returns:
            Formatted prompt string
        """
        # Format articles for the prompt
        articles_text = []
        for i, article in enumerate(articles, 1):
            article_str = f"""
Article {i}:
Source: {article.get('source_name', 'Unknown')}
Title: {article['title']}
Published: {article.get('published', 'Unknown')}
Link: {article.get('link', 'N/A')}
Summary: {article.get('summary', 'No summary available')}
"""
            articles_text.append(article_str)

        all_articles = "\n---\n".join(articles_text)

        # Build the main prompt
        prompt = f"""You are an expert news analyst. I have collected {len(articles)} articles from various sources on a specific topic. Your task is to:

1. **Identify Common Themes**: What are the main points that multiple sources agree on?
2. **Highlight Differences**: What unique perspectives or information does each source provide?
3. **Analyze Sentiment & Tone**: What is the overall sentiment (positive, negative, neutral) of each source?
4. **Detect Bias**: Are there any noticeable biases in how different sources present the information?
5. **Provide Synthesis**: Create a comprehensive, balanced summary that incorporates all perspectives.

Here are the articles:

{all_articles}

Please provide your analysis in the following structure:

## Common Themes
[What multiple sources agree on]

## Source-Specific Perspectives
[Unique information from each source]

## Sentiment Analysis
[Overall tone and sentiment of each source]

## Potential Biases
[Any detected biases or editorial slants]

## Comprehensive Synthesis
[Your balanced summary incorporating all perspectives]

## Key Takeaways
[3-5 bullet points of the most important insights]
"""

        return prompt

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate the cost of API call

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD
        """
        if self.model in self.PRICING:
            pricing = self.PRICING[self.model]
            cost = (input_tokens * pricing['input'] +
                   output_tokens * pricing['output'])
            return cost
        else:
            # Unknown model, return 0
            return 0.0
