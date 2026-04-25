"""Local-only Python<3.11 dev shim.

Aliases ``tomli`` as ``tomllib`` so the codebase (which targets Python 3.12)
remains importable in older interpreters used for ad-hoc test runs. This
file is in the project root, so it is only picked up when the working
directory is on ``sys.path`` — i.e. during local pytest invocations from
the repo root. It has no effect on the shipped product.
"""
import sys

if "tomllib" not in sys.modules:
    try:
        import tomli as _tomli  # type: ignore[import-not-found]
    except ImportError:
        pass
    else:
        sys.modules["tomllib"] = _tomli
