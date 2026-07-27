"""nabokov — a console prose linter (readability checks, flake8-style workflow)."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _version

# Read from installed package metadata rather than hardcoding. A literal here was
# missed in the 26.7.7 release, which shipped reporting itself as 26.7.6 — the
# exact silent drift the version coupling exists to prevent, one file deeper than
# `make versions` was looking. pyproject.toml is the single source now.
try:
    __version__ = _version("nabokov")
except PackageNotFoundError:  # running from a source tree with no install
    __version__ = "0.0.0+unknown"
