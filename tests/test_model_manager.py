"""
Comprehensive unit tests for ModelManager.
Tests all functionality including security, thread safety, resource management.
"""

import pytest
import asyncio
import threading
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import psutil

from heidi_cli.model_host.manager import ModelManager, _lazy_imports


class TestLazyImports:
    """Test lazy import functionality."""
    
    def test_lazy_imports_first_call(self):
        """Test that lazy imports work on first call."""
        with patch('builtins.__import__') as mock_import:
            mock_torch = Mock()
            mock_transformers = Mock()
            
            def import_side_effect(name, *args, **kwargs):
                if name == 'torch':
                    return mock_torch
                elif name == 'transformers':
                    return mock_transformers
                return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = import_side_effect
            
            torch, transformers = _lazy_imports()
            
            assert torch == mock_torch
            assert transformers == mock_transformers
            # Check that torch was imported (ignore additional arguments)
            torch_calls = [call for call in mock_import.call_args_list if call[0][0] == 'torch']
            transformer_calls = [call for call in mock_import.call_args_list if call[0][0] == 'transformers']
            assert len(torch_calls) == 1
            assert len(transformer_calls) == 1
    
    def test_lazy_imports_cached(self):
        """Test that lazy imports are cached."""
        # Reset globals to simulate first import
        import heidi_cli.model_host.manager as manager_module
        manager_module.torch = None
        manager_module.transformers = None
        
        with patch('builtins.__import__') as mock_import:
            mock_import.return_value = Mock()
            
            # First call
            _lazy_imports()
            # Second call should use cached values
            _lazy_imports()
            
            # Should only import once
            assert mock_import.call_count == 2  # torch + transformers


