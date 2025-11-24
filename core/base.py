"""
Abstract base classes for the News Aggregator pipeline
Defines the core architecture with proper error handling
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from .errors import AggregatorError, FetchError, ProcessError, StorageError
from .logger import Logger


class Component(ABC):
    """Base class for all pipeline components"""

    def __init__(self, config: Optional[Dict] = None, logger: Optional[Logger] = None):
        self.config = config or {}
        self.logger = logger

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """Execute the component's main operation"""
        pass


class Fetcher(Component):
    """Abstract fetcher - implementations: RSS, API, Scraper, PDF, etc."""

    @abstractmethod
    def fetch(self, source: str) -> List[Dict]:
        """
        Fetch articles from a source
        Returns: List of article dictionaries with keys: title, summary, link, published, source
        """
        pass


class Processor(Component):
    """Abstract processor - implementations: LLM, translation, analysis"""

    @abstractmethod
    def process(self, articles: List[Dict]) -> str:
        """
        Process articles and return synthesis
        Returns: String containing the synthesized/processed result
        """
        pass


class Storage(Component):
    """Abstract storage - implementations: JSON, SQLite, PostgreSQL"""

    @abstractmethod
    def save(self, data: Any, metadata: Optional[Dict] = None) -> str:
        """
        Save data with optional metadata
        Returns: Identifier/path of saved data
        """
        pass

    @abstractmethod
    def load(self, query: Dict) -> Any:
        """
        Load data based on query parameters
        Returns: Retrieved data
        """
        pass


class Output(Component):
    """Abstract output - implementations: Markdown, HTML, PDF, Console"""

    @abstractmethod
    def generate(self, synthesis: str, metadata: Optional[Dict] = None) -> str:
        """
        Generate formatted output
        Returns: Path to generated output file or formatted string
        """
        pass


