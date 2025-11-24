#!/usr/bin/env python3
"""
News Aggregator - Main CLI Application
Sprint 1: Complete working version with RSS, LLM, storage, and output
"""

import sys
import typer
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich import print as rprint

from core.base import Pipeline, Processor
from core.logger import Logger
from core.errors import AggregatorError, ConfigError, ProcessError
from components.rss import RSSFetcher
from components.llm import ClaudeLLMProcessor
from components.openai_llm import OpenAIProcessor
from components.gemini_llm import GeminiProcessor
from components.storage import JSONStorage
from components.output import MarkdownOutput
from config import Config

app = typer.Typer(help="News Aggregator - Multi-source news analysis with LLM")
console = Console()


def get_llm_processor(provider: str, logger: Logger) -> Processor:
    """
    Get LLM processor based on provider with fallback logic

    Args:
        provider: LLM provider name ("openai", "gemini", "anthropic")
        logger: Logger instance

    Returns:
        Configured processor

    Raises:
        ConfigError: If provider is not available
    """
    # Get model name
    model = Config.DEFAULT_LLM_MODEL or Config.DEFAULT_MODELS.get(provider, "")

    processors_map = {
        "openai": (OpenAIProcessor, Config.OPENAI_API_KEY),
        "gemini": (GeminiProcessor, Config.GEMINI_API_KEY),
        "anthropic": (ClaudeLLMProcessor, Config.ANTHROPIC_API_KEY)
    }

    if provider not in processors_map:
        raise ConfigError("LLM_PROVIDER", f"Unknown provider: {provider}")

    processor_class, api_key = processors_map[provider]
    if not api_key:
        raise ConfigError(f"{provider.upper()}_API_KEY",
                         f"{provider.capitalize()} API key not found")

    # Auto-select model if not specified
    if not model:
        model = Config.DEFAULT_MODELS.get(provider)

    return processor_class(model=model, logger=logger)


def create_pipeline(logger: Optional[Logger] = None, provider: Optional[str] = None, topic: Optional[str] = None) -> Pipeline:
    """
    Create and configure the pipeline with all components
    Uses multi-LLM fallback logic

    Args:
        logger: Optional logger instance
        provider: Optional LLM provider override
        topic: Optional topic filter for fetcher

    Returns:
        Configured Pipeline
    """
    if not logger:
        logger = Logger()

    # Determine which LLM provider to use
    if not provider:
        provider = Config.DEFAULT_LLM_PROVIDER

    # Get available providers for fallback
    available_providers = Config.get_available_providers()

    if not available_providers:
        raise ConfigError("API_KEYS", "No LLM API keys configured")

    # Try to use specified provider, fallback to first available
    if provider not in available_providers:
        logger.log_info(f"Provider '{provider}' not available, using '{available_providers[0]}'")
        provider = available_providers[0]

    logger.log_info(f"Using LLM provider: {provider}")

    # Create processor
    try:
        processor = get_llm_processor(provider, logger)
    except ConfigError as e:
        # Try fallback to any available provider
        for fallback_provider in available_providers:
            if fallback_provider != provider:
                logger.log_info(f"Falling back to provider: {fallback_provider}")
                try:
                    processor = get_llm_processor(fallback_provider, logger)
                    break
                except ConfigError:
                    continue
        else:
            raise ConfigError("LLM_PROVIDER", "No working LLM provider found")

    pipeline = Pipeline(logger=logger)
    pipeline.set_fetcher(RSSFetcher(max_articles=Config.MAX_ARTICLES_PER_SOURCE, topic_filter=topic, logger=logger)) \
            .set_processor(processor) \
            .set_storage(JSONStorage(storage_dir=Config.DATA_DIR, logger=logger)) \
            .set_output(MarkdownOutput(output_dir=Config.OUTPUT_DIR, logger=logger))

    return pipeline


