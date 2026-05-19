# Responses

RFC 6749 OAuth error response helpers. Each function returns a Starlette
`JSONResponse` with the appropriate status code and a `Cache-Control: no-store`
header.

::: mcp_authflow.responses
