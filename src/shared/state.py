from .config import ConfigLoader

def get_suite_state() -> dict:
    """Get the current suite state paths."""
    config = ConfigLoader.load()
    return config.state_dirs

def init_suite():
    """Initialize the suite state root and directories."""
    config = ConfigLoader.load()
    print(f"Initializing Learning Suite state root: {config.data_root}")
    config.ensure_dirs()
    print("State directories initialized.")

if __name__ == "__main__":
    init_suite()