class Pipeline:
    """
    Orchestrator that connects all components
    Handles the complete flow with error handling and logging
    """

    def __init__(self, logger: Optional[Logger] = None):
        self.fetcher: Optional[Fetcher] = None
        self.processor: Optional[Processor] = None
        self.storage: Optional[Storage] = None
        self.output: Optional[Output] = None
        self.logger = logger or Logger()

    def set_fetcher(self, fetcher: Fetcher) -> 'Pipeline':
        """Set the fetcher component (method chaining)"""
        self.fetcher = fetcher
        if not fetcher.logger:
            fetcher.logger = self.logger
        return self

    def set_processor(self, processor: Processor) -> 'Pipeline':
        """Set the processor component (method chaining)"""
        self.processor = processor
        if not processor.logger:
            processor.logger = self.logger
        return self

    def set_storage(self, storage: Storage) -> 'Pipeline':
        """Set the storage component (method chaining)"""
        self.storage = storage
        if not storage.logger:
            storage.logger = self.logger
        return self

    def set_output(self, output: Output) -> 'Pipeline':
        """Set the output component (method chaining)"""
        self.output = output
        if not output.logger:
            output.logger = self.logger
        return self

    def run(self, sources: List[str], topic: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the complete pipeline with error handling

        Args:
            sources: List of source URLs to fetch from
            topic: Optional topic description for context

        Returns:
            Dictionary containing results and metadata

        Raises:
            AggregatorError: If critical errors occur
        """
        start_time = datetime.now()
        results = {
            'success': False,
            'topic': topic,
            'sources': sources,
            'articles_processed': 0,
            'errors': [],
            'output_path': None,
            'storage_id': None,
            'duration': 0
        }

        try:
            # Validate components
            if not self.fetcher:
                raise AggregatorError("No fetcher configured")
            if not self.processor:
                raise AggregatorError("No processor configured")

            # Phase 1: Fetch articles from all sources
            self.logger.log_info(f"Starting pipeline for topic: {topic or 'None specified'}")
            all_articles = []
            failed_sources = []

            for source in sources:
                try:
                    articles = self.fetcher.fetch(source)
                    all_articles.extend(articles)
                except FetchError as e:
                    self.logger.log_fetch_error(source, e, datetime.now())
                    failed_sources.append(source)
                    results['errors'].append({
                        'phase': 'fetch',
                        'source': source,
                        'error': str(e)
                    })
                    # Continue with other sources
                    continue
                except Exception as e:
                    # Unexpected error - wrap it
                    fetch_error = FetchError(source, str(e), e)
                    self.logger.log_fetch_error(source, fetch_error, datetime.now())
                    failed_sources.append(source)
                    results['errors'].append({
                        'phase': 'fetch',
                        'source': source,
                        'error': str(e)
                    })
                    continue

            # Check if we got any articles
            if not all_articles:
                error_msg = f"No articles fetched from any source. Failed sources: {failed_sources}"
                self.logger.log_error("fetch", error_msg)
                raise FetchError("all_sources", error_msg)

            results['articles_processed'] = len(all_articles)
            self.logger.log_info(f"Successfully fetched {len(all_articles)} articles from {len(sources) - len(failed_sources)}/{len(sources)} sources")

            # Phase 2: Process articles
            try:
                synthesis = self.processor.process(all_articles)
            except ProcessError as e:
                self.logger.log_process_error("processor", e, datetime.now())
                results['errors'].append({
                    'phase': 'process',
                    'error': str(e)
                })
                raise
            except Exception as e:
                # Unexpected error - wrap it
                process_error = ProcessError("unknown", str(e), e)
                self.logger.log_process_error("processor", process_error, datetime.now())
                results['errors'].append({
                    'phase': 'process',
                    'error': str(e)
                })
                raise process_error

            # Phase 3: Store results (optional)
            metadata = {
                'topic': topic,
                'sources': sources,
                'article_count': len(all_articles),
                'timestamp': datetime.now().isoformat(),
                'failed_sources': failed_sources
            }

            if self.storage:
                try:
                    storage_id = self.storage.save({
                        'synthesis': synthesis,
                        'articles': all_articles,
                        'metadata': metadata
                    }, metadata)
                    results['storage_id'] = storage_id
                    self.logger.log_storage_operation("save", True, storage_id)
                except StorageError as e:
                    self.logger.log_storage_operation("save", False, str(e))
                    results['errors'].append({
                        'phase': 'storage',
                        'error': str(e)
                    })
                    # Non-critical, continue
                except Exception as e:
                    storage_error = StorageError("save", str(e), e)
                    self.logger.log_storage_operation("save", False, str(e))
                    results['errors'].append({
                        'phase': 'storage',
                        'error': str(e)
                    })
                    # Non-critical, continue

            # Phase 4: Generate output (optional)
            if self.output:
                try:
                    output_path = self.output.generate(synthesis, metadata)
                    results['output_path'] = output_path
                    self.logger.log_info(f"Output generated: {output_path}")
                except Exception as e:
                    self.logger.log_error("output", str(e))
                    results['errors'].append({
                        'phase': 'output',
                        'error': str(e)
                    })
                    # Non-critical, continue

            # Success!
            results['success'] = True
            results['synthesis'] = synthesis
            duration = (datetime.now() - start_time).total_seconds()
            results['duration'] = duration

            self.logger.log_info(f"Pipeline completed successfully in {duration:.2f}s")

            return results

        except AggregatorError as e:
            # Known error types - already logged
            duration = (datetime.now() - start_time).total_seconds()
            results['duration'] = duration
            self.logger.log_error("pipeline", str(e))
            raise

        except Exception as e:
            # Unexpected error
            duration = (datetime.now() - start_time).total_seconds()
            results['duration'] = duration
            self.logger.log_error("pipeline", f"Unexpected error: {str(e)}")
            raise AggregatorError(f"Pipeline failed with unexpected error: {str(e)}") from e

        finally:
            # Always save metrics
            try:
                self.logger.save_metrics()
            except Exception as e:
                # Don't let metrics saving crash the pipeline
                print(f"Warning: Failed to save metrics: {e}")
