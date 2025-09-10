#!/usr/bin/env python3
"""
Test script to validate StrataSlims MCP and bot setup.
"""

import json
import subprocess
import sys
from pathlib import Path

def test_imports():
    """Test that all modules can be imported without critical errors."""
    print("Testing module imports...")
    
    try:
        import mcp_server
        print("✓ MCP server module imports successfully")
    except ImportError as e:
        print(f"✗ MCP server import failed: {e}")
        return False
    
    # Test main module (should handle missing env gracefully)
    try:
        result = subprocess.run([sys.executable, "main.py"], 
                              capture_output=True, text=True, timeout=5)
        if "Starting StrataSlims Discord Bot" in result.stdout:
            print("✓ Main module handles missing configuration gracefully")
        else:
            print(f"✗ Main module unexpected output: {result.stdout}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Main module timed out")
        return False
    except Exception as e:
        print(f"✗ Main module test failed: {e}")
        return False
    
    return True

def test_mcp_server():
    """Test MCP server functionality."""
    print("\nTesting MCP server...")
    
    # Test initialize message
    test_message = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }
    
    try:
        process = subprocess.Popen(
            [sys.executable, "mcp_server.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(
            input=json.dumps(test_message) + "\n",
            timeout=5
        )
        
        if process.returncode == 0:
            # Parse the response
            lines = stdout.strip().split('\n')
            for line in lines:
                if line.startswith('{"jsonrpc"'):
                    response = json.loads(line)
                    if response.get("result", {}).get("serverInfo", {}).get("name") == "strataslims":
                        print("✓ MCP server responds correctly to initialize")
                        return True
            
            print(f"✗ MCP server unexpected response: {stdout}")
            return False
        else:
            print(f"✗ MCP server failed: {stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ MCP server timed out")
        process.kill()
        return False
    except Exception as e:
        print(f"✗ MCP server test failed: {e}")
        return False

def test_project_structure():
    """Test that all expected files are present."""
    print("\nTesting project structure...")
    
    required_files = [
        "README.md",
        "mcp_server.py", 
        "mcp.json",
        "pyproject.toml",
        "requirements.txt",
        "LICENSE",
        ".env.example"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"✗ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print("✓ All required files are present")
        return True

def test_configuration_files():
    """Test configuration file formats."""
    print("\nTesting configuration files...")
    
    # Test MCP configuration
    try:
        with open("mcp.json", "r") as f:
            mcp_config = json.load(f)
        if "mcpServers" in mcp_config and "strataslims" in mcp_config["mcpServers"]:
            print("✓ MCP configuration is valid")
        else:
            print("✗ MCP configuration missing required keys")
            return False
    except Exception as e:
        print(f"✗ MCP configuration invalid: {e}")
        return False
    
    # Test pyproject.toml
    try:
        import tomllib
    except ImportError:
        # Python < 3.11
        try:
            import tomli as tomllib
        except ImportError:
            print("! Cannot test pyproject.toml format (missing tomllib/tomli)")
            return True
    
    try:
        with open("pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
        if pyproject.get("project", {}).get("name") == "strataslims":
            print("✓ pyproject.toml is valid")
        else:
            print("✗ pyproject.toml missing required project name")
            return False
    except Exception as e:
        print(f"✗ pyproject.toml invalid: {e}")
        return False
    
    return True

def main():
    """Run all tests."""
    print("StrataSlims Setup Validation")
    print("=" * 30)
    
    tests = [
        test_project_structure,
        test_configuration_files,
        test_imports,
        test_mcp_server
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! StrataSlims is properly set up for MCP and ready to use.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your settings")
        print("2. Run 'python main.py' to start the Discord bot")
        print("3. Run 'python mcp_server.py' to start the MCP server")
        return True
    else:
        print(f"\n❌ {total - passed} tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)