"""
ZoektPy: Python client library for Zoekt code search
"""

__version__ = "0.1.0"

from .client import ZoektClient, AsyncZoektClient
from .models import (
    SearchOptions,
    ListOptions,
    ListOptionsField,
    SearchResult,
    FileMatch,
    ChunkMatch,
    LineMatch,
    Position,
    Range,
    SymbolInfo,
    RepositoryInfo,
    RepositoryList,
)
from .exceptions import (
    ZoektError, 
    ZoektTimeoutError, 
    ZoektConnectionError,
    ZoektAPIError,
    ZoektParseError
)
from .utils import (
    normalize_search_options,
    decode_base64,
    parse_query_components,
    build_query
)

__all__ = [
    "ZoektClient",
    "AsyncZoektClient",
    "SearchOptions",
    "ListOptions",
    "ListOptionsField",
    "SearchResult",
    "FileMatch",
    "ChunkMatch",
    "LineMatch",
    "RepositoryInfo",
    "RepositoryList",
    "Position",
    "Range",
    "SymbolInfo",
    "ZoektError",
    "ZoektTimeoutError",
    "ZoektConnectionError",
    "ZoektAPIError",
    "ZoektParseError",
    "normalize_search_options",
    "decode_base64",
    "parse_query_components",
    "build_query",
]