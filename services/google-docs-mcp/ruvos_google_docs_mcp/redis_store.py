"""Build key_value RedisStore with Memorystore TLS verification."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

_MEMORYSTORE_CA_PATH = Path("/tmp/memorystore-server-ca.pem")


class RedisTlsConfigError(RuntimeError):
    """Raised when Redis TLS configuration is missing or insecure for production."""


def _allow_insecure_redis_tls() -> bool:
    return os.environ.get("ALLOW_REDIS_INSECURE_TLS", "").lower() in {
        "1",
        "true",
        "yes",
    }


def _write_ca_cert_once(pem_text: str) -> Path:
    """Write the Memorystore server CA PEM to a fixed path (mode 0600), once."""
    normalized = pem_text.strip() + "\n"
    if _MEMORYSTORE_CA_PATH.exists():
        existing = _MEMORYSTORE_CA_PATH.read_text(encoding="utf-8")
        if existing == normalized:
            return _MEMORYSTORE_CA_PATH

    _MEMORYSTORE_CA_PATH.write_text(normalized, encoding="utf-8")
    _MEMORYSTORE_CA_PATH.chmod(0o600)
    return _MEMORYSTORE_CA_PATH


def build_redis_store(redis_url: str):
    """Return a RedisStore for ``redis_url`` with Memorystore TLS verification.

    For ``rediss://`` URLs, ``REDIS_CA_CERT`` (PEM text) is required. The cert
    is written to ``/tmp/memorystore-server-ca.pem`` and passed as
    ``ssl_ca_certs`` to ``RedisStore``. Without a CA, startup fails closed.
    ``ALLOW_REDIS_INSECURE_TLS=1`` may be set for local/non-prod only.
    """
    from key_value.aio.stores.redis import RedisStore

    ca_pem = os.environ.get("REDIS_CA_CERT", "").strip()
    if ca_pem:
        ca_path = _write_ca_cert_once(ca_pem)
        return RedisStore(url=redis_url, ssl_ca_certs=str(ca_path))

    if urlparse(redis_url).scheme == "rediss":
        if _allow_insecure_redis_tls():
            return RedisStore(url=redis_url, ssl_cert_reqs="none")

        raise RedisTlsConfigError(
            "REDIS_CA_CERT is required for rediss:// URLs. Set REDIS_CA_CERT to "
            "the Memorystore server CA PEM (Secret Manager → Cloud Run secret). "
            "ALLOW_REDIS_INSECURE_TLS=1 is for local/non-prod only."
        )

    return RedisStore(url=redis_url)
