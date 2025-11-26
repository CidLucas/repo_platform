"""Compatibility shim that exposes model symbols under
`vizu_db_connector.models` by forwarding to the shared `vizu_models` package.

This lets existing code/tests import `vizu_db_connector.models.<...>` while
keeping the canonical model definitions in `libs/vizu_models`.
"""
try:
    # The canonical models are exported at package level in `vizu_models`.
    # Import all exported symbols so `from vizu_db_connector.models import X`
    # continues to work.
    from vizu_models import *  # type: ignore  # re-export package-level symbols

    # Also keep a module-level reference to the package for callers that do
    # `import vizu_db_connector.models as models`.
    import vizu_models as models  # type: ignore
except Exception:
    # Surface the original import error (useful in CI/local where dependencies
    # are missing). Tests will fail with a meaningful message if vizu_models
    # isn't available.
    raise
