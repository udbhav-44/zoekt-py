"""
Synchronous and asynchronous clients for the Zoekt code search API
"""

import base64
import logging
import time
from typing import Any, Dict, List, Optional, Union, Tuple, Iterator, AsyncIterator
import asyncio
import aiohttp
import requests
from pydantic import ValidationError
from aiohttp import ClientTimeout
from .exceptions import (
    ZoektAPIError,
    ZoektConnectionError,
    ZoektParseError,
    ZoektTimeoutError,
)
from .models import (
    FileMatch,
    ListOptions,
    RepositoryList,
    SearchOptions,
    SearchResult,
)
from .utils import normalize_search_options, parse_query_components, build_query

logger = logging.getLogger("zoektpy")


class ZoektClient:
    """
    Synchronous client for the Zoekt code search API
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6070,
        timeout: float = 10.0,
    ):
        """
        Initialize a new Zoekt client
        
        Args:
            host: Zoekt server hostname
            port: Zoekt server port
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{host}:{port}"
        self.search_url = f"{self.base_url}/api/search"
        self.list_url = f"{self.base_url}/api/list"
        self.timeout = timeout
        self.headers = {"Content-Type": "application/json"}
        self._session = None
    
    def _get_session(self) -> requests.Session:
        """Get or create a requests session"""
        if self._session is None:
            self._session = requests.Session()
        return self._session
    
    def close(self) -> None:
        """Close the client session"""
        if self._session is not None:
            self._session.close()
            self._session = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def search(
        self,
        query: str,
        repo_ids: Optional[List[int]] = None,
        options: Optional[Union[Dict[str, Any], SearchOptions]] = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> SearchResult:
        """
        Search code using the Zoekt API
        
        Args:
            query: Zoekt search query
            repo_ids: Optional list of repository IDs to search
            options: Search options (as dict or SearchOptions object)
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff factor for retries
        
        Returns:
            SearchResult object containing matches and stats
        
        Raises:
            ZoektConnectionError: Error connecting to the server
            ZoektTimeoutError: Request timed out
            ZoektAPIError: Server returned an error response
            ZoektParseError: Error parsing the server response
        """
        logger.debug(f"Search query: {query}")
        
        # Convert SearchOptions object to dict if needed
        if isinstance(options, SearchOptions):
            options = options.model_dump(exclude_none=True)
        else:
            options = options or {}
        
        # Ensure ChunkMatches is True by default
        if "ChunkMatches" not in options:
            options["ChunkMatches"] = True
        
        # Prepare request payload
        payload: Dict[str, Any] = {"Q": query}
        if repo_ids is not None:
            payload["RepoIDs"] = repo_ids
        if options:
            payload["Opts"] = normalize_search_options(options)
        
        # Perform request with retries
        for attempt in range(max_retries):
            try:
                session = self._get_session()
                response = session.post(
                    self.search_url,
                    json=payload,
                    headers=self.headers,
                    timeout=self.timeout,
                )
                if not response.ok:
                    try:
                        message = response.json().get("Error", response.text)
                    except ValueError:
                        message = response.text or "Unknown error"
                    raise ZoektAPIError(status_code=response.status_code, message=message)
                
                data = response.json()
                
                # Zoekt returns the result in a "Result" field
                result_data = data.get("Result", data)
                
                # Parse and validate the response
                try:
                    return SearchResult.model_validate(result_data)
                except ValidationError as e:
                    raise ZoektParseError(f"Failed to parse search response: {e}")
                
            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise ZoektTimeoutError(f"Request timed out after {self.timeout} seconds")
            
            except requests.exceptions.ConnectionError as e:
                if attempt == max_retries - 1:
                    raise ZoektConnectionError(f"Failed to connect to Zoekt server: {e}")
            
            except requests.exceptions.HTTPError as e:
                if attempt == max_retries - 1:
                    raise ZoektAPIError(
                        status_code=e.response.status_code if e.response else 0,
                        message=e.response.json().get("Error", str(e)) if e.response else str(e)
                    )
            
            # Backoff before retrying
            time.sleep(retry_backoff * (2 ** attempt))
        
        # This should not be reached due to the exceptions above
        raise ZoektConnectionError("Failed to connect to Zoekt server after retries")
    
    def list_repositories(
        self,
        query: str = "",
        options: Optional[Union[Dict[str, Any], ListOptions]] = None,
    ) -> RepositoryList:
        """
        List repositories matching the given query
        
        Args:
            query: Zoekt repository query (e.g., "repo:abc")
            options: List options (as dict or ListOptions object)
        
        Returns:
            RepositoryList object containing repositories and stats
        
        Raises:
            ZoektConnectionError: Error connecting to the server
            ZoektTimeoutError: Request timed out
            ZoektAPIError: Server returned an error response
            ZoektParseError: Error parsing the server response
        """
        logger.debug(f"List repositories query: {query}")
        
        # Convert ListOptions object to dict if needed
        if isinstance(options, ListOptions):
            options = options.model_dump(exclude_none=True)
        
        # Prepare request payload
        payload: Dict[str, Any] = {"Q": query}
        if options is not None:
            payload["Opts"] = options
        
        try:
            session = self._get_session()
            response = session.post(
                self.list_url,
                json=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            
            # Zoekt returns the list in a "List" field
            list_data = data.get("List", data)
            
            # Parse and validate the response
            try:
                return RepositoryList.model_validate(list_data)
            except ValidationError as e:
                raise ZoektParseError(f"Failed to parse repository list response: {e}")
            
        except requests.exceptions.Timeout:
            raise ZoektTimeoutError(f"Request timed out after {self.timeout} seconds")
        
        except requests.exceptions.ConnectionError as e:
            raise ZoektConnectionError(f"Failed to connect to Zoekt server: {e}")
        
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 0
            message = str(e)
            raise ZoektAPIError(status_code, message)
    
    def search_by_language(
        self,
        query: str,
        language: str,
        **kwargs
    ) -> SearchResult:
        """
        Search for code in a specific language
        
        Args:
            query: Search query text
            language: Programming language to search
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add or replace the language component
        if "lang" in components:
            components["lang"] = [language]
        else:
            components["lang"] = [language]
        
        full_query = build_query(components)
        return self.search(full_query, **kwargs)
    
    def search_by_file_pattern(
        self,
        query: str,
        file_pattern: str,
        **kwargs
    ) -> SearchResult:
        """
        Search for code matching files with the given pattern
        
        Args:
            query: Search query text
            file_pattern: File pattern (e.g., "*.py")
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add or append to the file component
        if "file" in components:
            components["file"].append(file_pattern)
        else:
            components["file"] = [file_pattern]
        
        full_query = build_query(components)
        return self.search(full_query, **kwargs)
    
    def search_by_repo(
        self,
        query: str,
        repo_pattern: str,
        **kwargs
    ) -> SearchResult:
        """
        Search for code in repositories matching the given pattern
        
        Args:
            query: Search query text
            repo_pattern: Repository pattern (e.g., "myorg/*")
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add or append to the repo component
        if "repo" in components:
            components["repo"].append(repo_pattern)
        else:
            components["repo"] = [repo_pattern]
        
        full_query = build_query(components)
        return self.search(full_query, **kwargs)
    
    def search_case_sensitive(
        self,
        query: str,
        **kwargs
    ) -> SearchResult:
        """
        Perform a case-sensitive search
        
        Args:
            query: Search query text
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Set case sensitivity
        components["case"] = ["yes"]
        
        full_query = build_query(components)
        return self.search(full_query, **kwargs)
    
    def search_symbols(
        self,
        query: str,
        symbol_type: Optional[str] = None,
        **kwargs
    ) -> SearchResult:
        """
        Search for symbols matching the query
        
        Args:
            query: Search query text
            symbol_type: Optional symbol type filter
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add symbol search modifier
        if symbol_type:
            components["sym"] = [symbol_type]
        else:
            components["sym"] = [""]
        
        full_query = build_query(components)
        return self.search(full_query, **kwargs)
    
    def search_with_context(
        self,
        query: str,
        context_lines: int = 5,
        **kwargs
    ) -> SearchResult:
        """
        Search with additional context lines
        
        Args:
            query: Search query text
            context_lines: Number of context lines to include
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        options = kwargs.get("options", {})
        if isinstance(options, SearchOptions):
            options = options.model_dump(exclude_none=True)
        
        options["NumContextLines"] = context_lines
        kwargs["options"] = options
        
        return self.search(query, **kwargs)
    
    def search_batch(
        self,
        queries: List[str],
        **kwargs
    ) -> Dict[str, SearchResult]:
        """
        Perform multiple searches in batch
        
        Args:
            queries: List of search queries
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            Dictionary mapping queries to their SearchResult
        """
        results = {}
        for query in queries:
            results[query] = self.search(query, **kwargs)
        return results


class AsyncZoektClient:
    """
    Asynchronous client for the Zoekt code search API
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6070,
        timeout: float = 10.0,
    ):
        """
        Initialize a new async Zoekt client
        
        Args:
            host: Zoekt server hostname
            port: Zoekt server port
            timeout: Request timeout in seconds
        """
        self.base_url = f"http://{host}:{port}"
        self.search_url = f"{self.base_url}/api/search"
        self.list_url = f"{self.base_url}/api/list"
        self.timeout = timeout
        self.timeout_obj = ClientTimeout(total=timeout) 
        self.headers = {"Content-Type": "application/json"}
        self._session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp client session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(headers=self.headers)
        return self._session
    
    async def close(self) -> None:
        """Close the client session"""
        if self._session is not None and not self._session.closed:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def search(
        self,
        query: str,
        repo_ids: Optional[List[int]] = None,
        options: Optional[Union[Dict[str, Any], SearchOptions]] = None,
        max_retries: int = 3,
        retry_backoff: float = 0.5,
    ) -> SearchResult:
        """
        Search code using the Zoekt API asynchronously
        
        Args:
            query: Zoekt search query
            repo_ids: Optional list of repository IDs to search
            options: Search options (as dict or SearchOptions object)
            max_retries: Maximum number of retry attempts
            retry_backoff: Backoff factor for retries
        
        Returns:
            SearchResult object containing matches and stats
        
        Raises:
            ZoektConnectionError: Error connecting to the server
            ZoektTimeoutError: Request timed out
            ZoektAPIError: Server returned an error response
            ZoektParseError: Error parsing the server response
        """
        logger.debug(f"Async search query: {query}")
        
        # Convert SearchOptions object to dict if needed
        if isinstance(options, SearchOptions):
            options = options.model_dump(exclude_none=True)
        else:
            options = options or {}
        
        # Ensure ChunkMatches is True by default
        if "ChunkMatches" not in options:
            options["ChunkMatches"] = True
        
        # Prepare request payload
        payload: Dict[str, Any] = {"Q": query}
        if repo_ids is not None:
            payload["RepoIDs"] = repo_ids
        if options:
            payload["Opts"] = normalize_search_options(options)
        
        # Perform request with retries
        for attempt in range(max_retries):
            try:
                session = await self._get_session()
                async with session.post(
                    self.search_url,
                    json=payload,
                    timeout=self.timeout_obj,
                ) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    # Zoekt returns the result in a "Result" field
                    result_data = data.get("Result", data)
                    
                    # Parse and validate the response
                    try:
                        return SearchResult.model_validate(result_data)
                    except ValidationError as e:
                        raise ZoektParseError(f"Failed to parse search response: {e}")
            
            except asyncio.TimeoutError:
                if attempt == max_retries - 1:
                    raise ZoektTimeoutError(f"Request timed out after {self.timeout} seconds")
            
            except aiohttp.ClientConnectionError as e:
                if attempt == max_retries - 1:
                    raise ZoektConnectionError(f"Failed to connect to Zoekt server: {e}")
            
            except aiohttp.ClientResponseError as e:
                if attempt == max_retries - 1:
                    raise ZoektAPIError(e.status, str(e))
            
            # Backoff before retrying
            await asyncio.sleep(retry_backoff * (2 ** attempt))
        
        # This should not be reached due to the exceptions above
        raise ZoektConnectionError("Failed to connect to Zoekt server after retries")
    
    async def list_repositories(
        self,
        query: str = "",
        options: Optional[Union[Dict[str, Any], ListOptions]] = None,
    ) -> RepositoryList:
        """
        List repositories matching the given query asynchronously
        
        Args:
            query: Zoekt repository query (e.g., "repo:abc")
            options: List options (as dict or ListOptions object)
        
        Returns:
            RepositoryList object containing repositories and stats
        
        Raises:
            ZoektConnectionError: Error connecting to the server
            ZoektTimeoutError: Request timed out
            ZoektAPIError: Server returned an error response
            ZoektParseError: Error parsing the server response
        """
        logger.debug(f"Async list repositories query: {query}")
        
        # Convert ListOptions object to dict if needed
        if isinstance(options, ListOptions):
            options = options.model_dump(exclude_none=True)
        
        # Prepare request payload
        payload: Dict[str, Any] = {"Q": query}
        if options is not None:
            payload["Opts"] = options
        
        try:
            session = await self._get_session()
            async with session.post(
                self.list_url,
                json=payload,
                timeout=self.timeout_obj,
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                # Zoekt returns the list in a "List" field
                list_data = data.get("List", data)
                
                # Parse and validate the response
                try:
                    return RepositoryList.model_validate(list_data)
                except ValidationError as e:
                    raise ZoektParseError(f"Failed to parse repository list response: {e}")
            
        except asyncio.TimeoutError:
            raise ZoektTimeoutError(f"Request timed out after {self.timeout} seconds")
        
        except aiohttp.ClientConnectionError as e:
            raise ZoektConnectionError(f"Failed to connect to Zoekt server: {e}")
        
        except aiohttp.ClientResponseError as e:
            raise ZoektAPIError(e.status, str(e))

    async def search_by_language(
        self,
        query: str,
        language: str,
        **kwargs
    ) -> SearchResult:
        """
        Search for code in a specific language asynchronously
        
        Args:
            query: Search query text
            language: Programming language to search
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add or replace the language component
        if "lang" in components:
            components["lang"] = [language]
        else:
            components["lang"] = [language]
        
        full_query = build_query(components)
        return await self.search(full_query, **kwargs)
    
    async def search_by_file_pattern(
        self,
        query: str,
        file_pattern: str,
        **kwargs
    ) -> SearchResult:
        """
        Search for code matching files with the given pattern asynchronously
        
        Args:
            query: Search query text
            file_pattern: File pattern (e.g., "*.py")
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add or append to the file component
        if "file" in components:
            components["file"].append(file_pattern)
        else:
            components["file"] = [file_pattern]
        
        full_query = build_query(components)
        return await self.search(full_query, **kwargs)
    
    async def search_by_repo(
        self,
        query: str,
        repo_pattern: str,
        **kwargs
    ) -> SearchResult:
        """
        Search for code in repositories matching the given pattern asynchronously
        
        Args:
            query: Search query text
            repo_pattern: Repository pattern (e.g., "myorg/*")
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add or append to the repo component
        if "repo" in components:
            components["repo"].append(repo_pattern)
        else:
            components["repo"] = [repo_pattern]
        
        full_query = build_query(components)
        return await self.search(full_query, **kwargs)
    
    async def search_case_sensitive(
        self,
        query: str,
        **kwargs
    ) -> SearchResult:
        """
        Perform a case-sensitive search asynchronously
        
        Args:
            query: Search query text
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Set case sensitivity
        components["case"] = ["yes"]
        
        full_query = build_query(components)
        return await self.search(full_query, **kwargs)
    
    async def search_symbols(
        self,
        query: str,
        symbol_type: Optional[str] = None,
        **kwargs
    ) -> SearchResult:
        """
        Search for symbols matching the query asynchronously
        
        Args:
            query: Search query text
            symbol_type: Optional symbol type filter
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        components = parse_query_components(query)
        
        # Add symbol search modifier
        if symbol_type:
            components["sym"] = [symbol_type]
        else:
            components["sym"] = [""]
        
        full_query = build_query(components)
        return await self.search(full_query, **kwargs)
    
    async def search_with_context(
        self,
        query: str,
        context_lines: int = 5,
        **kwargs
    ) -> SearchResult:
        """
        Search with additional context lines asynchronously
        
        Args:
            query: Search query text
            context_lines: Number of context lines to include
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            SearchResult object
        """
        options = kwargs.get("options", {})
        if isinstance(options, SearchOptions):
            options = options.model_dump(exclude_none=True)
        
        options["NumContextLines"] = context_lines
        kwargs["options"] = options
        
        return await self.search(query, **kwargs)
    
    async def search_batch(
        self,
        queries: List[str],
        **kwargs
    ) -> Dict[str, SearchResult]:
        """
        Perform multiple searches in batch asynchronously
        
        Args:
            queries: List of search queries
            **kwargs: Additional arguments to pass to search()
        
        Returns:
            Dictionary mapping queries to their SearchResult
        """
        tasks = []
        for query in queries:
            task = self.search(query, **kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return dict(zip(queries, results))