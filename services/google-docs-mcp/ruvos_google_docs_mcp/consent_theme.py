"""Ruvos-branded OAuth consent HTML for FastMCP GoogleProvider."""

from __future__ import annotations

import html as html_module

from ruvos_google_docs_mcp.branding import (
    ruvos_icon_red_data_uri,
    ruvos_wordmark_navy_data_uri,
)

# Design bar tokens (ruvos.io console auth / UX mock lock)
_NAVY = "#122949"
_NAVY_HOVER = "#1a3a63"
_OFF_WHITE = "#F6F7F7"
_FOCUS_RING = "rgba(238, 62, 61, 0.28)"

_DEFAULT_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; base-uri 'none'"
)


def create_ruvos_consent_html(
    client_id: str,
    redirect_uri: str,
    scopes: list[str],
    txn_id: str,
    csrf_token: str,
    client_name: str | None = None,
    title: str = "Continue to Google",
    server_name: str | None = None,
    server_icon_url: str | None = None,
    server_website_url: str | None = None,
    client_website_url: str | None = None,
    csp_policy: str | None = None,
    is_cimd_client: bool = False,
    cimd_domain: str | None = None,
) -> str:
    """Render the OAuth consent interstitial with Ruvos auth styling.

    Drop-in replacement for ``fastmcp.server.auth.oauth_proxy.ui.create_consent_html``
    with the same form contract (POST, ``txn_id``, ``csrf_token``, ``action``).
    """
    app_name = html_module.escape(server_name or "Ruvos Google Docs")
    redirect_uri_escaped = html_module.escape(redirect_uri)
    title_escaped = html_module.escape(title)

    cimd_badge = ""
    if is_cimd_client and cimd_domain:
        cimd_domain_escaped = html_module.escape(cimd_domain)
        cimd_badge = f"""
        <div class="cimd-badge" role="status">
            <span class="cimd-check" aria-hidden="true">&#x2713;</span>
            Verified domain: <strong>{cimd_domain_escaped}</strong>
        </div>
        """

    detail_rows = [
        ("Application Name", html_module.escape(client_name or client_id)),
        ("Application Website", html_module.escape(client_website_url or "N/A")),
        ("Application ID", html_module.escape(client_id)),
        ("Redirect URI", redirect_uri_escaped),
        (
            "Requested Scopes",
            ", ".join(html_module.escape(s) for s in scopes) if scopes else "None",
        ),
    ]
    detail_rows_html = "\n".join(
        f"""
        <div class="detail-row">
            <div class="detail-label">{label}:</div>
            <div class="detail-value">{value}</div>
        </div>
        """
        for label, value in detail_rows
    )

    icon_uri = html_module.escape(ruvos_icon_red_data_uri(), quote=True)
    wordmark_uri = html_module.escape(ruvos_wordmark_navy_data_uri(), quote=True)

    policy = csp_policy if csp_policy is not None else _DEFAULT_CSP
    csp_meta = (
        f'<meta http-equiv="Content-Security-Policy" content="{html_module.escape(policy, quote=True)}" />'
        if policy
        else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title_escaped}</title>
    {csp_meta}
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: {_OFF_WHITE};
            color: {_NAVY};
            padding: 1.5rem 1rem;
        }}

        .auth-card {{
            background: #ffffff;
            border: 1px solid #e8eaed;
            border-radius: 1rem;
            box-shadow: 0 10px 30px rgba(18, 41, 73, 0.07);
            max-width: 24rem;
            width: 100%;
            padding: 2.25rem 1.75rem 1.75rem;
            text-align: center;
        }}

        .brand {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.625rem;
            margin-bottom: 1.5rem;
        }}

        .brand-icon {{
            width: 52px;
            height: 52px;
            display: block;
        }}

        .brand-wordmark {{
            width: 118px;
            height: auto;
            display: block;
        }}

        h1 {{
            font-size: 1.25rem;
            font-weight: 600;
            line-height: 1.35;
            margin-bottom: 0.75rem;
            color: {_NAVY};
        }}

        .lead {{
            font-size: 0.9375rem;
            line-height: 1.55;
            color: #4a5c6d;
            margin-bottom: 1.25rem;
        }}

        .lead strong {{
            color: {_NAVY};
            font-weight: 600;
        }}

        .info-box {{
            background: #f3f4f5;
            border-radius: 0.625rem;
            padding: 0.875rem 1rem;
            margin-bottom: 1.25rem;
            text-align: left;
            font-size: 0.875rem;
            line-height: 1.6;
            color: #4a5c6d;
        }}

        .info-box p {{
            margin: 0;
        }}

        .info-box p + p {{
            margin-top: 0.25rem;
        }}

        .info-box strong {{
            color: {_NAVY};
            font-weight: 600;
        }}

        .cimd-badge {{
            background: #eef6f1;
            border: 1px solid #b9dcc8;
            border-radius: 0.5rem;
            padding: 0.5rem 0.75rem;
            margin-bottom: 1rem;
            font-size: 0.8125rem;
            color: #1f4d36;
            text-align: center;
        }}

        .cimd-check {{
            color: #2f7a52;
            font-weight: 700;
            margin-right: 0.25rem;
        }}

        details {{
            margin-bottom: 1rem;
            text-align: left;
        }}

        summary {{
            cursor: pointer;
            font-size: 0.75rem;
            color: #8a96a3;
            font-weight: 500;
            list-style: none;
            padding: 0.25rem 0;
        }}

        summary::marker {{
            display: none;
        }}

        summary::before {{
            content: "▶";
            display: inline-block;
            margin-right: 0.375rem;
            font-size: 0.625rem;
            transition: transform 0.2s;
        }}

        details[open] summary::before {{
            transform: rotate(90deg);
        }}

        .detail-box {{
            background: #f8f9fa;
            border: 1px solid #e8eaed;
            border-radius: 0.5rem;
            padding: 0.625rem 0.75rem;
            margin-top: 0.375rem;
        }}

        .detail-row {{
            display: flex;
            padding: 0.3125rem 0;
            border-bottom: 1px solid #eceef0;
            gap: 0.5rem;
        }}

        .detail-row:last-child {{
            border-bottom: none;
        }}

        .detail-label {{
            font-weight: 600;
            min-width: 6.5rem;
            color: #6b7a88;
            font-size: 0.75rem;
            flex-shrink: 0;
        }}

        .detail-value {{
            flex: 1;
            font-family: 'SF Mono', 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 0.6875rem;
            color: {_NAVY};
            word-break: break-all;
        }}

        .button-group {{
            display: flex;
            flex-direction: column;
            gap: 0.625rem;
            margin-bottom: 1rem;
        }}

        button {{
            width: 100%;
            padding: 0.8125rem 1rem;
            font-size: 0.9375rem;
            font-weight: 600;
            border-radius: 0.5rem;
            cursor: pointer;
            font-family: inherit;
            transition: background-color 0.15s, border-color 0.15s, box-shadow 0.15s;
        }}

        button:focus-visible {{
            outline: none;
            box-shadow: 0 0 0 3px {_FOCUS_RING};
        }}

        .btn-approve {{
            background: {_NAVY};
            color: #ffffff;
            border: 1px solid {_NAVY};
        }}

        .btn-approve:hover {{
            background: {_NAVY_HOVER};
            border-color: {_NAVY_HOVER};
        }}

        .btn-deny {{
            background: #ffffff;
            color: {_NAVY};
            border: 1px solid #d5dbe0;
        }}

        .btn-deny:hover {{
            background: #f8f9fa;
            border-color: #c5ccd3;
        }}

        .footer-note {{
            font-size: 0.75rem;
            line-height: 1.45;
            color: #8a96a3;
        }}
    </style>
