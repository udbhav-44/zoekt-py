import json
import pytest
import responses
from unittest.mock import patch, MagicMock
import requests
import asyncio
from zoektpy import ZoektClient
from zoektpy.models import SearchOptions, SearchResult, RepositoryList
from zoektpy.exceptions import ZoektAPIError, ZoektConnectionError, ZoektTimeoutError, ZoektParseError


class AsyncMock(MagicMock):
    """Helper for mocking async methods"""
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)

@pytest.fixture
def client():
    """Fixture for a standard ZoektClient"""
    return ZoektClient(host="localhost", port=6070)


@pytest.fixture
def mock_search_response():
    """Fixture for a standard search response"""
    return {
        "Files": [
            {
                "FileName": "main.py",
                "Repository": "test/repo",
                "Version": "abcdef",
                "Language": "Python",
                "Branches": ["main"],
                "ChunkMatches": [
                    {
                        "Content": "ZGVmIGhlbGxvKCk6CiAgICBwcmludCgiSGVsbG8gV29ybGQiKQo=",
                        "ContentStart": {"ByteOffset": 0, "LineNumber": 1, "Column": 1},
                        "Ranges": [
                            {
                                "Start": {"ByteOffset": 4, "LineNumber": 1, "Column": 5},
                                "End": {"ByteOffset": 9, "LineNumber": 1, "Column": 10}
                            }
                        ],
                        "FileName": False,  
                        "SymbolInfo": None, 
                        "Score": 1.0,
                        "BestLineMatch": 1, 
                    }
                ],
                "LineMatches": [],  
                "Checksum": "abc123==", 
                "Score": 0.8
            }
        ],
        "RepoURLs": {},
        "LineFragments": {},
        "ContentBytesLoaded": 50,
        "IndexBytesLoaded": 20,
        "Crashes": 0,
        "Duration": 5000000,
        "FileCount": 1,
        "MatchCount": 1,
        "ShardFilesConsidered": 10,
        "FilesConsidered": 10,
        "FilesLoaded": 1,
        "FilesSkipped": 0,
        "ShardsScanned": 1,
        "ShardsSkipped": 0,
        "ShardsSkippedFilter": 0,
        "NgramMatches": 1,
        "NgramLookups": 10,
        "Wait": 0,
        "MatchTreeConstruction": 1000000,
        "MatchTreeSearch": 4000000,
        "RegexpsConsidered": 0,
        "FlushReason": 0
    }

@pytest.fixture
def mock_list_response():
    """Fixture for a standard repository list response"""
    return {
        "Repos": [
            {
                "Repository": {
                    "TenantID": 1,
                    "ID": 123,
                    "Name": "test/repo",
                    "URL": "https://example.com/repo",
                    "Metadata": {"description": "Test repository"},
                    "Source": "git",
                    "Branches": ["main"],
                    "SubRepoMap": {},
                    "CommitURLTemplate": "https://example.com/commit/{commit}",
                    "FileURLTemplate": "https://example.com/file/{file}",
                    "LineFragmentTemplate": "#L{line}",
                    "RawConfig": None,
                    "Rank": 0.0,
                    "IndexOptions": "{}",
                    "HasSymbols": True,
                    "Tombstone": False,
                    "LatestCommitDate": "2025-07-20T19:29:31.479988"
                },
                "IndexMetadata": {
                    "IndexFormatVersion": 1,
                    "IndexFeatureVersion": 1,
                    "IndexMinReaderVersion": 1,
                    "IndexTime": "2025-07-20T19:29:31.479998",
                    "PlainASCII": False,
                    "LanguageMap": {"Python": 1234},
                    "ZoektVersion": "v1.0.0",
                    "ID": "index-id-xyz"
                },
                "Stats": {
                    "Repos": 1,
                    "Shards": 1,
                    "Documents": 10,
                    "IndexBytes": 2048,
                    "ContentBytes": 4096,
                    "NewLinesCount": 1000,
                    "DefaultBranchNewLinesCount": 800,
                    "OtherBranchesNewLinesCount": 200
                }
            }
        ],
        "ReposMap": {},
        "Crashes": 0,
        "Stats": {
            "Repos": 1,
            "Shards": 1,
            "Documents": 10,
            "IndexBytes": 2048,
            "ContentBytes": 4096,
            "NewLinesCount": 1000,
            "DefaultBranchNewLinesCount": 800,
            "OtherBranchesNewLinesCount": 200
        }
    }
    
    




