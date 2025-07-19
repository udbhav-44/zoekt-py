"""
ZoektPy: Python client library for Zoekt code search
"""

__version__ = "0.1.0"

from .client import ZoektClient, AsyncZoektClient
from .models import (
    SearchOptions,
    ListOptions,
    SearchResult,
    FileMatch,
    ChunkMatch,
    LineMatch,
    RepositoryInfo,
)
from .exceptions import ZoektError, ZoektTimeoutError, ZoektConnectionError

__all__ = [
    "ZoektClient",
    "AsyncZoektClient",
    "SearchOptions",
    "ListOptions",
    "SearchResult",
    "FileMatch",
    "ChunkMatch",
    "LineMatch",
    "RepositoryInfo",
    "ZoektError",
    "ZoektTimeoutError",
    "ZoektConnectionError",
]