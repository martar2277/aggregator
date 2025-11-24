"""
Custom exception classes for the News Aggregator
"""

class AggregatorError(Exception):
    """Base exception for all aggregator errors"""
    pass


class FetchError(AggregatorError):
    """Raised when fetching data from a source fails"""
    def __init__(self, source: str, message: str, original_error: Exception = None):
        self.source = source
        self.original_error = original_error
        super().__init__(f"Failed to fetch from {source}: {message}")


class ProcessError(AggregatorError):
    """Raised when processing/LLM operations fail"""
    def __init__(self, processor: str, message: str, original_error: Exception = None):
        self.processor = processor
        self.original_error = original_error
        super().__init__(f"Processing failed ({processor}): {message}")


class StorageError(AggregatorError):
    """Raised when storage operations fail"""
    def __init__(self, operation: str, message: str, original_error: Exception = None):
        self.operation = operation
        self.original_error = original_error
        super().__init__(f"Storage {operation} failed: {message}")


class ConfigError(AggregatorError):
    """Raised when configuration is invalid or missing"""
    def __init__(self, config_key: str, message: str):
        self.config_key = config_key
        super().__init__(f"Configuration error ({config_key}): {message}")
