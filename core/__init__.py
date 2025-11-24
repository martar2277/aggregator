"""
News Aggregator Core Module
Contains base classes and utilities
"""

from .base import Component, Fetcher, Processor, Storage, Output, Pipeline
from .errors import (
    AggregatorError,
    FetchError,
    ProcessError,
    StorageError,
    ConfigError
)
from .logger import Logger

__all__ = [
    'Component',
    'Fetcher',
    'Processor',
    'Storage',
    'Output',
    'Pipeline',
    'AggregatorError',
    'FetchError',
    'ProcessError',
    'StorageError',
    'ConfigError',
    'Logger'
]
