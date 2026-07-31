import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "prism_data.json")


@pytest.fixture
def preserve_dataset():
    """Client mutations write straight into prism_data.json (by design, so
    runtime changes persist). Tests that exercise them must not leave
    the checked-in demo dataset mutated for the next run. Snapshot the file,
    yield, then restore it byte for byte."""
    with open(DATA_PATH, encoding="utf-8") as f:
        original = f.read()
    try:
        yield
    finally:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            f.write(original)
