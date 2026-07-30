import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "prism_data.json")
OVERLAY_PATH = os.path.join(os.path.dirname(__file__), "..", "prism_overlay.json")


@pytest.fixture
def preserve_dataset():
    """Guards the checked-in demo dataset. Nothing at runtime writes to
    prism_data.json any more (that is the entire point of the overlay), so
    yielding the original text also lets a test assert it stayed byte for byte
    identical. Snapshot, yield, restore either way."""
    with open(DATA_PATH, encoding="utf-8") as f:
        original = f.read()
    try:
        yield original
    finally:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            f.write(original)


@pytest.fixture(scope="session", autouse=True)
def isolate_overlay_from_developer_state():
    """Move any real prism_overlay.json aside for the whole run.

    Without this, a developer who adds a client through the UI would watch a
    dozen unrelated tests fail, because the suite asserts against the 16 seeded
    clients ("client_count == 16", "len(portfolios) == 16") and load_data()
    quite correctly merges their overlay into every one of those reads. The
    seed-data invariants are about the seed data, so the suite runs with the
    overlay out of the picture and puts it back untouched afterwards."""
    if not os.path.exists(OVERLAY_PATH):
        yield
        return
    with open(OVERLAY_PATH, encoding="utf-8") as f:
        original = f.read()
    os.remove(OVERLAY_PATH)
    try:
        yield
    finally:
        with open(OVERLAY_PATH, "w", encoding="utf-8") as f:
            f.write(original)


@pytest.fixture
def clean_overlay():
    """For tests that WRITE runtime edits. The session fixture above has
    already taken the developer's overlay out of play; this one guarantees a
    given test neither inherits another test's writes nor leaks its own."""
    if os.path.exists(OVERLAY_PATH):
        os.remove(OVERLAY_PATH)
    try:
        yield OVERLAY_PATH
    finally:
        if os.path.exists(OVERLAY_PATH):
            os.remove(OVERLAY_PATH)
