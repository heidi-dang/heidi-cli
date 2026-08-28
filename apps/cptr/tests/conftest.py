"""Hermetic CPTR test-session state.

The application database is normally migrated during CPTR startup. Unit tests that
exercise AgentService directly must not borrow a developer's existing ~/.cptr
schema, so the pytest process owns one temporary, fully migrated data directory.
Subprocess tests remain free to override CPTR_DATA_DIR with their own fixtures.
"""

from __future__ import annotations

import asyncio
import os
import tempfile

_TEST_DATA = tempfile.TemporaryDirectory(prefix="cptr-pytest-")
os.environ["CPTR_DATA_DIR"] = _TEST_DATA.name


def pytest_sessionstart(session) -> None:
    from cptr.utils.db import init_db

    asyncio.run(init_db())


def pytest_sessionfinish(session, exitstatus) -> None:
    from cptr.utils.db import get_engine

    asyncio.run(get_engine().dispose())
    _TEST_DATA.cleanup()
