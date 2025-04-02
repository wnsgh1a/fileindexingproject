# output_filter.py

import sys
import contextlib

@contextlib.contextmanager
def filter_specific_output():
    """Suppress specific output temporarily (e.g., from model loading)."""
    original_stdout = sys.stdout

    class DummyFile:
        def write(self, _): pass
        def flush(self): pass

    try:
        sys.stdout = DummyFile()
        yield
    finally:
        sys.stdout = original_stdout
