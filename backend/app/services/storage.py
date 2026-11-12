import uuid
from io import BytesIO

from app.config import get_settings

_memory: dict[str, bytes] = {}
_client = None
_bucket_ready = False


def _minio():
    global _client
    settings = get_settings()
    if not settings.minio_endpoint or not settings.minio_root_user:
        return None
    if _client is None:
        from minio import Minio

        endpoint = settings.minio_endpoint.replace("http://", "").replace("https://", "")
        _client = Minio(
            endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password or "",
            secure=settings.minio_secure or endpoint.endswith(":443"),
        )
    return _client


def ensure_bucket() -> None:
    global _bucket_ready
    if _bucket_ready:
        return
    client = _minio()
    settings = get_settings()
    if client is None:
        return
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
        _bucket_ready = True
    except Exception:
        # Storage is best-effort for demo; callers may fall back to memory.
        pass


def put_bytes(data: bytes, filename: str, content_type: str) -> str:
    key = f"attachments/{uuid.uuid4().hex}_{filename}"
    client = _minio()
    settings = get_settings()
    if client is not None:
        try:
            ensure_bucket()
            client.put_object(
                settings.minio_bucket,
                key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return key
        except Exception:
            pass
    _memory[key] = data
    return key


def get_bytes(key: str) -> bytes | None:
    if key in _memory:
        return _memory[key]
    client = _minio()
    settings = get_settings()
    if client is None:
        return None
    try:
        resp = client.get_object(settings.minio_bucket, key)
        try:
            return resp.read()
        finally:
            resp.close()
            resp.release_conn()
    except Exception:
        return None


def reset_memory() -> None:
    _memory.clear()
