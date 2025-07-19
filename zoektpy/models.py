"""
Data models for Zoekt API requests and responses
"""

import base64
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class ListOptionsField(IntEnum):
    FULL = 0
    REPOS_MAP = 2


class Position(BaseModel):
    ByteOffset: int
    LineNumber: int
    Column: int


class Range(BaseModel):
    Start: Position
    End: Position


class SymbolInfo(BaseModel):
    Kind: str
    Parent: Optional[str] = None
    ParentKind: Optional[str] = None


class LineMatch(BaseModel):
    LineNumber: int
    Line: str
    Before: Optional[List[str]] = None
    After: Optional[List[str]] = None
    FileName: bool = False
    
    def get_decoded_line(self) -> str:
        return base64.b64decode(self.Line).decode(errors="replace")
    
    def get_decoded_context(self) -> Dict[str, List[str]]:
        result = {}
        if self.Before:
            result["before"] = [
                base64.b64decode(line).decode(errors="replace") 
                for line in self.Before
            ]
        if self.After:
            result["after"] = [
                base64.b64decode(line).decode(errors="replace") 
                for line in self.After
            ]
        return result


class ChunkMatch(BaseModel):
    Content: str
    ContentStart: Position
    Ranges: List[Range]
    SymbolInfo: Optional[str] = None
    FileName: bool = False
    Score: float
    DebugScore: Optional[str] = None
    BestLineMatch: Optional[int] = None
    
    def get_decoded_content(self) -> str:
        return base64.b64decode(self.Content).decode(errors="replace")




class FileMatch(BaseModel):
    FileName: str
    Repository: str
    Version: str
    Language: Optional[str] = None
    Branches: List[str]
    LineMatches: Optional[List[LineMatch]] = None
    ChunkMatches: Optional[List[ChunkMatch]] = None
    Checksum: str
    Score: float
    Debug: Optional[str] = None


class SearchResult(BaseModel):
    Files: List[FileMatch]
    RepoURLs: Dict[str, str]
    LineFragments: Dict[str, str]
    
    # Stats fields
    ContentBytesLoaded: int
    IndexBytesLoaded: int
    Crashes: int
    Duration: int
    FileCount: int
    ShardFilesConsidered: int
    FilesConsidered: int
    FilesLoaded: int
    FilesSkipped: int
    ShardsScanned: int
    ShardsSkipped: int
    ShardsSkippedFilter: int
    MatchCount: int
    NgramMatches: int
    NgramLookups: int
    Wait: int
    MatchTreeConstruction: int
    MatchTreeSearch: int
    RegexpsConsidered: int
    FlushReason: int


class RepositoryMetadata(BaseModel):
    IndexFormatVersion: int
    IndexFeatureVersion: int
    IndexMinReaderVersion: int
    IndexTime: datetime
    PlainASCII: bool
    LanguageMap: Dict[str, int]
    ZoektVersion: str
    ID: str


class RepositoryStats(BaseModel):
    Repos: int
    Shards: int
    Documents: int
    IndexBytes: int
    ContentBytes: int
    NewLinesCount: int
    DefaultBranchNewLinesCount: int
    OtherBranchesNewLinesCount: int


class Repository(BaseModel):
    TenantID: int
    ID: int
    Name: str
    URL: str
    Metadata: Optional[Dict[str, Any]] = None
    Source: str
    Branches: List[str]
    SubRepoMap: Dict[str, str]
    CommitURLTemplate: str
    FileURLTemplate: str
    LineFragmentTemplate: str
    RawConfig: Optional[str] = None
    Rank: float
    IndexOptions: str
    HasSymbols: bool
    Tombstone: bool
    LatestCommitDate: Optional[datetime] = None


class RepositoryInfo(BaseModel):
    Repository: Repository
    IndexMetadata: RepositoryMetadata
    Stats: RepositoryStats


class RepositoryList(BaseModel):
    Repos: List[RepositoryInfo]
    ReposMap: Dict[str, Any]
    Crashes: int
    Stats: RepositoryStats


class SearchOptions(BaseModel):
    EstimateDocCount: bool = False
    Whole: bool = False
    ShardMaxMatchCount: int = 100
    TotalMaxMatchCount: int = 1000
    ShardRepoMaxMatchCount: int = 10
    MaxWallTime: float = 10.0  # seconds
    FlushWallTime: float = 0.5  # seconds
    MaxDocDisplayCount: int = 20
    NumContextLines: int = 3
    ChunkMatches: bool = True
    UseDocumentRanks: bool = True
    DocumentRanksWeight: float = 0.5
    Trace: bool = False
    DebugScore: bool = False
    MaxMatchCountPerFile: Optional[int] = None
    ComputeRepoStats: bool = False
    ForkLongestMatches: bool = False
    SpanContext: Optional[Dict[str, str]] = None


class ListOptions(BaseModel):
    Field: ListOptionsField = ListOptionsField.FULL