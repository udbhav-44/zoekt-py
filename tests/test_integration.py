import pytest
import responses
import json
from typing import Dict, Any

from zoektpy import ZoektClient, AsyncZoektClient
from zoektpy.exceptions import ZoektAPIError


@pytest.fixture
def mock_zoekt_server():
    """Set up mock responses for Zoekt server"""
    with responses.RequestsMock() as rsps:
        # Prepare search response
        search_response = {
            "Files": [
                {
                    "FileName": "main.py",
                    "Repository": "test/repo",
                    "Language": "Python",
                    "ChunkMatches": [
                        {
                            "Content": "ZGVmIG1haW4oKToKICAgIHByaW50KCJIZWxsbyIpCg==",
                            "ContentStart": {"ByteOffset": 0, "LineNumber": 1, "Column": 1},
                            "Ranges": [
                                {
                                    "Start": {"ByteOffset": 4, "LineNumber": 1, "Column": 5},
                                    "End": {"ByteOffset": 8, "LineNumber": 1, "Column": 9}
                                }
                            ],
                            "Score": 1.0
                        }
                    ],
                    "Branches": ["main"],
                    "Score": 0.8
                }
            ],
            "RepoURLs": {},
            "LineFragments": {},
            "FileCount": 1,
            "MatchCount": 1,
            "ContentBytesLoaded": 100,
            "IndexBytesLoaded": 50,
            "Duration": 5000000,
            "FilesConsidered": 10,
            "ShardFilesConsidered": 10,
            "FilesLoaded": 1,
            "FilesSkipped": 0,
            "ShardsScanned": 1,
            "ShardsSkipped": 0,
            "ShardsSkippedFilter": 0,
            "NgramMatches": 1,
            "NgramLookups": 10,
            "Crashes": 0,
            "Wait": 0,
            "MatchTreeConstruction": 1000000,
            "MatchTreeSearch": 4000000,
            "RegexpsConsidered": 0,
            "FlushReason": 0
        }
        
        # Add search endpoint
        def search_callback(request):
            payload = json.loads(request.body)
            query = payload.get("Q", "")
            
            # Return error for invalid query
            if "invalid" in query:
                return (400, {}, json.dumps({"Error": "Invalid query"}))
            
            # Return empty results for non-matching query
            if "nonexistent" in query:
                result = search_response.copy()
                result["Files"] = []
                result["FileCount"] = 0
                result["MatchCount"] = 0
                return (200, {}, json.dumps({"Result": result}))
            
            # Return modified results for specific language
            if "lang:java" in query:
                result = search_response.copy()
                result["Files"][0]["Language"] = "Java"
                result["Files"][0]["FileName"] = "Main.java"
                return (200, {}, json.dumps({"Result": result}))
            
            # Return normal results otherwise
            return (200, {}, json.dumps({"Result": search_response}))
        
        rsps.add_callback(
            responses.POST,
            "http://localhost:6070/api/search",
            callback=search_callback,
            content_type="application/json",
        )
        
        # Prepare list response
        list_response = {
            "Repos": [
                {
                    "Repository": {
                        "ID": 1,
                        "Name": "test/repo",
                        "URL": "https://github.com/test/repo",
                        "Branches": ["main"],
                        "SubRepoMap": {},
                        "HasSymbols": True,
                        "Enabled": True,
                        "IndexOptions": {}
                    },
                    "Stats": {
                        "Repos": 1,
                        "Documents": 10,
                        "IndexBytes": 1000,
                        "ContentBytes": 5000,
                        "NewLinesCount": 200,
                        "Languages": {"Python": 10}
                    }
                }
            ]
        }
        
        # Add list endpoint
        def list_callback(request):
            payload = json.loads(request.body)
            query = payload.get("Q", "")
            
            # Return filtered results for specific query
            if "repo:java" in query:
                result = list_response.copy()
                result["Repos"][0]["Repository"]["Name"] = "java/repo"
                result["Repos"][0]["Stats"]["Languages"] = {"Java": 15}
                return (200, {}, json.dumps({"List": result}))
            
            # Return empty results for non-matching query
            if "repo:nonexistent" in query:
                result = list_response.copy()
                result["Repos"] = []
                return (200, {}, json.dumps({"List": result}))
            
            # Return normal results otherwise
            return (200, {}, json.dumps({"List": list_response}))
        
        rsps.add_callback(
            responses.POST,
            "http://localhost:6070/api/list",
            callback=list_callback,
            content_type="application/json",
        )
        
        yield rsps


