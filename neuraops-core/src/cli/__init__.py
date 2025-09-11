# CLI module
"""
NeuraOps CLI Module
Command-line interface components and utilities
"""

# Import available modules from parent directory
try:
    from ..main import app, main

    __all__ = ["app", "main"]
except ImportError:
    # main.py import failed, just expose utilities
    __all__ = []
