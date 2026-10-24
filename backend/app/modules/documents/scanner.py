"""
Malware Scanner Provider Interface and Implementations
Handles file scanning with clear state transitions and honest unavailable/bypass behaviors.
"""
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime, timezone


class ScanResult:
    """Result of a malware scan operation."""
    
    def __init__(
        self,
        status: str,  # CLEAN, INFECTED, SCAN_UNAVAILABLE, SCAN_BYPASSED_DEVELOPMENT, PROCESSING_FAILED
        provider: str,
        result_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        self.status = status
        self.provider = provider
        self.result_data = result_data or {}
        self.error_message = error_message
        self.timestamp = datetime.now(timezone.utc)
    
    def to_json(self) -> str:
        """Serialize result to JSON."""
        return json.dumps({
            "status": self.status,
            "provider": self.provider,
            "result_data": self.result_data,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        })


class ScannerProvider(ABC):
    """
    Abstract interface for file scanning.
    Implementations must return honest results: do not fake CLEAN status.
    """
    
    @abstractmethod
    def scan_bytes(self, file_content: bytes, filename: str) -> ScanResult:
        """
        Scan file content and return the result.
        
        Args:
            file_content: File bytes to scan
            filename: Original filename (for logging/context)
        
        Returns:
            ScanResult with status and metadata
        """
        pass


class DisabledScannerProvider(ScannerProvider):
    """
    Default disabled scanner. Returns SCAN_UNAVAILABLE for all scans.
    Production configuration must fail closed if scanning is required.
    """
    
    def scan_bytes(self, file_content: bytes, filename: str) -> ScanResult:
        """Return unavailable status."""
        return ScanResult(
            status="SCAN_UNAVAILABLE",
            provider="disabled",
            error_message="No scanner configured; scanning unavailable",
        )


class DemoScannerProvider(ScannerProvider):
    """
    Demo/synthetic scanner for testing. Does NOT scan real content.
    
    Rules for demo:
    - Files with "infected" in name → INFECTED
    - Files < 100 bytes → CLEAN (assuming test files)
    - Empty files → rejected upstream (not reached here)
    - Everything else → CLEAN
    
    This is explicitly a DEMO provider. Production must use real scanner.
    """
    
    def scan_bytes(self, file_content: bytes, filename: str) -> ScanResult:
        """Synthetic scanning based on filename patterns."""
        
        # Demo rule 1: filename contains "infected"
        if "infected" in filename.lower():
            return ScanResult(
                status="INFECTED",
                provider="demo",
                result_data={
                    "threat": "EICAR-STANDARD-ANTIVIRUS-TEST-FILE!",
                    "note": "Demo provider detected test pattern in filename",
                },
            )
        
        # Demo rule 2: very small files are assumed clean (test files)
        if len(file_content) < 100:
            return ScanResult(
                status="CLEAN",
                provider="demo",
                result_data={"note": "Demo provider: small test file assumed clean"},
            )
        
        # Demo rule 3: everything else is clean (demo assumption)
        return ScanResult(
            status="CLEAN",
            provider="demo",
            result_data={"note": "Demo provider: file passed basic checks"},
        )


class DevelopmentBypassScannerProvider(ScannerProvider):
    """
    DEVELOPMENT-ONLY bypass. Files marked as SCAN_BYPASSED_DEVELOPMENT.
    This must only be used in explicit development mode and never in production.
    """
    
    def scan_bytes(self, file_content: bytes, filename: str) -> ScanResult:
        """Bypass scan and mark as development bypass."""
        return ScanResult(
            status="SCAN_BYPASSED_DEVELOPMENT",
            provider="development_bypass",
            result_data={
                "warning": "This file has NOT been scanned. Development mode only.",
                "filename": filename,
                "file_size": len(file_content),
            },
        )


# Global scanner provider instance
_scanner_provider: Optional[ScannerProvider] = None


def get_scanner_provider() -> ScannerProvider:
    """
    Get or initialize the global scanner provider instance.
    Defaults to DisabledScannerProvider if not explicitly set.
    """
    global _scanner_provider
    if _scanner_provider is None:
        _scanner_provider = DisabledScannerProvider()
    return _scanner_provider


def set_scanner_provider(provider: ScannerProvider) -> None:
    """
    Set the global scanner provider.
    Used for testing or to configure a different scanner.
    """
    global _scanner_provider
    _scanner_provider = provider
