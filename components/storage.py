"""
Storage Component
Handles data persistence using JSON files
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from core.base import Storage
from core.errors import StorageError


class JSONStorage(Storage):
    """
    Simple JSON-based storage for articles and syntheses
    Suitable for Sprint 1, can be replaced with database later
    """

    def __init__(self, storage_dir: str = "data", **kwargs):
        super().__init__(**kwargs)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.raw_dir = self.storage_dir / "raw"
        self.syntheses_dir = self.storage_dir / "syntheses"
        self.raw_dir.mkdir(exist_ok=True)
        self.syntheses_dir.mkdir(exist_ok=True)

    def execute(self, data):
        """Execute method required by Component base class"""
        return self.save(data)

    def save(self, data: Any, metadata: Optional[Dict] = None) -> str:
        """
        Save data to JSON files

        Args:
            data: Dictionary containing 'synthesis', 'articles', and 'metadata'
            metadata: Optional additional metadata

        Returns:
            Identifier (timestamp-based) of saved data

        Raises:
            StorageError: If save operation fails
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            identifier = f"{timestamp}"

            # Add topic to identifier if available
            if metadata and metadata.get('topic'):
                topic_slug = self._slugify(metadata['topic'])
                identifier = f"{timestamp}_{topic_slug}"

            # Save synthesis
            synthesis_file = self.syntheses_dir / f"{identifier}.json"
            synthesis_data = {
                'identifier': identifier,
                'timestamp': datetime.now().isoformat(),
                'synthesis': data.get('synthesis', ''),
                'metadata': metadata or {},
                'article_count': len(data.get('articles', []))
            }

            with open(synthesis_file, 'w', encoding='utf-8') as f:
                json.dump(synthesis_data, f, indent=2, ensure_ascii=False)

            # Save raw articles
            raw_file = self.raw_dir / f"{identifier}.json"
            raw_data = {
                'identifier': identifier,
                'timestamp': datetime.now().isoformat(),
                'articles': data.get('articles', []),
                'metadata': metadata or {}
            }

            with open(raw_file, 'w', encoding='utf-8') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)

            # Update index file
            self._update_index(identifier, metadata)

            return identifier

        except IOError as e:
            raise StorageError("save", f"Failed to write files: {str(e)}", e)
        except Exception as e:
            raise StorageError("save", f"Unexpected error: {str(e)}", e)

    def load(self, query: Dict) -> Any:
        """
        Load data based on query

        Args:
            query: Dictionary with 'identifier' or other search criteria

        Returns:
            Loaded data dictionary

        Raises:
            StorageError: If load operation fails
        """
        try:
            identifier = query.get('identifier')
            if not identifier:
                raise StorageError("load", "No identifier provided in query")

            # Try to load synthesis
            synthesis_file = self.syntheses_dir / f"{identifier}.json"
            raw_file = self.raw_dir / f"{identifier}.json"

            if not synthesis_file.exists():
                raise StorageError("load", f"Synthesis file not found: {identifier}")

            with open(synthesis_file, 'r', encoding='utf-8') as f:
                synthesis_data = json.load(f)

            # Load raw articles if available
            articles = []
            if raw_file.exists():
                with open(raw_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    articles = raw_data.get('articles', [])

            return {
                'synthesis': synthesis_data.get('synthesis'),
                'articles': articles,
                'metadata': synthesis_data.get('metadata'),
                'timestamp': synthesis_data.get('timestamp')
            }

        except StorageError:
            raise
        except IOError as e:
            raise StorageError("load", f"Failed to read files: {str(e)}", e)
        except json.JSONDecodeError as e:
            raise StorageError("load", f"Invalid JSON format: {str(e)}", e)
        except Exception as e:
            raise StorageError("load", f"Unexpected error: {str(e)}", e)

    def list_all(self) -> list:
        """
        List all stored syntheses

        Returns:
            List of synthesis metadata
        """
        try:
            index_file = self.storage_dir / "index.json"
            if not index_file.exists():
                return []

            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
                return index.get('syntheses', [])

        except Exception as e:
            if self.logger:
                self.logger.log_error("storage", f"Failed to list syntheses: {e}")
            return []

    def _update_index(self, identifier: str, metadata: Optional[Dict]):
        """
        Update the index file with new entry

        Args:
            identifier: Storage identifier
            metadata: Entry metadata
        """
        index_file = self.storage_dir / "index.json"

        # Load existing index
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                index = json.load(f)
        else:
            index = {'syntheses': []}

        # Add new entry
        entry = {
            'identifier': identifier,
            'timestamp': datetime.now().isoformat(),
            'topic': metadata.get('topic') if metadata else None,
            'sources': metadata.get('sources') if metadata else [],
            'article_count': metadata.get('article_count') if metadata else 0
        }

        index['syntheses'].append(entry)

        # Save updated index
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _slugify(self, text: str, max_length: int = 50) -> str:
        """
        Convert text to a URL-safe slug

        Args:
            text: Text to slugify
            max_length: Maximum length of slug

        Returns:
            Slugified text
        """
        import re
        # Convert to lowercase and replace spaces with underscores
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '_', slug)
        return slug[:max_length]
