
import asyncio
import time
import client
import httpx
from unittest.mock import MagicMock, AsyncMock, patch

# Mock httpx.AsyncClient to simulate latency
async def delayed_get(*args, **kwargs):
    await asyncio.sleep(0.1) # Short delay
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [{"id": "gpt-4", "name": "GPT-4"}]
    return mock_response

def blocking_subprocess(*args, **kwargs):
    time.sleep(2) # Blocking sleep
    result = MagicMock()
    result.returncode = 0
    result.stdout = "openai/gpt-4o"
    return result

async def heartbeat():
    """A background task that should run every 0.1s"""
    print("Heartbeat start")
    last_time = time.time()
    for i in range(5):
        await asyncio.sleep(0.5)
        now = time.time()
        print(f"Heartbeat tick: {now - last_time:.2f}s elapsed (expected 0.5s)")
        last_time = now

async def main():
    pipe = client.Pipe()
    pipe.valves.HEIDI_SERVER_URL = "http://mock-server"
    pipe.valves.ENABLE_OPENCODE = True

    print("Starting concurrent tasks (OpenCode enabled)...")

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = delayed_get
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    # Patch subprocess.run so we can control it
    # We want to ensure that even though subprocess.run blocks (simulated by time.sleep),
    # the event loop is not blocked because we use asyncio.to_thread

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch("subprocess.run", side_effect=blocking_subprocess):
            start_time = time.time()
            await asyncio.gather(
                heartbeat(),
                pipe.pipes()
            )
            print(f"Total time: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(main())
