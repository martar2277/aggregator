"""
OpenAI LLM Processor Component
Processes articles using OpenAI GPT models for synthesis
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from core.base import Processor
from core.errors import ProcessError, ConfigError


class OpenAIProcessor(Processor):
    """
    Processes articles using OpenAI GPT models
    Handles API calls, cost tracking, and error handling
    """

    # Token pricing (as of 2024) - adjust as needed
    PRICING = {
        'gpt-4o-mini': {
            'input': 0.150 / 1_000_000,   # $0.150 per 1M input tokens
            'output': 0.600 / 1_000_000   # $0.600 per 1M output tokens
        },
        'gpt-4o': {
            'input': 2.50 / 1_000_000,    # $2.50 per 1M input tokens
            'output': 10.0 / 1_000_000    # $10 per 1M output tokens
        },
        'gpt-4-turbo': {
            'input': 10.0 / 1_000_000,
            'output': 30.0 / 1_000_000
        }
    }

    def __init__(self, model: str = "gpt-4o-mini",
                 max_tokens: int = 4096, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.max_tokens = max_tokens

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ConfigError("OPENAI_API_KEY",
                            "OpenAI API key not found in environment variables")

        self.client = OpenAI(api_key=api_key)

    def execute(self, data):
        """Execute method required by Component base class"""
        return self.process(data)

    def process(self, articles: List[Dict]) -> str:
        """
        Process articles and generate synthesis using OpenAI

        Args:
            articles: List of article dictionaries

        Returns:
            Synthesized analysis as string

        Raises:
            ProcessError: If processing fails
        """
        start_time = datetime.now()

        if self.logger:
            self.logger.log_process_start(f"OpenAI-{self.model}", len(articles))

        try:
            # Build the prompt
            prompt = self._build_prompt(articles)

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {"role": "system", "content": "You are an expert news analyst specializing in multi-source analysis and synthesis."},
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract synthesis
            synthesis = response.choices[0].message.content

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            cost = self._calculate_cost(input_tokens, output_tokens)

            if self.logger:
                self.logger.log_process_success(
                    f"OpenAI-{self.model}",
                    start_time,
                    tokens_used=input_tokens + output_tokens,
                    cost=cost
                )

            return synthesis

        except RateLimitError as e:
            error = ProcessError("OpenAI", "Rate limit exceeded. Please wait and retry.", e)
            if self.logger:
                self.logger.log_process_error("OpenAI", error, start_time)
            raise error

        except APIConnectionError as e:
            error = ProcessError("OpenAI", "Failed to connect to OpenAI API", e)
            if self.logger:
                self.logger.log_process_error("OpenAI", error, start_time)
            raise error

        except APIError as e:
            error = ProcessError("OpenAI", f"API error: {str(e)}", e)
            if self.logger:
                self.logger.log_process_error("OpenAI", error, start_time)
            raise error

        except Exception as e:
            error = ProcessError("OpenAI", f"Unexpected error: {str(e)}", e)
            if self.logger:
                self.logger.log_process_error("OpenAI", error, start_time)
            raise error

    def _build_prompt(self, articles: List[Dict]) -> str:
        """
        Build the prompt for OpenAI based on articles

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
        prompt = f"""I have collected {len(articles)} articles from various sources on a specific topic. Your task is to:

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
