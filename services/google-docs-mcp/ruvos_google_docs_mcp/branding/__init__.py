"""Vendored Ruvos brand assets for OAuth consent (CSP-safe data URIs)."""

from __future__ import annotations

import base64
from functools import lru_cache
from importlib import resources

_BRANDING = "ruvos_google_docs_mcp.branding"


@lru_cache(maxsize=1)
def ruvos_icon_red_data_uri() -> str:
    """Red Ruvos +R icon as a data URI."""
    svg_bytes = resources.files(_BRANDING).joinpath("ruvos-icon-red.svg").read_bytes()
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


@lru_cache(maxsize=1)
def ruvos_wordmark_navy_data_uri() -> str:
    """Navy Ruvos wordmark as a data URI."""
    svg_bytes = resources.files(_BRANDING).joinpath("ruvos-wordmark-navy.svg").read_bytes()
    encoded = base64.b64encode(svg_bytes).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
