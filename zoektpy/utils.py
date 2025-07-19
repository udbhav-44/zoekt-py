"""
Utility functions for the Zoekt client library
"""

import base64
import re
from typing import Any, Dict, List, Optional, Tuple, Union

# Duration fields in SearchOptions that need to be converted to nanoseconds
DURATION_NS_FIELDS = {"MaxWallTime", "FlushWallTime"}


def normalize_search_options(opts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert any duration fields (float seconds) into nanosecond ints.
    E.g. 5.0  → 5_000_000_000
         0.25 →   250_000_000
    """
    normalized: Dict[str, Any] = {}
    for key, val in opts.items():
        if key in DURATION_NS_FIELDS and isinstance(val, (int, float)):
            normalized[key] = int(val * 1e9)
        else:
            normalized[key] = val
    return normalized


def decode_base64(content: str) -> str:
    """Decode base64-encoded content from Zoekt responses"""
    return base64.b64decode(content).decode(errors="replace")


def parse_query_components(query: str) -> Dict[str, List[str]]:
    """
    Parse a Zoekt query string into components (repo, file, lang, case, etc.)
    
    Example:
    "repo:abc file:*.py case:yes text" -> 
        {"repo": ["abc"], "file": ["*.py"], "case": ["yes"], "text": ["text"]}
    """
    components = {}
    
    # Define regex patterns for common query atoms
    atoms = re.finditer(r'(\w+):("(?:[^"\\]|\\.)*"|(?:\S+))', query)
    
    # Extract text content (everything not in a specific atom)
    atom_spans = []
    for match in atoms:
        atom_type = match.group(1)
        atom_value = match.group(2)
        if atom_value.startswith('"') and atom_value.endswith('"'):
            atom_value = atom_value[1:-1]
        
        if atom_type not in components:
            components[atom_type] = []
        components[atom_type].append(atom_value)
        atom_spans.append(match.span())
    
    # Extract remaining text
    if atom_spans:
        last_pos = 0
        text_parts = []
        
        for start, end in sorted(atom_spans):
            if start > last_pos:
                text_part = query[last_pos:start].strip()
                if text_part:
                    text_parts.append(text_part)
            last_pos = end
        
        if last_pos < len(query):
            text_part = query[last_pos:].strip()
            if text_part:
                text_parts.append(text_part)
        
        if text_parts:
            components["text"] = text_parts
    else:
        # No atoms found, entire query is text
        if query.strip():
            components["text"] = [query.strip()]
    
    return components


def build_query(components: Dict[str, List[str]]) -> str:
    """
    Build a Zoekt query string from components
    
    Example:
    {"repo": ["abc"], "file": ["*.py"], "case": ["yes"], "text": ["text"]} ->
        'repo:abc file:*.py case:yes text'
    """
    query_parts = []
    
    # Handle all typed components
    for component_type, values in components.items():
        if component_type == "text":
            continue
        
        for value in values:
            # Quote values with spaces
            if ' ' in value:
                value = f'"{value}"'
            query_parts.append(f"{component_type}:{value}")
    
    # Add text components at the end
    if "text" in components:
        for text in components["text"]:
            query_parts.append(text)
    
    return " ".join(query_parts)