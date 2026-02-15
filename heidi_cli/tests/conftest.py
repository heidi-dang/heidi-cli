import sys
from unittest.mock import MagicMock

# Mock keyring
try:
    import keyring
except ImportError:
    keyring = MagicMock()
    sys.modules["keyring"] = keyring

# Mock pydantic
try:
    import pydantic
except ImportError:
    pydantic = MagicMock()
    class MockBaseModel:
        def __init__(self, **kwargs):
            pass
        def dict(self):
            return {}
    pydantic.BaseModel = MockBaseModel
    sys.modules["pydantic"] = pydantic

# Mock rich
try:
    import rich
except ImportError:
    rich = MagicMock()
    rich.console = MagicMock()
    rich.console.Console = MagicMock()
    rich.logging = MagicMock()
    rich.logging.RichHandler = MagicMock()
    sys.modules["rich"] = rich
    sys.modules["rich.console"] = rich.console
    sys.modules["rich.logging"] = rich.logging

# Mock copilot
try:
    import copilot
except ImportError:
    copilot = MagicMock()
    copilot.CopilotClient = MagicMock()
    sys.modules["copilot"] = copilot
