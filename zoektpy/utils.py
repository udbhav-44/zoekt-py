"""
Utility functions for the Zoekt client library
"""

import base64
import re
from typing import Any, Dict, List, Optional, Tuple, Union, Optional
from urllib.parse import quote

# Duration fields in SearchOptions that need to be converted to nanoseconds
DURATION_NS_FIELDS = {"MaxWallTime", "FlushWallTime"}

# Regex pattern to match URLJoinPath templates
URL_JOIN_PATH_TEMPLATE = re.compile(r"^{{\s*URLJoinPath\s+(?P<args>.*?)\s*}}$")

TAB_CHARS = '\t'

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

def evaluate_file_url_template(
    template: str,
    version: str,
    path: str,
    line_fragment_template: Optional[str] = None,
    line_number: Optional[int] = None,
) -> str:
    """
    Evaluate a RepoURLs Zoekt template by substituting version, path, and line number.

    Supports two formats:
    1. URLJoinPath template: "{{ URLJoinPath .Version .Path }}"
    2. Simple replacement: "{{.Version}}" and "{{.Path}}"
    """
    url = ""
    match = URL_JOIN_PATH_TEMPLATE.match(template)

    if match:
        args = match.group("args")
        parts = []
        for arg in args.split():
            if arg == ".Version":
                parts.append("/".join(quote(component, safe="") for component in version.split("/")))
            elif arg == ".Path":
                parts.append("/".join(quote(component, safe="") for component in path.split("/")))
            else:
                # It's a quoted string: https://pkg.go.dev/strconv#Quote.
                parts.append(arg.strip('"'))
        url = "/".join(parts)
    else:
        url = template.replace("{{.Version}}", version).replace("{{.Path}}", path)

    line_fragment = ""
    if line_fragment_template is not None and line_number is not None:
        line_fragment = line_fragment_template.replace("{{.LineNumber}}", str(line_number))

    return url + line_fragment

def evaluate_repo_url_template(template: str) -> str:
    """
    Extract repo URL from RepoURLs template by removing any template syntax

    """

    url = ""
    match = URL_JOIN_PATH_TEMPLATE.match(template)
    if match:
        args = match.group("args")
        url = args.split()[0]
    return url

def adjust_character_offset(line_text: str, source_offset: int, tab_size: int = 4) -> int:
    """
    Adjusts offset from start of text to account for tab character expansion

    :param line_text: The full text of the line.
    :param source_offset: The 0-based character index of the start of the match.
    :param tab_size: The number of spaces a tab expands to (Rich's default is 4).
    :return: The 0-based column index in the rendered tab-expanded form.
    """

    tab_chars_len = tab_size - len(TAB_CHARS)

    return source_offset + tab_chars_len * line_text.count(TAB_CHARS, 0, source_offset)
