"""
Data models for Zoekt API requests and responses
"""

import base64
from datetime import datetime
from enum import IntEnum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


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
    Kind: Optional[str] = None
    Parent: Optional[str] = None
    ParentKind: Optional[str] = None
    Scope: Optional[str] = None


class LineMatch(BaseModel):
    LineNumber: int
    Line: str
    Before: Optional[List[str]] = []
    After: Optional[List[str]] = []
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
    SymbolInfo: Optional["SymbolInfo"] = None
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
    LineMatches: Optional[List[LineMatch]] = []
    ChunkMatches: Optional[List[ChunkMatch]] = []
    Checksum: str
    Score: float
    Debug: Optional[str] = None


class SearchResult(BaseModel):
    Files: List["FileMatch"] = []
    RepoURLs: Dict[str, str] = Field(default_factory=dict)
    LineFragments: Dict[str, str] = Field(default_factory=dict)

    # Stats fields
    ContentBytesLoaded: int = 0
    IndexBytesLoaded: int = 0 
    Crashes: int =  0
    Duration: int = 0
    FileCount: int = 0
    ShardFilesConsidered: int = 0
    FilesConsidered: int = 0 
    FilesLoaded: int = 0
    FilesSkipped: int = 0
    ShardsScanned: int = 0
    ShardsSkipped: int = 0
    ShardsSkippedFilter: int = 0
    MatchCount: int = 0
    NgramMatches: int = 0
    NgramLookups: int = 0
    Wait: int = 0
    MatchTreeConstruction: int = 0
    MatchTreeSearch: int = 0
    RegexpsConsidered: int = 0
    FlushReason: int = 0
    
 


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

class Branch(BaseModel):
    Name: str
    Version: str

class Repository(BaseModel):
    TenantID: int
    ID: int
    Name: str
    URL: str
    Metadata: Optional[Dict[str, Any]] = None
    Source: str
    Branches: List[Branch]
    SubRepoMap: Optional[Dict[str, 'Repository']]
    CommitURLTemplate: str
    FileURLTemplate: str
    LineFragmentTemplate: str
    RawConfig: Optional[Dict[str, Any]] = None
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