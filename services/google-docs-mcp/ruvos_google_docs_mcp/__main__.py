"""Run the MCP server (Cloud Run: respects PORT env var)."""

from __future__ import annotations

from ruvos_google_docs_mcp.config import Settings
from ruvos_google_docs_mcp.server import create_app


def main() -> None:
    settings = Settings.from_env()
    mcp = create_app(settings)
    mcp.run(
        transport="http",
        host=settings.host,
        port=settings.port,
    )


if __name__ == "__main__":
    main()
