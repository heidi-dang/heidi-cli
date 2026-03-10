#!/usr/bin/env python3
"""
Simple test script to validate Heidi CLI setup and functionality.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from heidi_cli.shared.config import ConfigLoader
        from heidi_cli.runtime.db import db
        from heidi_cli.model_host.manager import manager
        from heidi_cli.registry.manager import model_registry
        from heidi_cli.registry.eval import eval_harness
        from heidi_cli.registry.hotswap import hotswap_manager
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\n🔧 Testing configuration...")
    
    try:
        from heidi_cli.shared.config import ConfigLoader
        config = ConfigLoader.load()
        
        # Test basic config properties
        assert hasattr(config, 'data_root')
        assert hasattr(config, 'state_dirs')
        assert hasattr(config, 'models')
        
        print(f"✓ Configuration loaded from {config.data_root}")
        print(f"✓ Found {len(config.models)} local models")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_database():
    """Test database connectivity."""
    print("\n💾 Testing database...")
    
    try:
        from heidi_cli.runtime.db import db
        conn = db.get_connection()
        
        # Test that tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['memories', 'episodes', 'reflections', 'rules', 'reward_events', 'strategy_stats', 'run_summaries', 'rule_violations']
        
        for table in expected_tables:
            if table in tables:
                print(f"✓ Table {table} exists")
            else:
                print(f"❌ Table {table} missing")
                return False
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_opencode_api():
    """Test OpenCode API configuration."""
    print("\n🌐 Testing OpenCode API...")
    
    api_key = os.environ.get("OPENCODE_API_KEY")
    if api_key:
        print(f"✓ OpenCode API key found: {api_key[:10]}...")
        
        try:
            from heidi_cli.model_host.manager import manager
            if manager.opencode_client:
                print("✓ OpenCode client initialized")
                return True
            else:
                print("❌ OpenCode client not initialized")
                return False
        except Exception as e:
            print(f"❌ OpenCode client test failed: {e}")
            return False
    else:
        print("⚠️  OpenCode API key not found (set OPENCODE_API_KEY to enable)")
        return True  # Not a failure, just not configured

def test_model_host():
    """Test model host functionality."""
    print("\n🤖 Testing model host...")
    
    try:
        from heidi_cli.model_host.manager import manager
        
        # Test model listing
        models = manager.list_models()
        print(f"✓ Found {len(models)} available models")
        
        for model in models[:3]:  # Show first 3 models
            backend = model.get("backend", "local")
            if backend == "opencode":
                print(f"  🌐 {model['id']} (OpenCode API)")
            else:
                print(f"  📦 {model['id']} (Local)")
        
        return True
    except Exception as e:
        print(f"❌ Model host test failed: {e}")
        return False

def test_registry():
    """Test registry functionality."""
    print("\n📋 Testing registry...")
    
    try:
        from heidi_cli.registry.manager import model_registry
        
        # Test registry loading
        registry = model_registry.load_registry()
        print(f"✓ Registry loaded")
        print(f"✓ Active stable: {registry.get('active_stable', 'None')}")
        print(f"✓ Total versions: {len(registry.get('versions', {}))}")
        
        return True
    except Exception as e:
        print(f"❌ Registry test failed: {e}")
        return False

async def test_async_functionality():
    """Test async functionality."""
    print("\n⚡ Testing async functionality...")
    
    try:
        from heidi_cli.registry.manager import model_registry
        
        # Test version listing
        versions = await model_registry.list_versions()
        print(f"✓ Listed {len(versions)} versions")
        
        return True
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Heidi CLI Setup Validation\n")
    
    tests = [
        test_imports,
        test_config,
        test_database,
        test_opencode_api,
        test_model_host,
        test_registry,
    ]
    
    # Run sync tests
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    # Run async tests
    try:
        if asyncio.run(test_async_functionality()):
            passed += 1
            total += 1
    except Exception as e:
        print(f"❌ Async tests failed: {e}")
        total += 1
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Heidi CLI is ready to use.")
        print("\nNext steps:")
        print("1. Run 'heidi setup' to configure your API key and models")
        print("2. Run 'heidi model serve' to start the model host")
        print("3. Run 'heidi status' to check everything is working")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
