import sys
import os
from unittest.mock import MagicMock

# Ensure source is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# Helper to mock module if missing
def mock_module(name):
    try:
        __import__(name)
    except ImportError:
        sys.modules[name] = MagicMock()

# Mock dependencies
mock_module("keyring")
mock_module("rich")
mock_module("rich.console")
mock_module("rich.logging")
mock_module("typer")
mock_module("copilot")

# Pydantic mock needs special care for BaseModel inheritance
try:
    import pydantic
except ImportError:
    pydantic_mock = MagicMock()

    class MockBaseModel:
        model_fields = {}

        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            # Set defaults from class attributes if not provided
            # This is a simplification; real pydantic does more
            for cls in self.__class__.__mro__:
                for k, v in cls.__dict__.items():
                    if not k.startswith("_") and not callable(v) and k not in kwargs:
                         if k not in self.__dict__:
                             setattr(self, k, v)

        def model_dump(self, **kwargs):
            exclude_none = kwargs.get("exclude_none", False)
            return {k: v for k, v in self.__dict__.items()
                    if not k.startswith("_") and (not exclude_none or v is not None)}

        @classmethod
        def model_validate(cls, obj):
            return cls(**obj)

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

        def to_dict(self):
            return self.model_dump()

    pydantic_mock.BaseModel = MockBaseModel
    sys.modules["pydantic"] = pydantic_mock
