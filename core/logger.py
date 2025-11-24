"""
Observer/Logger component for tracking operations, costs, and errors
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from rich.console import Console
from rich.table import Table

console = Console()


class Logger:
    """
    Centralized logging and monitoring for the aggregator
    Tracks operations, costs, errors, and performance metrics
    """

    def __init__(self, log_dir: str = "logs", enable_console: bool = True):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.enable_console = enable_console

        # Setup file logging
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"session_{self.session_id}.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler() if enable_console else logging.NullHandler()
            ]
        )
        self.logger = logging.getLogger('NewsAggregator')

        # Metrics tracking
        self.metrics = {
            'session_start': datetime.now().isoformat(),
            'operations': [],
            'errors': [],
            'costs': {
                'total': 0.0,
                'by_llm': {}
            },
            'performance': {
                'fetch_times': [],
                'process_times': [],
                'total_articles': 0
            }
        }

    def log_fetch_start(self, source: str):
        """Log the start of a fetch operation"""
        if self.enable_console:
            console.print(f"[blue]📡 Fetching from: {source}[/blue]")
        self.logger.info(f"Fetch started: {source}")
        return datetime.now()

    def log_fetch_success(self, source: str, article_count: int, start_time: datetime):
        """Log successful fetch operation"""
        duration = (datetime.now() - start_time).total_seconds()
        if self.enable_console:
            console.print(f"[green]✓ Fetched {article_count} articles from {source} ({duration:.2f}s)[/green]")

        self.logger.info(f"Fetch completed: {source} - {article_count} articles in {duration:.2f}s")
        self.metrics['operations'].append({
            'type': 'fetch',
            'source': source,
            'article_count': article_count,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })
        self.metrics['performance']['fetch_times'].append(duration)
        self.metrics['performance']['total_articles'] += article_count

    def log_fetch_error(self, source: str, error: Exception, start_time: datetime):
        """Log failed fetch operation"""
        duration = (datetime.now() - start_time).total_seconds()
        if self.enable_console:
            console.print(f"[red]✗ Failed to fetch from {source}: {str(error)}[/red]")

        self.logger.error(f"Fetch failed: {source} - {str(error)}")
        self.metrics['errors'].append({
            'type': 'fetch',
            'source': source,
            'error': str(error),
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })

    def log_process_start(self, processor_name: str, article_count: int):
        """Log the start of processing operation"""
        if self.enable_console:
            console.print(f"[blue]🤖 Processing {article_count} articles with {processor_name}...[/blue]")
        self.logger.info(f"Processing started: {processor_name} - {article_count} articles")
        return datetime.now()

    def log_process_success(self, processor_name: str, start_time: datetime,
                           tokens_used: Optional[int] = None, cost: Optional[float] = None):
        """Log successful processing operation"""
        duration = (datetime.now() - start_time).total_seconds()

        msg = f"✓ Processing completed ({duration:.2f}s)"
        if tokens_used:
            msg += f" - {tokens_used} tokens"
        if cost:
            msg += f" - ${cost:.4f}"

        if self.enable_console:
            console.print(f"[green]{msg}[/green]")

        self.logger.info(f"Processing completed: {processor_name} in {duration:.2f}s")

        operation = {
            'type': 'process',
            'processor': processor_name,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }

        if tokens_used:
            operation['tokens'] = tokens_used
        if cost:
            operation['cost'] = cost
            self.metrics['costs']['total'] += cost
            if processor_name not in self.metrics['costs']['by_llm']:
                self.metrics['costs']['by_llm'][processor_name] = 0.0
            self.metrics['costs']['by_llm'][processor_name] += cost

        self.metrics['operations'].append(operation)
        self.metrics['performance']['process_times'].append(duration)

    def log_process_error(self, processor_name: str, error: Exception, start_time: datetime):
        """Log failed processing operation"""
        duration = (datetime.now() - start_time).total_seconds()
        if self.enable_console:
            console.print(f"[red]✗ Processing failed: {str(error)}[/red]")

        self.logger.error(f"Processing failed: {processor_name} - {str(error)}")
        self.metrics['errors'].append({
            'type': 'process',
            'processor': processor_name,
            'error': str(error),
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        })

    def log_storage_operation(self, operation: str, success: bool, details: Optional[str] = None):
        """Log storage operations"""
        if success:
            if self.enable_console:
                console.print(f"[green]✓ Storage {operation} successful[/green]")
            self.logger.info(f"Storage {operation} successful: {details}")
        else:
            if self.enable_console:
                console.print(f"[red]✗ Storage {operation} failed[/red]")
            self.logger.error(f"Storage {operation} failed: {details}")

    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """Log general errors"""
        if self.enable_console:
            console.print(f"[red]✗ Error ({error_type}): {message}[/red]")

        self.logger.error(f"{error_type}: {message}")
        self.metrics['errors'].append({
            'type': error_type,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })

    def log_info(self, message: str):
        """Log general information"""
        if self.enable_console:
            console.print(f"[dim]{message}[/dim]")
        self.logger.info(message)

    def print_summary(self):
        """Print a summary of the session"""
        table = Table(title="Session Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        total_ops = len(self.metrics['operations'])
        total_errors = len(self.metrics['errors'])
        total_cost = self.metrics['costs']['total']
        total_articles = self.metrics['performance']['total_articles']

        avg_fetch_time = (sum(self.metrics['performance']['fetch_times']) /
                         len(self.metrics['performance']['fetch_times'])
                         if self.metrics['performance']['fetch_times'] else 0)

        avg_process_time = (sum(self.metrics['performance']['process_times']) /
                           len(self.metrics['performance']['process_times'])
                           if self.metrics['performance']['process_times'] else 0)

        table.add_row("Total Operations", str(total_ops))
        table.add_row("Total Errors", str(total_errors))
        table.add_row("Articles Processed", str(total_articles))
        table.add_row("Total Cost", f"${total_cost:.4f}")
        table.add_row("Avg Fetch Time", f"{avg_fetch_time:.2f}s")
        table.add_row("Avg Process Time", f"{avg_process_time:.2f}s")

        console.print(table)

        # Print cost breakdown by LLM
        if self.metrics['costs']['by_llm']:
            cost_table = Table(title="Cost Breakdown by LLM")
            cost_table.add_column("LLM", style="cyan")
            cost_table.add_column("Cost", style="green")

            for llm, cost in self.metrics['costs']['by_llm'].items():
                cost_table.add_row(llm, f"${cost:.4f}")

            console.print(cost_table)

    def save_metrics(self):
        """Save metrics to JSON file"""
        metrics_file = self.log_dir / f"metrics_{self.session_id}.json"
        self.metrics['session_end'] = datetime.now().isoformat()

        with open(metrics_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

        self.logger.info(f"Metrics saved to {metrics_file}")
        return metrics_file