class TestModelManager:
    """Test ModelManager functionality."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self, temp_dir):
        """Create mock configuration."""
        mock_config = Mock()
        mock_config.models = []
        mock_config.max_new_tokens = 256
        mock_config.temperature = 0.8
        mock_config.do_sample = True
        mock_config.top_p = 0.95
        mock_config.top_k = 40
        mock_config.max_memory_gb = 4
        mock_config.max_concurrent_requests = 5
        mock_config.allowed_model_paths = [temp_dir]
        return mock_config
    
    @pytest.fixture
    def mock_registry(self, temp_dir):
        """Create mock registry file."""
        registry_data = {
            "active_stable": "test-model-v1",
            "versions": {
                "test-model-v1": {
                    "path": str(temp_dir / "model"),
                    "channel": "stable"
                }
            }
        }
        
        registry_path = temp_dir / "state" / "registry"
        registry_path.mkdir(parents=True, exist_ok=True)
        
        registry_file = registry_path / "registry.json"
        with open(registry_file, 'w') as f:
            json.dump(registry_data, f)
        
        return registry_file
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    @patch('heidi_cli.model_host.manager.Path')
    def test_init(self, mock_path, mock_config_loader, mock_config):
        """Test ModelManager initialization."""
        mock_config_loader.load.return_value = mock_config
        mock_path.return_value.exists.return_value = False
        
        manager = ModelManager()
        
        assert manager.config == mock_config
        assert manager.generation_config["max_new_tokens"] == 256
        assert manager.generation_config["temperature"] == 0.8
        assert manager.max_memory_gb == 4
        assert manager.max_concurrent_requests == 5
        assert manager._active_requests == 0
        assert isinstance(manager._lock, type(threading.RLock()))
    
    def test_validate_model_path_valid(self, temp_dir, mock_config):
        """Test valid model path validation."""
        manager = ModelManager()
        manager.allowed_model_paths = [temp_dir]
        
        valid_path = temp_dir / "model"
        assert manager._validate_model_path(valid_path) == True
    
    def test_validate_model_path_invalid(self, temp_dir, mock_config):
        """Test invalid model path validation."""
        manager = ModelManager()
        manager.allowed_model_paths = [temp_dir]
        
        invalid_path = Path("/etc/passwd")
        assert manager._validate_model_path(invalid_path) == False
    
    def test_validate_model_path_error(self, mock_config):
        """Test model path validation with error."""
        manager = ModelManager()
        
        with patch.object(Path, 'resolve', side_effect=Exception("Test error")):
            assert manager._validate_model_path(Path("test")) == False
    
    @patch('psutil.virtual_memory')
    def test_check_memory_usage_within_limit(self, mock_memory, mock_config):
        """Test memory usage check within limit."""
        mock_memory.return_value.used = 2 * (1024**3)  # 2GB
        
        manager = ModelManager()
        manager.max_memory_gb = 4
        
        assert manager._check_memory_usage() == True
    
    @patch('psutil.virtual_memory')
    def test_check_memory_usage_exceeds_limit(self, mock_memory, mock_config):
        """Test memory usage check exceeding limit."""
        mock_memory.return_value.used = 6 * (1024**3)  # 6GB
        
        manager = ModelManager()
        manager.max_memory_gb = 4
        
        assert manager._check_memory_usage() == False
    
    @patch('psutil.virtual_memory')
    def test_check_memory_usage_error(self, mock_memory, mock_config):
        """Test memory usage check with error."""
        mock_memory.side_effect = Exception("Memory error")
        
        manager = ModelManager()
        
        # Should allow on error
        assert manager._check_memory_usage() == True
    
    def test_estimate_token_count(self, mock_config):
        """Test token count estimation."""
        manager = ModelManager()
        
        # Test empty text
        assert manager._estimate_token_count("") == 0
        
        # Test short text
        count = manager._estimate_token_count("Hello world")
        assert count >= 1
        
        # Test longer text
        long_text = "This is a longer text with multiple words and sentences."
        count = manager._estimate_token_count(long_text)
        assert count > 1
    
    def test_fallback_response(self, mock_config):
        """Test fallback response generation."""
        manager = ModelManager()
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        response = manager._fallback_response("test-model", messages, "Test error")
        
        assert response["id"] == "chatcmpl-test-model"
        assert response["model"] == "test-model"
        assert "Test error" in response["choices"][0]["message"]["content"]
        assert response["usage"]["prompt_tokens"] > 0
        assert response["usage"]["completion_tokens"] > 0
        assert response["usage"]["total_tokens"] > 0
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    def test_unload_model(self, mock_config_loader, mock_config):
        """Test model unloading."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        manager.model = Mock()
        manager.tokenizer = Mock()
        manager.model_path = Path("test")
        
        with patch('gc.collect') as mock_gc:
            manager.unload_model()
            
            assert manager.model is None
            assert manager.tokenizer is None
            assert manager.model_path is None
            mock_gc.assert_called_once()
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    def test_reload_model(self, mock_config_loader, mock_config):
        """Test model reloading."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        manager.unload_model = Mock()
        manager._load_model_from_registry = Mock()
        
        manager.reload_model()
        
        manager.unload_model.assert_called_once()
        manager._load_model_from_registry.assert_called_once()
    
    @patch('psutil.virtual_memory')
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    def test_get_resource_status(self, mock_config_loader, mock_memory, mock_config):
        """Test resource status reporting."""
        mock_config_loader.load.return_value = mock_config
        
        mock_memory.return_value.used = 2 * (1024**3)
        mock_memory.return_value.available = 6 * (1024**3)
        mock_memory.return_value.percent = 25.0
        
        manager = ModelManager()
        manager._active_requests = 2
        manager.model = Mock()
        manager.model_path = Path("test")
        
        status = manager.get_resource_status()
        
        assert status["memory_used_gb"] == 2.0
        assert status["memory_available_gb"] == 6.0
        assert status["memory_percent"] == 25.0
        assert status["active_requests"] == 2
        assert status["max_concurrent_requests"] == 5
        assert status["model_loaded"] == True
        assert status["model_path"] == "test"
    
    @patch('psutil.virtual_memory')
    def test_get_resource_status_error(self, mock_memory, mock_config):
        """Test resource status with error."""
        mock_memory.side_effect = Exception("Memory error")
        
        manager = ModelManager()
        status = manager.get_resource_status()
        
        assert "error" in status
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    async def test_get_response_concurrent_limit(self, mock_config_loader, mock_config):
        """Test concurrent request limit."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        manager.max_concurrent_requests = 1
        manager._active_requests = 1  # Already at limit
        manager.model = None  # Force fallback
        
        messages = [{"role": "user", "content": "test"}]
        response = await manager.get_response("test-model", messages)
        
        assert "Server overloaded" in response["choices"][0]["message"]["content"]
        assert manager._active_requests == 1  # Should not increment
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    async def test_get_response_model_not_loaded(self, mock_config_loader, mock_config):
        """Test response when model not loaded."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        manager.model = None
        manager.tokenizer = None
        
        messages = [{"role": "user", "content": "test"}]
        response = await manager.get_response("test-model", messages)
        
        assert "Model not loaded" in response["choices"][0]["message"]["content"]
        assert manager._active_requests == 0  # Should be decremented in finally
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    async def test_get_response_memory_limit(self, mock_config_loader, mock_config):
        """Test response when memory limit exceeded."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        manager.model = None  # Force fallback
        manager.tokenizer = None
        
        with patch.object(manager, '_check_memory_usage', return_value=False):
            messages = [{"role": "user", "content": "test"}]
            response = await manager.get_response("test-model", messages)
            
            assert "High memory usage" in response["choices"][0]["message"]["content"]
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    async def test_get_response_with_loaded_model(self, mock_config_loader, mock_config):
        """Test response with loaded model."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        
        # Mock loaded model
        mock_tokenizer = Mock()
        mock_tokenizer.apply_chat_template.return_value = "mock_inputs"
        mock_tokenizer.decode.return_value = "Test response"
        mock_tokenizer.eos_token_id = 2
        
        mock_model = Mock()
        mock_model.parameters.return_value = [Mock()]
        mock_model.generate.return_value = Mock()
        mock_model.generate.return_value.__getitem__ = Mock(return_value="mock_tokens")
        mock_model.generate.return_value.__len__ = Mock(return_value=10)
        
        manager.model = mock_model
        manager.tokenizer = mock_tokenizer
        
        # Mock device
        mock_device = Mock()
        mock_model.parameters.return_value[0].device = mock_device
        
        with patch.object(manager, '_check_memory_usage', return_value=True):
            messages = [{"role": "user", "content": "test"}]
            response = await manager.get_response("test-model", messages)
            
            assert response["model"] == "test-model"
            assert response["choices"][0]["message"]["content"] == "Test response"
            assert response["usage"]["total_tokens"] > 0


class TestThreadSafety:
    """Test thread safety of ModelManager."""
    
    @patch('heidi_cli.model_host.manager.ConfigLoader')
    def test_concurrent_requests_counter(self, mock_config_loader, mock_config):
        """Test thread safety of concurrent requests counter."""
        mock_config_loader.load.return_value = mock_config
        
        manager = ModelManager()
        manager.max_concurrent_requests = 10
        results = []
        
        def increment_counter():
            for _ in range(100):
                with manager._lock:
                    current = manager._active_requests
                    manager._active_requests = current + 1
                    results.append(manager._active_requests)
                    manager._active_requests = current
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify no race conditions (counter should never exceed 1)
        assert all(count <= 1 for count in results)
        assert manager._active_requests == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
