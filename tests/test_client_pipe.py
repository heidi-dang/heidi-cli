import sys
import os
import pytest

# client.py is in root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))



@pytest.mark.anyio
@pytest.mark.skip(reason="httpx mocking needs refactoring for PR #33")
async def test_pipe_routing_chat():
    pass


@pytest.mark.anyio
@pytest.mark.skip(reason="httpx mocking needs refactoring for PR #33")
async def test_pipe_routing_run():
    pass


@pytest.mark.anyio
@pytest.mark.skip(reason="httpx mocking needs refactoring for PR #33")
async def test_pipe_routing_loop():
    pass
