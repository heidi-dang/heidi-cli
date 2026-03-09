import pytest
import struct
import json
import time
from unittest.mock import patch, MagicMock
from heidi_cli.rpc_client import RPCClient, RPCError

def test_framing_oversize_reject():
    client = RPCClient(socket_path="/tmp/dummy.sock")
    huge_payload = {"method": "dummy", "params": {"data": "x" * (512 * 1024 + 1)}}
    with pytest.raises(ValueError, match="Payload exceeds 512KB limit"):
        client._send(huge_payload)

@patch("socket.socket")
def test_daemon_down_fails_fast(mock_socket):
    mock_sock_instance = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock_instance
    mock_sock_instance.connect.side_effect = ConnectionRefusedError("Connection refused")
    
    client = RPCClient(socket_path="/tmp/nonexistent.sock")
    start = time.time()
    with pytest.raises(ConnectionError, match="Failed to communicate with heidid"):
        client.call("provider.generate", {"dummy": 1})
    duration = time.time() - start
    assert duration < 2.0  # Max retries take 0 + 0.5 + 1.0 = 1.5s max

@patch("socket.socket")
def test_valid_request_response(mock_socket):
    mock_sock_instance = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock_instance
    
    resp_payload = json.dumps({
        "jsonrpc": "2.0",
        "result": {"output": "hello"},
        "id": 1
    }).encode("utf-8")
    resp_len = struct.pack(">I", len(resp_payload))
    
    mock_sock_instance.recv.side_effect = [resp_len, resp_payload]
    
    client = RPCClient(socket_path="/tmp/dummy.sock")
    result = client.call("provider.generate", {"dummy": 1})
    
    assert result == {"output": "hello"}
    
@patch("socket.socket")
def test_server_error_response(mock_socket):
    mock_sock_instance = MagicMock()
    mock_socket.return_value.__enter__.return_value = mock_sock_instance
    
    resp_payload = json.dumps({
        "jsonrpc": "2.0",
        "error": {"code": -32001, "message": "E_TRANSPORT_UNAVAILABLE: curl not built"},
        "id": 1
    }).encode("utf-8")
    resp_len = struct.pack(">I", len(resp_payload))
    
    mock_sock_instance.recv.side_effect = [resp_len, resp_payload]
    
    client = RPCClient(socket_path="/tmp/dummy.sock")
    with pytest.raises(RPCError) as exc_info:
        client.call("provider.generate", {"real_network_enabled": True})
        
    assert exc_info.value.code == -32001
    assert "E_TRANSPORT_UNAVAILABLE" in str(exc_info.value)
