"""
File Upload Validation and Safety Checks
Defensive validation: check file signatures, reject unsafe content, normalize paths.
"""
import os
from typing import Tuple, Optional


# Allowed file types with magic bytes (file signatures)
ALLOWED_TYPES = {
    "application/pdf": {
        "extensions": [".pdf"],
        "signatures": [b"%PDF"],
    },
    "image/png": {
        "extensions": [".png"],
        "signatures": [b"\x89PNG"],
    },
    "image/jpeg": {
        "extensions": [".jpg", ".jpeg"],
        "signatures": [b"\xff\xd8\xff"],
    },
}

# Configuration
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MIN_FILE_SIZE_BYTES = 1  # Reject empty files


class UploadValidationError(Exception):
    """Raised when a file fails validation."""
    pass


def get_file_extension(filename: str) -> str:
    """
    Extract file extension safely.
    Returns lowercase extension with dot (e.g., ".pdf").
    """
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def normalize_filename(filename: str, max_length: int = 255) -> str:
    """
    Normalize filename for safe display.
    - Remove directory separators
    - Bound length
    - Preserve only alphanumeric, dots, hyphens, underscores
    """
    if not filename:
        return "document"
    
    # Remove any directory separators
    filename = os.path.basename(filename)
    
    # Remove null bytes and control characters
    filename = "".join(c for c in filename if ord(c) >= 32 or c in "\t\n")
    
    # Keep only safe characters
    safe_chars = []
    for c in filename:
        if c.isalnum() or c in "._- ":
            safe_chars.append(c)
        elif c == " ":
            safe_chars.append("_")
    
    result = "".join(safe_chars).strip("_")
    if not result:
        result = "document"
    
    # Bound length
    if len(result) > max_length:
        # Keep extension
        _, ext = os.path.splitext(result)
        name = result[:max_length - len(ext)]
        result = name + ext
    
    return result


def detect_mime_type(file_content: bytes) -> Optional[str]:
    """
    Detect MIME type from file signature (magic bytes).
    Never trust browser-supplied MIME type.
    
    Returns:
        Detected MIME type or None if unrecognized.
    """
    for mime_type, info in ALLOWED_TYPES.items():
        for signature in info["signatures"]:
            if file_content.startswith(signature):
                return mime_type
    
    return None


def validate_upload(
    filename: str,
    file_content: bytes,
    browser_mime_type: Optional[str] = None,
) -> Tuple[str, str, str]:
    """
    Validate uploaded file comprehensively.
    
    Returns:
        Tuple of (mime_type, normalized_filename, file_size_str)
    
    Raises:
        UploadValidationError: If validation fails
    """
    # 1. Check file size
    file_size = len(file_content)
    
    if file_size < MIN_FILE_SIZE_BYTES:
        raise UploadValidationError("File is empty")
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise UploadValidationError(
            f"File size {file_size / 1024 / 1024:.1f} MB exceeds maximum "
            f"{MAX_FILE_SIZE_BYTES / 1024 / 1024:.0f} MB"
        )
    
    # 2. Check extension
    extension = get_file_extension(filename)
    if not extension:
        raise UploadValidationError("File has no extension")
    
    # 3. Detect actual MIME type from file signature
    detected_mime = detect_mime_type(file_content)
    if not detected_mime:
        raise UploadValidationError(
            f"File type not supported or file signature unrecognized. "
            f"Extension: {extension}. Allowed: PDF, PNG, JPEG"
        )
    
    # 4. Validate extension matches detected type
    allowed_extensions = ALLOWED_TYPES[detected_mime]["extensions"]
    if extension not in allowed_extensions:
        raise UploadValidationError(
            f"Extension {extension} does not match detected file type {detected_mime}"
        )
    
    # 5. Normalize filename for display
    normalized = normalize_filename(filename)
    
    # 6. Format file size for display
    if file_size < 1024:
        size_str = f"{file_size} B"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / 1024 / 1024:.1f} MB"
    
    return detected_mime, normalized, size_str