class TestZoektClientIntegration:
    """Integration tests for ZoektClient"""
    
    def test_search_flow(self, mock_zoekt_server):
        """Test complete search flow"""
        client = ZoektClient()
        
        # Search for valid query
        result = client.search("main")
        assert result.MatchCount == 1
        assert result.Files[0].FileName == "main.py"
        
        # Get content from chunks
        chunk = result.Files[0].ChunkMatches[0]
        content = chunk.get_decoded_content()
        assert "def main():" in content
        assert "print" in content
        
        # Search for different language
        java_result = client.search("main lang:java")
        assert java_result.Files[0].Language == "Java"
        assert java_result.Files[0].FileName == "Main.java"
        
        # Search with no results
        empty_result = client.search("nonexistent")
        assert empty_result.MatchCount == 0
        assert len(empty_result.Files) == 0
        
        # Search with invalid query
        with pytest.raises(ZoektAPIError) as excinfo:
            client.search("invalid query")
        assert excinfo.value.status_code == 400
    
    def test_list_repositories_flow(self, mock_zoekt_server):
        """Test complete repository listing flow"""
        client = ZoektClient()
        
        # List all repositories
        repos = client.list_repositories()
        assert len(repos.Repos) == 1
        assert repos.Repos[0].Repository.Name == "test/repo"
        assert "Python" in repos.Repos[0].Stats.Languages
        
        # List Java repositories
        java_repos = client.list_repositories("repo:java")
        assert java_repos.Repos[0].Repository.Name == "java/repo"
        assert "Java" in java_repos.Repos[0].Stats.Languages
        
        # List non-existent repositories
        empty_repos = client.list_repositories("repo:nonexistent")
        assert len(empty_repos.Repos) == 0
    
    def test_specialized_search_methods(self, mock_zoekt_server):
        """Test specialized search methods"""
        client = ZoektClient()
        
        # Test language search
        lang_result = client.search_by_language("main", "java")
        assert lang_result.Files[0].Language == "Java"
        
        # Test file pattern search
        client.search_by_file_pattern("main", "*.py")
        
        # Test case-sensitive search
        client.search_case_sensitive("Main")
        
        # Test symbol search
        client.search_symbols("main")
        
        # Test search with context
        client.search_with_context("main", context_lines=10)
        
        # Test batch search
        batch_results = client.search_batch(["main", "nonexistent"])
        assert batch_results["main"].MatchCount == 1
        assert batch_results["nonexistent"].MatchCount == 0


@pytest.mark.asyncio
class TestAsyncZoektClientIntegration:
    """Integration tests for AsyncZoektClient"""
    
    async def test_async_search_flow(self, mock_zoekt_server):
        """Test complete async search flow"""
        client = AsyncZoektClient()
        
        try:
            # Search for valid query
            result = await client.search("main")
            assert result.MatchCount == 1
            assert result.Files[0].FileName == "main.py"
            
            # Search for different language
            java_result = await client.search("main lang:java")
            assert java_result.Files[0].Language == "Java"
            
            # Search with no results
            empty_result = await client.search("nonexistent")
            assert empty_result.MatchCount == 0
            
            # Search with invalid query
            with pytest.raises(ZoektAPIError):
                await client.search("invalid query")
                
        finally:
            await client.close()
    
    async def test_async_specialized_search_methods(self, mock_zoekt_server):
        """Test async specialized search methods"""
        client = AsyncZoektClient()
        
        try:
            # Test language search
            lang_result = await client.search_by_language("main", "java")
            assert lang_result.Files[0].Language == "Java"
            
            # Test batch search
            batch_results = await client.search_batch(["main", "nonexistent"])
            assert batch_results["main"].MatchCount == 1
            assert batch_results["nonexistent"].MatchCount == 0
            
        finally:
            await client.close()