</head>
<body>
    <main class="auth-card">
        <div class="brand">
            <img src="{icon_uri}" alt="Ruvos" class="brand-icon" width="52" height="52" />
            <img src="{wordmark_uri}" alt="Ruvos" class="brand-wordmark" width="118" height="18" />
        </div>
        <h1>{title_escaped}</h1>
        <p class="lead">
            Connect <strong>{app_name}</strong> so Cursor can create and edit Google Docs
            in place on your behalf.
        </p>
        {cimd_badge}
        <div class="info-box" aria-label="Connection details">
            <p><strong>App:</strong> {app_name}</p>
            <p><strong>Next:</strong> Google account picker</p>
        </div>
        <form id="consentForm" method="POST" action="">
            <input type="hidden" name="txn_id" value="{html_module.escape(txn_id)}" />
            <input type="hidden" name="csrf_token" value="{html_module.escape(csrf_token)}" />
            <input type="hidden" name="submit" value="true" />
            <div class="button-group">
                <button type="submit" name="action" value="approve" class="btn-approve">Allow</button>
                <button type="submit" name="action" value="deny" class="btn-deny">Deny</button>
            </div>
        </form>
        <p class="footer-note">You stay in control. Deny cancels without signing in.</p>
        <details>
            <summary>Advanced details</summary>
            <div class="detail-box">
                {detail_rows_html}
            </div>
        </details>
    </main>
</body>
</html>"""
