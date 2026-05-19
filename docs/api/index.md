# API Reference

The full public surface of `mcp_authflow`, generated from docstrings.

::: mcp_authflow
    options:
      show_root_heading: false
      show_root_toc_entry: false
      members: false

## Modules

- [**Storage**](storage.md): `TokenStorage`, `MemoryTokenStorage`, `PostgresTokenStorage`
- [**Responses**](responses.md): RFC 6749 error response helpers
- [**Rate Limiting**](rate-limiting.md): `SlidingWindowRateLimiter`, `AsyncRedisClient`
- [**Validation**](validation.md): `validate_client_id`, `parse_scope_field`, `parse_json_field`
- [**CORS**](cors.md): `parse_allowed_origins`, `build_cors_headers`, `get_cors_origin`

Everything in this list is re-exported from the top level. `from mcp_authflow import SlidingWindowRateLimiter` works the same as importing from the submodule.
