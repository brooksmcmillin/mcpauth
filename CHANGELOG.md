# Changelog

## 0.2.0

### Breaking changes

- Renamed Python import from `mcp_auth_framework` to `mcp_authflow` so it
  matches the PyPI distribution name. The package is now installed and
  imported under the same name:

  ```python
  # Before
  from mcp_auth_framework import MemoryTokenStorage

  # After
  from mcp_authflow import MemoryTokenStorage
  ```

  No compatibility shim is provided; update imports directly.
- The GitHub repository moved from `brooksmcmillin/mcpauth` to
  `brooksmcmillin/mcp-authflow`. GitHub redirects the old URLs, but
  bookmarks and CI configurations should be updated.

## 0.1.0

Initial release on PyPI as `mcp-authflow` (imported as `mcp_auth_framework`).
OAuth 2.0 Authorization Server primitives for MCP: token storage
(in-memory + PostgreSQL), RFC 6749 error helpers, sliding-window rate
limiter, input validation, and CORS helpers.
