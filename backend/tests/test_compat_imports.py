"""
Compatibility test for legacy top-level imports.

This test verifies whether the (now-removed) legacy module import paths are still
resolvable. Current project decision: top-level legacy modules were removed in
favour of app.services / app.core. This test asserts that importing the old paths
raises ImportError. If you prefer to keep backward-compatible shims (e.g. a small
app/scraper.py that re-exports from app.services.scraper and emits a DeprecationWarning),
update this test to accept the shim (e.g. import succeeds and module.__doc__ or a
DEPRECATED flag is present).
"""
import importlib
import pytest

OLD_MODULES = [
    "app.scraper",
    "app.tmdb",
    "app.security",
    "app.rate_limiter",
]


@pytest.mark.parametrize("module_name", OLD_MODULES)
def test_legacy_top_level_imports_removed(module_name):
    """
    Expect ImportError for legacy top-level modules. If your rollout strategy
    requires compatibility shims, change this test to detect a shim/DeprecationWarning
    instead of failing.
    """
    with pytest.raises(ImportError):
        importlib.import_module(module_name)
