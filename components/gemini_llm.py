"""
Google Gemini LLM Processor Component
Processes articles using Google Gemini models for synthesis
"""

import os
from datetime import datetime
from typing import List, Dict, Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from core.base import Processor
from core.errors import ProcessError, ConfigError


class GeminiProcessor(Processor):
    """
    Processes articles using Google Gemini models
    Handles API calls, cost tracking, and error handling
    """

    # Token pricing (as of 2024) - Gemini has generous free tier
    PRICING = {
        'gemini-1.5-flash': {
            'input': 0.075 / 1_000_000,   # $0.075 per 1M input tokens
            'output': 0.30 / 1_000_000    # $0.30 per 1M output tokens
        },
        'gemini-1.5-pro': {
            'input': 1.25 / 1_000_000,    # $1.25 per 1M input tokens
            'output': 5.0 / 1_000_000     # $5.00 per 1M output tokens
        },
        'gemini-pro': {
            'input': 0.50 / 1_000_000,
            'output': 1.50 / 1_000_000
        }
    }

    def __init__(self, model: str = "gemini-1.5-flash",
                 max_tokens: int = 4096, **kwargs):
        super().__init__(**kwargs)
        self.model = model
        self.max_tokens = max_tokens

        # Initialize Gemini client
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ConfigError("GEMINI_API_KEY",
                            "Gemini API key not found in environment variables")

        genai.configure(api_key=api_key)
        self.client = genai.GenerativeModel(model)

    def process(self, articles: List[Dict]) -> str:
        """
        Process articles and generate synthesis using Gemini

        Args:
            articles: List of article dictionaries

        Returns:
            Synthesized analysis as string

        Raises:
            ProcessError: If processing fails
        """
        start_time = datetime.now()

        if self.logger:
            self.logger.log_process_start(f"Gemini-{self.model}", len(articles))

        try:
            # Build the prompt
            prompt = self._build_prompt(articles)

            # Call Gemini API
            response = self.client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=self.max_tokens,
                )
            )

            # Extract synthesis
            synthesis = response.text

            # Estimate tokens and cost (Gemini doesn't always provide exact counts)
            # Using rough estimate: 1 token ≈ 4 characters
            estimated_input_tokens = len(prompt) // 4
            estimated_output_tokens = len(synthesis) // 4
            cost = self._calculate_cost(estimated_input_tokens, estimated_output_tokens)

            if self.logger:
                self.logger.log_process_success(
                    f"Gemini-{self.model}",
                    start_time,
                    tokens_used=estimated_input_tokens + estimated_output_tokens,
                    cost=cost
                )

            return synthesis

        except google_exceptions.ResourceExhausted as e:
            error = ProcessError("Gemini", "Rate limit exceeded or quota exhausted", e)
            if self.logger:
                self.logger.log_process_error("Gemini", error, start_time)
            raise error

        except google_exceptions.GoogleAPIError as e:
            error = ProcessError("Gemini", f"API error: {str(e)}", e)
            if self.logger:
                self.logger.log_process_error("Gemini", error, start_time)
            raise error

        except Exception as e:
            error = ProcessError("Gemini", f"Unexpected error: {str(e)}", e)
            if self.logger:
                self.logger.log_process_error("Gemini", error, start_time)
            raise error

    def _build_prompt(self, articles: List[Dict]) -> str:
        """
        Build the prompt for Gemini based on articles

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
            input_tokens: Number of input tokens (estimated)
            output_tokens: Number of output tokens (estimated)

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
