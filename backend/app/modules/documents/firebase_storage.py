"""
Firebase Cloud Storage Provider for SakshyaTrail Document Storage.

Server-side only. Uses firebase-admin SDK with service-account credentials
or Application Default Credentials (ADC).

Security design:
- All storage access is privileged / server-side; the browser never receives
  bucket credentials, service-account tokens, or direct object paths.
- Signed URLs are generated only after backend authorization and carry a short
  expiry (≤ 15 minutes by default). They must never be logged or cached.
- SHA-256 integrity is verified on every download against the digest stored in
  the relational database.
- Firebase Storage rules must deny all browser / end-user access; the backend
  uses the Admin SDK which bypasses end-user rules, but we still enforce our
  own application RBAC before every operation.

Do NOT call this module from the frontend or expose its methods via a public
API without first performing authorization in the FastAPI route layer.
"""
import datetime
import hashlib
import io
import logging
from typing import Any, Dict, Optional

from app.modules.documents.storage import StorageProvider, StorageException

logger = logging.getLogger(__name__)

# Namespace prefix inside the GCS bucket so objects are isolated from any
# other services that might share the same bucket.
_BUCKET_PREFIX = "sakshyatrail"


class FirebaseStorageProvider(StorageProvider):
    """
    Google Cloud / Firebase Storage backend using the firebase-admin SDK.

    All operations are server-side only; bucket credentials are never sent to
    the browser. Signed URLs are generated after authorization and carry a
    default 15-minute expiry.

    Initialisation order (idempotent – safe to call multiple times):
    1. If GOOGLE_APPLICATION_CREDENTIALS is set, load that service-account JSON.
    2. Otherwise fall back to Application Default Credentials (ADC), which works
       on GCP/Firebase Hosting without any extra file.
    """

    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """
        Args:
            bucket_name: The GCS/Firebase bucket name (e.g. sih-26265-fdr.firebasestorage.app).
            credentials_path: Absolute or relative path to a service-account JSON file.
                              If None, ADC is attempted.
        """
        try:
            import firebase_admin
            from firebase_admin import credentials as fb_credentials, storage as fb_storage
        except ImportError as exc:
            raise StorageException(
                "firebase-admin is not installed. "
                "Run: pip install firebase-admin"
            ) from exc

        try:
            if not firebase_admin._apps:
                # Resolution priority for cloud / container environments:
                raw_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT_JSON")
                raw_b64 = os.environ.get("FIREBASE_SERVICE_ACCOUNT_BASE64")

                if raw_json:
                    import json
                    cred = fb_credentials.Certificate(json.loads(raw_json))
                    logger.info("[Firebase] Initialised with FIREBASE_SERVICE_ACCOUNT_JSON env var.")
                elif raw_b64:
                    import json, base64
                    decoded = base64.b64decode(raw_b64).decode("utf-8")
                    cred = fb_credentials.Certificate(json.loads(decoded))
                    logger.info("[Firebase] Initialised with FIREBASE_SERVICE_ACCOUNT_BASE64 env var.")
                elif credentials_path and os.path.exists(credentials_path):
                    cred = fb_credentials.Certificate(credentials_path)
                    logger.info("[Firebase] Initialised with service-account credentials file: %s", credentials_path)
                elif os.path.exists("/etc/secrets/serviceAccountKey.json"):
                    cred = fb_credentials.Certificate("/etc/secrets/serviceAccountKey.json")
                    logger.info("[Firebase] Initialised with Render secret file (/etc/secrets/serviceAccountKey.json).")
                else:
                    try:
                        cred = fb_credentials.ApplicationDefault()
                        logger.info("[Firebase] Initialised with Application Default Credentials.")
                    except Exception as adc_err:
                        raise StorageException(
                            "No valid Firebase credentials found. Provide FIREBASE_SERVICE_ACCOUNT_JSON env, "
                            "a secret file at /etc/secrets/serviceAccountKey.json, or configure local storage."
                        ) from adc_err

                firebase_admin.initialize_app(cred, {"storageBucket": bucket_name})
            else:
                logger.info("[Firebase] Re-using existing firebase-admin app.")

            self._bucket = fb_storage.bucket()
            self._bucket_name = bucket_name
        except Exception as exc:
            raise StorageException(
                f"Firebase Storage initialisation failed: {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _blob_path(self, storage_key: str) -> str:
        """Return the full object path within the bucket."""
        # Reject traversal attempts
        if ".." in storage_key or storage_key.startswith("/"):
            raise StorageException(f"Invalid storage key: {storage_key!r}")
        return f"{_BUCKET_PREFIX}/{storage_key}"

    def _blob(self, storage_key: str):
        """Return a Blob object for the given storage key."""
        return self._bucket.blob(self._blob_path(storage_key))

    # ------------------------------------------------------------------
    # StorageProvider interface
    # ------------------------------------------------------------------

    def save_file(self, content: bytes, original_filename: str) -> str:
        """
        Upload bytes to Firebase Storage.

        Generates a server-side UUID storage key; never trusts the caller-
        supplied filename as the destination path.

        Returns:
            storage_key – an opaque UUID string. Persist this in the DB.
        """
        import uuid
        storage_key = str(uuid.uuid4())

        try:
            blob = self._blob(storage_key)
            # Detect content type server-side; never rely on browser MIME claim.
            content_type = _detect_content_type(content, original_filename)
            blob.upload_from_string(content, content_type=content_type)
            logger.info(
                "[Firebase] Uploaded object key=%s size=%d content_type=%s",
                storage_key, len(content), content_type,
            )
            return storage_key
        except StorageException:
            raise
        except Exception as exc:
            raise StorageException(
                f"Firebase upload failed (key={storage_key}): {exc}"
            ) from exc

    def read_file(self, storage_key: str) -> bytes:
        """
        Download bytes from Firebase Storage.

        Raises:
            StorageException if the object does not exist or download fails.
        """
        try:
            blob = self._blob(storage_key)
            if not blob.exists():
                raise StorageException(f"Object not found in Firebase: {storage_key}")
            data = blob.download_as_bytes()
            logger.info(
                "[Firebase] Downloaded object key=%s size=%d", storage_key, len(data)
            )
            return data
        except StorageException:
            raise
        except Exception as exc:
            raise StorageException(
                f"Firebase download failed (key={storage_key}): {exc}"
            ) from exc

    def file_exists(self, storage_key: str) -> bool:
        """Check whether an object exists in Firebase Storage."""
        try:
            return self._blob(storage_key).exists()
        except Exception:
            return False

    def delete_file(self, storage_key: str) -> None:
        """
        Delete an object from Firebase Storage.

        Safe to call on non-existent objects (no-op).
        """
        try:
            blob = self._blob(storage_key)
            if blob.exists():
                blob.delete()
                logger.info("[Firebase] Deleted object key=%s", storage_key)
        except StorageException:
            raise
        except Exception as exc:
            raise StorageException(
                f"Firebase delete failed (key={storage_key}): {exc}"
            ) from exc

    def get_metadata(self, storage_key: str) -> Dict[str, Any]:
        """
        Return non-sensitive object metadata (size, content-type, provider).
        Never includes signed URLs, bucket credentials, or private-key material.
        """
        try:
            blob = self._blob(storage_key)
            if not blob.exists():
                raise StorageException(f"Object not found: {storage_key}")
            blob.reload()
            return {
                "storage_key": storage_key,
                "file_size_bytes": blob.size,
                "content_type": blob.content_type,
                "exists": True,
                "provider": "firebase",
                "bucket": self._bucket_name,
            }
        except StorageException:
            raise
        except Exception as exc:
            raise StorageException(
                f"Firebase get_metadata failed (key={storage_key}): {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Firebase-specific extras
    # ------------------------------------------------------------------

    def generate_signed_url(
        self, storage_key: str, expiry_minutes: int = 15
    ) -> str:
        """
        Generate a short-lived V4 signed URL for authorised download.

        IMPORTANT:
        - Call this ONLY after backend authorization has been verified.
        - Never log, cache, or return the URL outside the authorised response.
        - The default expiry is 15 minutes; do not increase without justification.

        Returns:
            A HTTPS signed URL valid for `expiry_minutes`.
        """
        try:
            blob = self._blob(storage_key)
            url = blob.generate_signed_url(
                expiration=datetime.timedelta(minutes=expiry_minutes),
                method="GET",
                version="v4",
            )
            # Intentionally do NOT log the URL itself.
            logger.info(
                "[Firebase] Generated signed URL for key=%s expiry=%dmin",
                storage_key, expiry_minutes,
            )
            return url
        except Exception as exc:
            raise StorageException(
                f"Signed URL generation failed (key={storage_key}): {exc}"
            ) from exc

    def verify_integrity(self, storage_key: str, expected_sha256: str) -> bool:
        """
        Download and verify the SHA-256 digest of a stored object.

        Returns True if the digest matches, False otherwise.
        Raises StorageException if the object cannot be read.
        """
        data = self.read_file(storage_key)
        actual = hashlib.sha256(data).hexdigest()
        match = actual == expected_sha256
        if not match:
            logger.warning(
                "[Firebase] Integrity mismatch for key=%s expected=%s actual=%s",
                storage_key, expected_sha256, actual,
            )
        return match


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _detect_content_type(content: bytes, filename: str) -> str:
    """
    Detect content type from file magic bytes (preferred) with filename extension
    as fallback. Never relies solely on caller-supplied MIME type.
    """
    # PDF magic
    if content[:4] == b"%PDF":
        return "application/pdf"
    # PNG magic
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    # JPEG magic
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    # ZIP / DOCX / XLSX / ODP families share the ZIP magic
    if content[:4] == b"PK\x03\x04":
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        mime_map = {
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        }
        return mime_map.get(ext, "application/octet-stream")
    return "application/octet-stream"

