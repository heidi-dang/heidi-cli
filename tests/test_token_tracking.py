"""
Comprehensive tests for token tracking functionality.
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from heidi_cli.token_tracking.models import (
    TokenUsage, CostConfig, TokenDatabase, get_token_database
)


class TestTokenUsage:
    """Test TokenUsage dataclass."""
    
    def test_token_usage_creation(self):
        """Test TokenUsage creation with defaults."""
        usage = TokenUsage(
            model_id="test-model",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )
        
        assert usage.model_id == "test-model"
        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30
        assert usage.session_id == ""
        assert usage.user_id == "default"
        assert usage.request_type == "chat_completion"
        assert usage.model_provider == "local"
        assert usage.cost_usd == 0.0
        assert usage.metadata == {}
        assert usage.timestamp is not None
    
    def test_token_usage_properties(self):
        """Test TokenUsage calculated properties."""
        usage = TokenUsage(
            model_id="test-model",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            cost_usd=0.015
        )
        
        # Test cost per 1k tokens
        expected_cost_per_1k = (0.015 / 1500) * 1000
        assert usage.cost_per_1k_tokens == expected_cost_per_1k
        
        # Test timestamp ISO format
        assert isinstance(usage.timestamp_iso, str)
        assert len(usage.timestamp_iso) > 0


class TestCostConfig:
    """Test CostConfig functionality."""
    
    def test_cost_config_creation(self):
        """Test CostConfig creation."""
        config = CostConfig(
            provider="openai",
            model_id="gpt-4",
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06
        )
        
        assert config.provider == "openai"
        assert config.model_id == "gpt-4"
        assert config.input_cost_per_1k == 0.03
        assert config.output_cost_per_1k == 0.06
        assert config.currency == "USD"
    
    def test_cost_calculation(self):
        """Test cost calculation."""
        config = CostConfig(
            provider="openai",
            model_id="gpt-4",
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06
        )
        
        # Test cost calculation
        prompt_tokens = 1000
        completion_tokens = 500
        
        expected_cost = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
        actual_cost = config.calculate_cost(prompt_tokens, completion_tokens)
        
        assert actual_cost == expected_cost
        assert actual_cost == 0.06  # 0.03 + 0.03


class TestTokenDatabase:
    """Test TokenDatabase functionality."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        temp_dir = Path(tempfile.mkdtemp())
        db_path = temp_dir / "test_tokens.db"
        db = TokenDatabase(db_path)
        yield db
        shutil.rmtree(temp_dir)
    
    def test_database_initialization(self, temp_db):
        """Test database initialization."""
        assert temp_db.db_path.exists()
        
        # Check tables exist
        import sqlite3
        with sqlite3.connect(temp_db.db_path) as conn:
            cursor = conn.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name IN ('token_usage', 'cost_configs')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            assert 'token_usage' in tables
            assert 'cost_configs' in tables
    
    def test_record_usage(self, temp_db):
        """Test recording token usage."""
        usage = TokenUsage(
            model_id="test-model",
            session_id="test-session",
            user_id="test-user",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.01
        )
        
        record_id = temp_db.record_usage(usage)
        assert record_id is not None
        assert record_id > 0
    
    def test_get_usage_history(self, temp_db):
        """Test retrieving usage history."""
        # Create test data
        now = datetime.now(timezone.utc)
        usages = [
            TokenUsage(
                model_id="model-1",
                session_id="session-1",
                user_id="user-1",
                prompt_tokens=100,
                completion_tokens=50,
                total_tokens=150,
                cost_usd=0.01
            ),
            TokenUsage(
                model_id="model-2",
                session_id="session-2",
                user_id="user-2",
                prompt_tokens=200,
                completion_tokens=100,
                total_tokens=300,
                cost_usd=0.02
            )
        ]
        
        # Record usage
        for usage in usages:
            temp_db.record_usage(usage)
        
        # Get all history
        history = temp_db.get_usage_history()
        assert len(history) == 2
        
        # Test filtering by model
        history_model1 = temp_db.get_usage_history(model_id="model-1")
        assert len(history_model1) == 1
        assert history_model1[0].model_id == "model-1"
        
        # Test limit
        history_limited = temp_db.get_usage_history(limit=1)
        assert len(history_limited) == 1
    
    def test_get_usage_summary(self, temp_db):
        """Test usage summary calculation."""
        now = datetime.now(timezone.utc)
        
        # Create test data for today
        usage1 = TokenUsage(
            model_id="model-1",
            session_id="session-1",
            user_id="user-1",
            prompt_tokens=1000,
            completion_tokens=500,
            total_tokens=1500,
            cost_usd=0.03
        )
        
        usage2 = TokenUsage(
            model_id="model-2",
            session_id="session-2",
            user_id="user-2",
            prompt_tokens=2000,
            completion_tokens=1000,
            total_tokens=3000,
            cost_usd=0.06
        )
        
        temp_db.record_usage(usage1)
        temp_db.record_usage(usage2)
        
        # Get daily summary
        summary = temp_db.get_usage_summary(period="day")
        
        assert summary["period"] == "day"
        assert summary["total"]["requests"] == 2
        assert summary["total"]["total_tokens"] == 4500
        assert summary["total"]["cost_usd"] == 0.09
        assert "model-1" in summary["by_model"]
        assert "model-2" in summary["by_model"]
    
    def test_cost_config_management(self, temp_db):
        """Test cost configuration management."""
        config = CostConfig(
            provider="openai",
            model_id="gpt-4",
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06
        )
        
        # Save config
        temp_db.save_cost_config(config)
        
        # Retrieve config
        retrieved = temp_db.get_cost_config("openai", "gpt-4")
        assert retrieved is not None
        assert retrieved.provider == "openai"
        assert retrieved.model_id == "gpt-4"
        assert retrieved.input_cost_per_1k == 0.03
        assert retrieved.output_cost_per_1k == 0.06
        
        # Test non-existent config
        non_existent = temp_db.get_cost_config("nonexistent", "model")
        assert non_existent is None
    
    def test_export_usage(self, temp_db):
        """Test usage data export."""
        # Create test data
        usage = TokenUsage(
            model_id="test-model",
            session_id="test-session",
            user_id="test-user",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            cost_usd=0.01
        )
        temp_db.record_usage(usage)
        
        # Test JSON export
        json_export = temp_db.export_usage(format="json")
        assert json_export is not None
        exported_data = json.loads(json_export)
        assert len(exported_data) == 1
        assert exported_data[0]["model_id"] == "test-model"
        
        # Test CSV export
        csv_export = temp_db.export_usage(format="csv")
        assert csv_export is not None
        assert "model_id" in csv_export
        assert "test-model" in csv_export


