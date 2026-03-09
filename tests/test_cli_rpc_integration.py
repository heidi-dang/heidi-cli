import pytest
import os
import subprocess
import time
from pathlib import Path
from heidi_cli.rpc_client import RPCClient, RPCError

@pytest.fixture(scope="module")
def heidid_server():
    # Set HEIDI_HOME to a temporary directory for isolated testing
    temp_home = Path("/tmp/heidi_test_home")
    if temp_home.exists():
        import shutil
        shutil.rmtree(temp_home)
    temp_home.mkdir(parents=True)
    os.environ["HEIDI_HOME"] = str(temp_home)
    
    # Path to the compiled heidid executable
    repo_root = Path(__file__).parent.parent.parent
    heidid_bin = repo_root / "heidi-engine" / "build" / "bin" / "heidid"
    
    if not heidid_bin.exists():
        pytest.skip(f"heidid executable not found at {heidid_bin}")
        
    process = subprocess.Popen(
        [str(heidid_bin), "--port", "8099"],
        env=os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for UDS socket to be created
    expected_sock = temp_home / "runtime" / "heidid.sock"
    max_wait = 5.0
    start = time.time()
    while not expected_sock.exists() and (time.time() - start) < max_wait:
        time.sleep(0.1)
        
    if not expected_sock.exists():
        process.kill()
        pytest.fail(f"heidid failed to create socket at {expected_sock}")
        
    yield expected_sock
    
    # Tear down
    process.terminate()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:
        process.kill()

def test_integration_stub_generate(heidid_server):
    client = RPCClient(socket_path=str(heidid_server))
    response = client.call("provider.generate", {
        "provider": "mock",
        "model": "mock",
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.7
    })
    
    assert "output" in response
    assert isinstance(response["output"], str)

def test_integration_fail_closed_real_mode_without_curl(heidid_server):
    # The current build has HEIDI_HAS_CURL=OFF, so REAL mode MUST fail
    client = RPCClient(socket_path=str(heidid_server))
    with pytest.raises(RPCError) as exc_info:
         client.call("provider.generate", {
             "model": "stub",
             "real_network_enabled": True
         })
         
    assert exc_info.value.code == -32001
    assert "E_TRANSPORT_UNAVAILABLE" in str(exc_info.value.message)