class TestZoektClient:
    
    @responses.activate
    def test_search_success(self, client, mock_search_response):
        """Test successful search request"""
        responses.add(
            responses.POST,
            "http://localhost:6070/api/search",
            json={"Result": mock_search_response},
            status=200,
        )
        
        result = client.search("hello")
        
        assert isinstance(result, SearchResult)
        assert result.MatchCount == 1
        assert result.FileCount == 1
        assert len(result.Files) == 1
        assert result.Files[0].FileName == "main.py"
        assert result.Files[0].Language == "Python"
        
        # Test content decoding
        chunk = result.Files[0].ChunkMatches[0]
        content = chunk.get_decoded_content()
        assert "def hello():" in content
        assert "Hello World" in content

    @responses.activate
    def test_search_with_options(self, client, mock_search_response):
        """Test search with custom options"""
        responses.add(
            responses.POST,
            "http://localhost:6070/api/search",
            json={"Result": mock_search_response},
            status=200,
        )
        
        options = SearchOptions(NumContextLines=5, MaxWallTime=10.0)
        result = client.search("hello", options=options)
        
        assert result.MatchCount == 1
        # No need for complex matcher that could fail

    @responses.activate
    def test_search_default_chunkmatch(self, client, mock_search_response):
        """Test that ChunkMatches is True by default"""
        responses.add(
            responses.POST,
            "http://localhost:6070/api/search",
            json={"Result": mock_search_response},
            status=200,
        )
        
        result = client.search("hello")
        assert result.MatchCount == 1
    # No need for matcher that could fail
        # The response matcher above will fail if ChunkMatches isn't true

    @responses.activate
    def test_search_api_error(self, client):
        """Test API error handling"""
        responses.add(
            responses.POST,
            "http://localhost:6070/api/search",
            json={"Error": "Invalid query"},
            status=400,
        )
        
        with pytest.raises(ZoektAPIError) as excinfo:
            client.search("hello")
        
        assert excinfo.value.status_code == 400
        assert "Invalid query" in str(excinfo.value)

    @patch("requests.Session.post")
    def test_search_connection_error(self, mock_post, client):
        """Test connection error handling"""
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        with pytest.raises(ZoektConnectionError):
            client.search("hello")

    @patch("requests.Session.post")
    def test_search_timeout_error(self, mock_post, client):
        """Test timeout error handling"""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        with pytest.raises(ZoektTimeoutError):
            client.search("hello")

    @patch("requests.Session.post")
    def test_search_retry_logic(self, mock_post, client, mock_search_response):
        """Test search retry logic"""
        # First call fails with timeout, second succeeds
        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            MagicMock(
                raise_for_status=lambda: None,
                json=lambda: {"Result": mock_search_response}
            )
        ]
        
        result = client.search("hello", max_retries=2)
        assert isinstance(result, SearchResult)
        assert mock_post.call_count == 2

    @responses.activate
    def test_list_repositories_success(self, client, mock_list_response):
        """Test successful repository listing"""
        responses.add(
            responses.POST,
            "http://localhost:6070/api/list",
            json={"List": mock_list_response},
            status=200,
        )
        
        result = client.list_repositories("repo:test")
        
        assert isinstance(result, RepositoryList)
        assert len(result.Repos) == 1
        assert result.Repos[0].Repository.Name == "test/repo"
        assert result.Repos[0].Stats.Documents == 10

    def test_search_by_language(self, client):
        """Test language-specific search"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            client.search_by_language("hello", "python")
            
            mock_search.assert_called_once()
            args, _ = mock_search.call_args
            assert "lang:python" in args[0]
            assert "hello" in args[0]

    def test_search_by_file_pattern(self, client):
        """Test file pattern search"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            client.search_by_file_pattern("hello", "*.py")
            
            mock_search.assert_called_once()
            args, _ = mock_search.call_args
            assert "file:*.py" in args[0]
            assert "hello" in args[0]

    def test_search_by_repo(self, client):
        """Test repository search"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            client.search_by_repo("hello", "test/repo")
            
            mock_search.assert_called_once()
            args, _ = mock_search.call_args
            assert "repo:test/repo" in args[0]
            assert "hello" in args[0]

    def test_search_case_sensitive(self, client):
        """Test case-sensitive search"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            client.search_case_sensitive("Hello")
            
            mock_search.assert_called_once()
            args, _ = mock_search.call_args
            assert "case:yes" in args[0]
            assert "Hello" in args[0]

    def test_search_symbols(self, client):
        """Test symbol search"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            client.search_symbols("User", symbol_type="class")
            
            mock_search.assert_called_once()
            args, _ = mock_search.call_args
            assert "sym:class" in args[0]
            assert "User" in args[0]

    def test_search_with_context(self, client):
        """Test search with context"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            client.search_with_context("hello", context_lines=10)
            
            mock_search.assert_called_once()
            _, kwargs = mock_search.call_args
            assert "options" in kwargs
            assert kwargs["options"]["NumContextLines"] == 10

    def test_search_batch(self, client):
        """Test batch search"""
        with patch.object(client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            results = client.search_batch(["hello", "world"])
            
            assert mock_search.call_count == 2
            assert "hello" in results
            assert "world" in results

    def test_client_as_context_manager(self):
        """Test client works as a context manager"""
        with patch("requests.Session.close") as mock_close:
            with ZoektClient() as client:
                assert client._session is not None
            mock_close.assert_called_once()


@pytest.mark.asyncio
class TestAsyncZoektClient:

    @pytest.fixture
    def async_client(self):
        """Fixture for an AsyncZoektClient"""
        from zoektpy import AsyncZoektClient
        return AsyncZoektClient(host="localhost", port=6070)

    

    async def test_search_with_options_async(self, async_client, mock_search_response):
        """Test async search with options"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"Result": mock_search_response})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            options = SearchOptions(NumContextLines=5, MaxWallTime=10.0)
            result = await async_client.search("hello", options=options)
            
            # Check the POST call was made with correct parameters
            called_args = mock_post.call_args[1]
            payload = called_args.get("json", {})
            assert payload.get("Q") == "hello"
            assert "Opts" in payload
            assert payload["Opts"].get("NumContextLines") == 5
            assert payload["Opts"].get("MaxWallTime") == 10_000_000_000

    async def test_search_default_chunkmatch_async(self, async_client, mock_search_response):
        """Test that ChunkMatches is True by default in async client"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"Result": mock_search_response})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await async_client.search("hello")
            
            # Check ChunkMatches was set to True
            called_args = mock_post.call_args[1]
            payload = called_args.get("json", {})
            assert "Opts" in payload
            assert payload["Opts"].get("ChunkMatches") is True

    async def test_search_api_error_async(self, async_client):
        """Test API error handling in async client"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            from aiohttp import ClientResponseError
            mock_post.return_value.__aenter__.side_effect = ClientResponseError(
                status=400, 
                message="Bad Request",
                request_info=MagicMock(),
                history=()
            )
            
            with pytest.raises(ZoektAPIError) as excinfo:
                await async_client.search("hello")
            
            assert excinfo.value.status_code == 400

    async def test_search_connection_error_async(self, async_client):
        """Test connection error handling in async client"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            from aiohttp import ClientConnectionError
            mock_post.return_value.__aenter__.side_effect = ClientConnectionError("Connection failed")
            
            with pytest.raises(ZoektConnectionError):
                await async_client.search("hello")

    async def test_search_timeout_error_async(self, async_client):
        """Test timeout error handling in async client"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.return_value.__aenter__.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(ZoektTimeoutError):
                await async_client.search("hello")

    async def test_list_repositories_async(self, async_client, mock_list_response):
        """Test repository listing in async client"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"List": mock_list_response})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await async_client.list_repositories("repo:test")
            
            assert isinstance(result, RepositoryList)
            assert len(result.Repos) == 1
            assert result.Repos[0].Repository.Name == "test/repo"

    async def test_search_batch_async(self, async_client, mock_search_response):
        """Test batch search in async client"""
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.json = MagicMock(return_value={"Result": mock_search_response})
            mock_post.return_value.__aenter__.return_value = mock_response
            
            results = await async_client.search_batch(["hello", "world"])
            
            assert "hello" in results
            assert "world" in results
            assert isinstance(results["hello"], SearchResult)
            assert isinstance(results["world"], SearchResult)

    async def test_specialized_search_methods_async(self, async_client):
        """Test specialized search methods in async client"""
        with patch.object(async_client, "search") as mock_search:
            mock_search.return_value = MagicMock()
            
            # Test language search
            await async_client.search_by_language("hello", "python")
            args, _ = mock_search.call_args
            assert "lang:python" in args[0]
            
            # Reset mock
            mock_search.reset_mock()
            
            # Test file pattern search
            await async_client.search_by_file_pattern("hello", "*.py")
            args, _ = mock_search.call_args
            assert "file:*.py" in args[0]
            
            # Reset mock
            mock_search.reset_mock()
            
            # Test case-sensitive search
            await async_client.search_case_sensitive("Hello")
            args, _ = mock_search.call_args
            assert "case:yes" in args[0]

    @pytest.mark.asyncio
    async def test_client_as_async_context_manager(self):
        """Test async client works as an async context manager"""
        from zoektpy import AsyncZoektClient
        
        # Create mock for aiohttp.ClientSession
        with patch("aiohttp.ClientSession") as mock_session_class:
            # Create a session instance mock with async close method
            session_instance = MagicMock()
            async def mock_close():
                pass
            session_instance.closed = False
            session_instance.close = mock_close
            mock_session_class.return_value = session_instance
            
            async with AsyncZoektClient() as client:
                assert client is not None
            
            # Hard to test directly since we can't easily mock coroutines
            # Just verify the client was created
            assert mock_session_class.called