class TestTokenTrackingIntegration:
    """Test token tracking integration with model host."""
    
    @patch('heidi_cli.token_tracking.models.Path')
    @patch('heidi_cli.token_tracking.models.TokenDatabase')
    def test_get_token_database_singleton(self, mock_token_db, mock_path):
        """Test that get_token_database returns singleton."""
        mock_path.return_value.exists.return_value = True
        
        # Create mock database instance
        mock_db_instance = Mock()
        mock_token_db.return_value = mock_db_instance
        
        # Reset global instance
        import heidi_cli.token_tracking.models as models_module
        models_module._db_instance = None
        
        # First call should create instance
        db1 = get_token_database()
        # Second call should return same instance
        db2 = get_token_database()
        
        assert db1 is db2
        mock_token_db.assert_called_once_with()
    
    def test_token_usage_with_real_model(self):
        """Test token usage with realistic model data."""
        usage = TokenUsage(
            model_id="llama-2-7b",
            session_id="session-123",
            user_id="user-456",
            prompt_tokens=2048,
            completion_tokens=512,
            total_tokens=2560,
            request_type="chat_completion",
            model_provider="local",
            cost_usd=0.0,  # Free for local models
            metadata={
                "temperature": 0.7,
                "max_tokens": 512,
                "model_path": "/models/llama-2-7b"
            }
        )
        
        # Test all properties
        assert usage.model_id == "llama-2-7b"
        assert usage.session_id == "session-123"
        assert usage.user_id == "user-456"
        assert usage.prompt_tokens == 2048
        assert usage.completion_tokens == 512
        assert usage.total_tokens == 2560
        assert usage.request_type == "chat_completion"
        assert usage.model_provider == "local"
        assert usage.cost_usd == 0.0
        assert usage.metadata["temperature"] == 0.7
        assert usage.metadata["max_tokens"] == 512
        assert usage.metadata["model_path"] == "/models/llama-2-7b"


class TestTokenTrackingEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database."""
        temp_dir = Path(tempfile.mkdtemp())
        db_path = temp_dir / "test_tokens.db"
        db = TokenDatabase(db_path)
        yield db
        shutil.rmtree(temp_dir)
    
    def test_empty_usage_history(self, temp_db):
        """Test getting usage history when no data exists."""
        history = temp_db.get_usage_history()
        assert history == []
        
        summary = temp_db.get_usage_summary(period="day")
        assert summary["total"]["requests"] == 0
        assert summary["total"]["total_tokens"] == 0
        assert summary["total"]["cost_usd"] == 0.0
    
    def test_zero_token_usage(self, temp_db):
        """Test recording zero token usage."""
        usage = TokenUsage(
            model_id="test-model",
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_usd=0.0
        )
        
        record_id = temp_db.record_usage(usage)
        assert record_id is not None
        
        history = temp_db.get_usage_history()
        assert len(history) == 1
        assert history[0].total_tokens == 0
    
    def test_invalid_export_format(self, temp_db):
        """Test export with invalid format."""
        with pytest.raises(ValueError, match="Unsupported export format"):
            temp_db.export_usage(format="invalid")
    
    def test_cost_calculation_edge_cases(self):
        """Test cost calculation with edge cases."""
        config = CostConfig(
            provider="test",
            model_id="test-model",
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.02
        )
        
        # Test with zero tokens
        cost = config.calculate_cost(0, 0)
        assert cost == 0.0
        
        # Test with very small numbers
        cost = config.calculate_cost(1, 1)
        expected = (1/1000) * 0.01 + (1/1000) * 0.02
        assert cost == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
