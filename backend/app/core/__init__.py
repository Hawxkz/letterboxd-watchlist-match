"""
Core module containing cross-cutting infrastructure:
- config: Environment variable loading and configuration
- cache: Centralized diskcache storage
- security: SSRF mitigation, IP validation, and input sanitization
- cors: Cross-Origin Resource Sharing configuration
- rate_limiter: In-memory sliding-window request throttling
"""
