from .config import ConfigLoader

def init_suite():
    """Initialize the suite state root and directories."""
    config = ConfigLoader.load()
    print(f"Initializing Unified Learning Suite at: {config.data_root}")
    config.ensure_dirs()
    
    # Set default paths if not set
    if not config.memory_sqlite_path:
        config.memory_sqlite_path = config.state_dirs["memory"] / "memory.db"
    
    print("✓ State directories initialized.")

if __name__ == "__main__":
    init_suite()
