# API Integration Debugging

## When to use this skill
Diagnose a broken or misbehaving integration with an external HTTP API — covering
auth failures, request shape errors, network issues, and response parsing bugs.

## Approach
1. Capture the **raw** HTTP request and response: method, URL, headers, body, status code, latency
2. Verify authentication: token present, not expired, has the required scope/permissions
3. Compare the request shape against the API spec: method, path, content-type, required fields, encoding
4. Reproduce the failure with a minimal `curl` or `httpx` call **outside the application** to isolate app vs. API
5. Check for network-layer issues: DNS resolution, TLS certificate validity, proxy config, firewall rules
6. Review rate limiting: check `Retry-After`, `X-RateLimit-*` headers; verify retry logic uses exponential backoff
7. Validate response parsing: check whether the API changed its schema; compare against latest API changelog
8. Add structured logging at the integration boundary for request ID, status, and latency

## Tools used
- **curl / httpx**: reproduce the request in isolation
- **wireshark / mitmproxy**: inspect raw network traffic when headers alone are insufficient
- **OpenAPI spec**: compare actual request against documented contract

## Known constraints
- Always reproduce outside the application before changing application code
- Never log full authentication tokens — truncate to last 4 characters in logs
- Check the API provider's status page and changelog before assuming a code bug

## Known failure modes
- Assuming auth is correct without verifying token scope — 403 ≠ 401
- Ignoring `Retry-After` headers and hammering the API, triggering a cascade rate-limit ban
- Not pinning API version, causing silent breaking changes on provider upgrade
- Parsing errors caused by HTML error pages returned with status 200 OK

## Examples
### Good output pattern
**Observation:** POST /v2/orders returns 422 Unprocessable Entity.  
**Isolation:** curl reproduces it — app code not at fault.  
**Root cause:** API now requires `currency` field (added in v2.3, released 2026-04-10).  
**Fix:** Add `"currency": "USD"` to the request payload; pin to API version v2.3 in the client header.

### Bad output pattern
"The API is broken, let's add a retry loop until it works."