@app.command()
def analyze(
    topic: str = typer.Argument(..., help="Topic to analyze (e.g., 'AI regulation in EU')"),
    sources: Optional[List[str]] = typer.Option(None, "--source", "-s", help="RSS feed URLs"),
    category: Optional[str] = typer.Option(None, "--category", "-c",
                                           help="Source category: default, international, tech, all"),
    no_storage: bool = typer.Option(False, "--no-storage", help="Skip saving to storage"),
    no_output: bool = typer.Option(False, "--no-output", help="Skip markdown output generation"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
):
    """
    Analyze news articles on a specific topic

    Examples:
        python main.py analyze "AI policy in Estonia"
        python main.py analyze "Climate change" -c international
        python main.py analyze "Tech startups" -s https://techcrunch.com/feed/
    """
    console.print(Panel.fit(
        f"[bold blue]News Aggregator[/bold blue]\n"
        f"Topic: {topic}",
        border_style="blue"
    ))

    # Validate configuration
    config_errors = Config.validate()
    if config_errors:
        console.print("[red]Configuration errors:[/red]")
        for error in config_errors:
            console.print(f"  - {error}")
        raise typer.Exit(1)

    # Determine sources
    if sources:
        source_urls = list(sources)
    elif category:
        source_urls = list(Config.get_sources_by_category(category).values())
    else:
        source_urls = list(Config.DEFAULT_SOURCES.values())

    console.print(f"\n[dim]Using {len(source_urls)} source(s)[/dim]\n")

    # Create logger and pipeline
    logger = Logger(enable_console=verbose)
    pipeline = create_pipeline(logger, topic=topic)

    # Remove components if requested
    if no_storage:
        pipeline.storage = None
    if no_output:
        pipeline.output = None

    try:
        # Run the pipeline
        results = pipeline.run(source_urls, topic=topic)

        # Display results
        if results['success']:
            console.print("\n[green bold]✓ Analysis Complete![/green bold]\n")

            # Print synthesis
            console.print(Panel(
                results['synthesis'],
                title="[bold]Synthesis[/bold]",
                border_style="green"
            ))

            # Print metadata
            console.print(f"\n[dim]Articles processed: {results['articles_processed']}[/dim]")
            console.print(f"[dim]Duration: {results['duration']:.2f}s[/dim]")

            if results.get('output_path'):
                console.print(f"[dim]Output saved: {results['output_path']}[/dim]")

            if results.get('storage_id'):
                console.print(f"[dim]Storage ID: {results['storage_id']}[/dim]")

            # Print summary
            logger.print_summary()

        else:
            console.print("[red]Analysis failed[/red]")
            if results.get('errors'):
                console.print("\n[red]Errors:[/red]")
                for error in results['errors']:
                    console.print(f"  - {error}")

    except ConfigError as e:
        console.print(f"[red]Configuration Error: {e}[/red]")
        raise typer.Exit(1)

    except AggregatorError as e:
        console.print(f"[red]Error: {e}[/red]")
        logger.print_summary()
        raise typer.Exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        logger.print_summary()
        raise typer.Exit(130)

    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.print_summary()
        raise typer.Exit(1)


@app.command()
def list_sources(
    category: Optional[str] = typer.Option("all", "--category", "-c",
                                           help="Category: default, international, tech, all")
):
    """
    List available RSS sources by category
    """
    console.print(Panel.fit("[bold]Available RSS Sources[/bold]", border_style="blue"))

    sources = Config.get_sources_by_category(category)

    for name, url in sources.items():
        console.print(f"  [cyan]{name:20}[/cyan] [dim]{url}[/dim]")

    console.print(f"\n[dim]Total: {len(sources)} sources[/dim]")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of recent analyses to show")
):
    """
    Show history of past analyses
    """
    console.print(Panel.fit("[bold]Analysis History[/bold]", border_style="blue"))

    try:
        storage = JSONStorage(storage_dir=Config.DATA_DIR)
        entries = storage.list_all()

        if not entries:
            console.print("[dim]No analyses found[/dim]")
            return

        # Show most recent first
        for entry in reversed(entries[-limit:]):
            console.print(f"\n[cyan]{entry['identifier']}[/cyan]")
            console.print(f"  Topic: {entry.get('topic', 'N/A')}")
            console.print(f"  Time: {entry['timestamp']}")
            console.print(f"  Articles: {entry.get('article_count', 0)}")
            console.print(f"  Sources: {len(entry.get('sources', []))}")

    except Exception as e:
        console.print(f"[red]Error loading history: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def show(
    identifier: str = typer.Argument(..., help="Analysis identifier to show")
):
    """
    Show a specific analysis by identifier
    """
    try:
        storage = JSONStorage(storage_dir=Config.DATA_DIR)
        data = storage.load({'identifier': identifier})

        console.print(Panel.fit(
            f"[bold]Analysis: {identifier}[/bold]",
            border_style="blue"
        ))

        console.print(f"\n[dim]Topic: {data['metadata'].get('topic', 'N/A')}[/dim]")
        console.print(f"[dim]Time: {data['timestamp']}[/dim]")
        console.print(f"[dim]Articles: {len(data['articles'])}[/dim]\n")

        console.print(Panel(
            data['synthesis'],
            title="[bold]Synthesis[/bold]",
            border_style="green"
        ))

    except Exception as e:
        console.print(f"[red]Error loading analysis: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test():
    """
    Test the pipeline with a simple query
    """
    console.print(Panel.fit("[bold yellow]Testing Pipeline[/bold yellow]", border_style="yellow"))

    # Validate configuration
    config_errors = Config.validate()
    if config_errors:
        console.print("[red]Configuration errors:[/red]")
        for error in config_errors:
            console.print(f"  - {error}")
        raise typer.Exit(1)

    console.print("[green]✓ Configuration valid[/green]")

    # Test with one source
    test_source = list(Config.DEFAULT_SOURCES.values())[0]
    console.print(f"[dim]Testing with source: {test_source}[/dim]\n")

    try:
        logger = Logger(enable_console=True)
        pipeline = create_pipeline(logger, topic="TEST")
        results = pipeline.run([test_source], topic="TEST")

        if results['success'] and results['articles_processed'] > 0:
            console.print("\n[green bold]✓ All components working![/green bold]")
            logger.print_summary()
        else:
            console.print("\n[red]✗ Test failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[red]✗ Test failed: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config():
    """
    Show current configuration
    """
    Config.print_config()


if __name__ == "__main__":
    app()
