import pytest
import base64

from zoektpy.utils import (
    normalize_search_options,
    decode_base64,
    parse_query_components,
    build_query
)


class TestNormalizeSearchOptions:
    """Test options normalization function"""
    
    def test_normalize_empty_options(self):
        """Test normalizing empty options"""
        options = {}
        normalized = normalize_search_options(options)
        assert normalized == {}
    
    def test_normalize_time_options(self):
        """Test converting time options to nanoseconds"""
        options = {
            "MaxWallTime": 5.0,       # 5 seconds
            "FlushWallTime": 0.5,     # 0.5 seconds
            "NumContextLines": 3      # Not a time option
        }
        
        normalized = normalize_search_options(options)
        
        # Check time conversions
        assert normalized["MaxWallTime"] == 5_000_000_000
        assert normalized["FlushWallTime"] == 500_000_000
        
        # Non-time options remain unchanged
        assert normalized["NumContextLines"] == 3
    
    def test_normalize_with_none_values(self):
        """Test normalization with None values"""
        options = {
            "MaxWallTime": None,
            "NumContextLines": 5
        }
        
        normalized = normalize_search_options(options)
        
        assert "MaxWallTime" in normalized
        assert normalized["MaxWallTime"] is None
        assert normalized["NumContextLines"] == 5


class TestDecodeBase64:
    """Test base64 decoding utility"""
    
    def test_decode_valid_base64(self):
        """Test decoding valid base64"""
        # "Hello World"
        encoded = "SGVsbG8gV29ybGQ="
        decoded = decode_base64(encoded)
        assert decoded == "Hello World"
    
    def test_decode_with_padding(self):
        """Test decoding with different padding"""
        # Test cases with different padding requirements
        cases = [
            ("SGVsbG8=", "Hello"),               # Padding: ==
            ("SGVsbG8gV29ybGQ=", "Hello World"),  # Padding: =
            ("SGVsbG8gV29ybGQh", "Hello World!")  # No padding needed
        ]
        
        for encoded, expected in cases:
            assert decode_base64(encoded) == expected
    
    def test_decode_invalid_base64(self):
        """Test handling invalid base64"""
        invalid = "This is not base64!"
        with pytest.raises(Exception):
            decode_base64(invalid)
    
    def test_decode_empty_string(self):
        """Test decoding empty string"""
        assert decode_base64("") == ""


class TestQueryParsing:
    """Test query parsing functions"""
    
    def test_parse_simple_query(self):
        """Test parsing a simple query"""
        query = "hello world"
        components = parse_query_components(query)
        
        assert "text" in components
        assert components["text"] == ["hello", "world"]
    
    def test_parse_quoted_text(self):
        """Test parsing quoted text"""
        query = '"hello world" function'
        components = parse_query_components(query)
        
        assert "text" in components
        assert "hello world" in components["text"]
        assert "function" in components["text"]
    
    def test_parse_filters(self):
        """Test parsing query filters"""
        query = 'repo:myorg file:*.py lang:python case:yes "search term"'
        components = parse_query_components(query)
        
        assert components["repo"] == ["myorg"]
        assert components["file"] == ["*.py"]
        assert components["lang"] == ["python"]
        assert components["case"] == ["yes"]
        assert components["text"] == ["search term"]
    
    def test_parse_multiple_filters(self):
        """Test parsing multiple filters of the same type"""
        query = 'repo:myorg repo:another file:*.py file:*.js'
        components = parse_query_components(query)
        
        assert components["repo"] == ["myorg", "another"]
        assert components["file"] == ["*.py", "*.js"]
    
    def test_parse_complex_query(self):
        """Test parsing a complex query"""
        query = 'repo:myorg -repo:test file:*.py "error handling" lang:python'
        components = parse_query_components(query)
        
        assert components["repo"] == ["myorg", "-test"]
        assert components["file"] == ["*.py"]
        assert components["lang"] == ["python"]
        assert components["text"] == ["error handling"]


class TestQueryBuilding:
    """Test query building functions"""
    
    def test_build_simple_query(self):
        """Test building a simple query"""
        components = {
            "text": ["hello", "world"]
        }
        
        query = build_query(components)
        assert "hello" in query
        assert "world" in query
    
    def test_build_with_filters(self):
        """Test building query with filters"""
        components = {
            "repo": ["myorg"],
            "file": ["*.py"],
            "lang": ["python"],
            "text": ["function"]
        }
        
        query = build_query(components)
        
        assert "repo:myorg" in query
        assert "file:*.py" in query
        assert "lang:python" in query
        assert "function" in query
    
    def test_build_with_spaces(self):
        """Test building with values containing spaces"""
        components = {
            "repo": ["my org/repo"],
            "text": ["hello world"]
        }
        
        query = build_query(components)
        
        # Check that values with spaces are quoted
        assert 'repo:"my org/repo"' in query
        assert "hello world" in query
    
    def test_build_with_negation(self):
        """Test building with negated filters"""
        components = {
            "repo": ["myorg", "-test"],
            "text": ["function"]
        }
        
        query = build_query(components)
        
        assert "repo:myorg" in query
        assert "-repo:test" in query
        assert "function" in query
    
    def test_build_complex_query(self):
        """Test building a complex query"""
        components = {
            "repo": ["myorg/repo"],
            "file": ["*.py", "*.js"],
            "lang": ["python"],
            "case": ["yes"],
            "text": ["error handling", "try except"]
        }
        
        query = build_query(components)
        
        assert "repo:myorg/repo" in query
        assert "file:*.py" in query
        assert "file:*.js" in query
        assert "lang:python" in query
        assert "case:yes" in query
        assert "error handling" in query
        assert "try except" in query