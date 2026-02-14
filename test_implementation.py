#!/usr/bin/env python3
"""
Test script to validate the Heidi CLI implementation.
This script checks that all the required components are properly implemented.
"""

import sys
from pathlib import Path


def test_file_exists(filepath, description):
    """Test if a file exists."""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} (NOT FOUND)")
        return False


def test_import(module_name, description):
    """Test if a module can be imported."""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name} (ImportError: {e})")
        return False


def main():
    """Run all tests."""
    print("🔍 Heidi CLI Implementation Test Suite")
    print("=" * 50)

    # Get the project root
    project_root = Path(__file__).parent
    heidi_cli_dir = project_root / "heidi_cli" / "src" / "heidi_cli"

    tests_passed = 0
    total_tests = 0

    # Test 1: Installation scripts
    print("\n📦 Installation Scripts:")
    total_tests += 2
    if test_file_exists(project_root / "install.sh", "Linux/macOS install script"):
        tests_passed += 1
    if test_file_exists(project_root / "install.ps1", "Windows install script"):
        tests_passed += 1

    # Test 2: Core CLI files
    print("\n🔧 Core CLI Files:")
    core_files = [
        ("cli.py", "Main CLI application"),
        ("config.py", "Configuration manager"),
        ("server.py", "HTTP server"),
        ("setup_wizard.py", "Setup wizard"),
        ("openwebui_commands.py", "OpenWebUI commands"),
    ]

    for filename, description in core_files:
        total_tests += 1
        if test_file_exists(heidi_cli_dir / filename, description):
            tests_passed += 1

    # Test 3: Module imports (if we can import them)
    print("\n📚 Module Imports:")
    sys.path.insert(0, str(project_root / "heidi_cli" / "src"))

    modules_to_test = [
        ("heidi_cli.config", "ConfigManager"),
        ("heidi_cli.server", "HTTP Server"),
        ("heidi_cli.setup_wizard", "Setup Wizard"),
        ("heidi_cli.openwebui_commands", "OpenWebUI Commands"),
    ]

    for module_name, description in modules_to_test:
        total_tests += 1
        if test_import(module_name, description):
            tests_passed += 1

    # Test 4: Configuration structure
    print("\n⚙️  Configuration Structure:")
    try:
        from heidi_cli.config import HeidiConfig, ConfigManager

        # Test config model
        config = HeidiConfig()
        required_fields = ["openwebui_url", "openwebui_token", "server_url"]

        for field in required_fields:
            total_tests += 1
            if hasattr(config, field):
                print(f"✅ Config field: {field}")
                tests_passed += 1
            else:
                print(f"❌ Config field: {field} (MISSING)")

        # Test ConfigManager methods
        methods_to_test = [
            "ensure_dirs",
            "load_config",
            "save_config",
            "get_github_token",
            "set_github_token",
        ]
        for method in methods_to_test:
            total_tests += 1
            if hasattr(ConfigManager, method):
                print(f"✅ ConfigManager method: {method}")
                tests_passed += 1
            else:
                print(f"❌ ConfigManager method: {method} (MISSING)")

    except ImportError as e:
        print(f"❌ Configuration test failed: {e}")
        total_tests += len(["openwebui_url", "openwebui_token", "server_url"]) + 6

    # Test 5: CLI commands
    print("\n🖥️  CLI Commands:")
    try:
        from heidi_cli.cli import app

        # Check if setup command exists
        total_tests += 1
        if hasattr(app, "registered_commands") and any(
            cmd.name == "setup" for cmd in app.registered_commands
        ):
            print("✅ CLI command: setup")
            tests_passed += 1
        else:
            print("❌ CLI command: setup (MISSING)")

        # Check if openwebui typer exists
        total_tests += 1
        if hasattr(app, "registered_groups") and any(
            group.name == "openwebui" for group in app.registered_groups
        ):
            print("✅ CLI group: openwebui")
            tests_passed += 1
        else:
            print("❌ CLI group: openwebui (MISSING)")

    except ImportError as e:
        print(f"❌ CLI test failed: {e}")
        total_tests += 2

    # Test 6: Server endpoints
    print("\n🌐 Server Endpoints:")
    try:
        from heidi_cli.server import app as server_app

        # Check if required endpoints exist
        routes = [route.path for route in server_app.routes]
        required_endpoints = ["/health", "/agents", "/runs", "/openapi.json"]

        for endpoint in required_endpoints:
            total_tests += 1
            if endpoint in routes:
                print(f"✅ Server endpoint: {endpoint}")
                tests_passed += 1
            else:
                print(f"❌ Server endpoint: {endpoint} (MISSING)")

    except ImportError as e:
        print(f"❌ Server test failed: {e}")
        total_tests += 4

    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")

    if tests_passed == total_tests:
        print("🎉 All tests passed! Implementation is complete.")
        return 0
    else:
        print(f"⚠️  {total_tests - tests_passed} tests failed. Please review the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
