"""
Exceptions for the Zoekt client library
"""

class ZoektError(Exception):
    """Base exception for all Zoekt client errors"""
    pass


class ZoektConnectionError(ZoektError):
    """Error connecting to Zoekt server"""
    pass


class ZoektTimeoutError(ZoektError):
    """Zoekt server request timed out"""
    pass


class ZoektAPIError(ZoektError):
    """API error returned by Zoekt server"""
    
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Zoekt API error ({status_code}): {message}")


class ZoektParseError(ZoektError):
    """Error parsing Zoekt response"""
    pass