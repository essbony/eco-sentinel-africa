"""Eco Sentinel Africa — package principal."""

from importlib.metadata import version as _pkg_version

try:
    __version__ = _pkg_version("eco-sentinel-africa")
except Exception:
    __version__ = "0.1.0"

__all__ = ["__version__"]
