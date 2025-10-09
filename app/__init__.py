"""
App package for Legend AI API.

This package provides a thin wrapper around the existing root-level
`legend_ai_backend.app`, adding standardized observability (JSON logs,
optional Sentry), CORS configuration, and health/readiness endpoints.

All code is designed to be idempotent and composable.
"""
