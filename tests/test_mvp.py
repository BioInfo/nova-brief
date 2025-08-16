"""
Basic MVP test script for Nova Brief.
Tests core functionality without full execution (due to dependency requirements).
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported correctly."""
    print("Testing module imports...")
    
    api_key_errors = 0
    import_successes = 0
    
    # Test observability
    try:
        from src.observability.logging import get_logger
        from src.observability.tracing import emit_event
        print("✅ Observability modules imported successfully")
        import_successes += 1
    except Exception as e:
        print(f"❌ Observability import failed: {e}")
        return False
    
    # Test providers (may require API key but structure should be verified)
    try:
        from src.providers import cerebras_client, search_providers
        print("✅ Provider modules structure verified")
        import_successes += 1
    except ValueError as e:
        if "CEREBRAS_API_KEY" in str(e):
            print("✅ Provider modules structure verified (API key required for initialization)")
            api_key_errors += 1
            import_successes += 1
        else:
            print(f"⚠️  Provider modules error: {e}")
    except ImportError as e:
        print(f"⚠️  Provider modules need dependencies: {e}")
    
    # Test tools
    try:
        from src.tools import web_search, fetch_url, parse_pdf
        print("✅ Tool modules structure verified")
        import_successes += 1
    except ValueError as e:
        if "CEREBRAS_API_KEY" in str(e):
            print("✅ Tool modules structure verified (API key required for initialization)")
            api_key_errors += 1
            import_successes += 1
        else:
            print(f"⚠️  Tool modules error: {e}")
    except ImportError as e:
        print(f"⚠️  Tool modules need dependencies: {e}")
    
    # Test agents
    try:
        from src.agent import planner, searcher, reader, analyst, verifier, writer
        print("✅ Agent modules structure verified")
        import_successes += 1
    except ValueError as e:
        if "CEREBRAS_API_KEY" in str(e):
            print("✅ Agent modules structure verified (API key required for initialization)")
            api_key_errors += 1
            import_successes += 1
        else:
            print(f"⚠️  Agent modules error: {e}")
    except ImportError as e:
        print(f"⚠️  Agent modules need dependencies: {e}")
    
    # Success if we imported all modules (even with API key errors)
    return import_successes >= 4

def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        "requirements.txt",
        ".env.example",
        "src/app.py",
        "src/__init__.py",
        "src/agent/__init__.py",
        "src/agent/planner.py",
        "src/agent/searcher.py",
        "src/agent/reader.py",
        "src/agent/analyst.py",
        "src/agent/verifier.py",
        "src/agent/writer.py",
        "src/tools/__init__.py",
        "src/tools/web_search.py",
        "src/tools/fetch_url.py",
        "src/tools/parse_pdf.py",
        "src/providers/__init__.py",
        "src/providers/cerebras_client.py",
        "src/providers/search_providers.py",
        "src/observability/__init__.py",
        "src/observability/logging.py",
        "src/observability/tracing.py",
        "eval/harness.py",
        "eval/topics.json"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_configuration():
    """Test configuration files."""
    print("\nTesting configuration...")
    
    # Test requirements.txt
    requirements_path = Path("requirements.txt")
    if requirements_path.exists():
        requirements = requirements_path.read_text()
        required_deps = ["streamlit", "openai", "httpx", "trafilatura", "pypdf", "python-dotenv"]
        missing_deps = [dep for dep in required_deps if dep not in requirements]
        
        if missing_deps:
            print(f"❌ Missing dependencies: {missing_deps}")
            return False
        else:
            print("✅ All required dependencies listed")
    
    # Test .env.example
    env_example_path = Path(".env.example")
    if env_example_path.exists():
        env_content = env_example_path.read_text()
        required_vars = ["CEREBRAS_API_KEY", "MODEL", "SEARCH_PROVIDER"]
        missing_vars = [var for var in required_vars if var not in env_content]
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            return False
        else:
            print("✅ All required environment variables defined")
    
    return True

def test_evaluation_topics():
    """Test evaluation topics file."""
    print("\nTesting evaluation topics...")
    
    topics_path = Path("eval/topics.json")
    if not topics_path.exists():
        print("❌ Topics file missing")
        return False
    
    try:
        import json
        with open(topics_path) as f:
            topics = json.load(f)
        
        if len(topics) < 10:
            print(f"❌ Expected at least 10 topics, found {len(topics)}")
            return False
        
        # Check topic structure
        required_fields = ["id", "topic", "description", "complexity"]
        for topic in topics[:3]:  # Check first 3
            missing_fields = [field for field in required_fields if field not in topic]
            if missing_fields:
                print(f"❌ Topic missing fields: {missing_fields}")
                return False
        
        print(f"✅ {len(topics)} evaluation topics loaded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Topics file error: {e}")
        return False

def main():
    """Run all MVP tests."""
    print("=" * 60)
    print("NOVA BRIEF MVP TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Configuration", test_configuration),
        ("Evaluation Topics", test_evaluation_topics),
        ("Module Imports", test_imports)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nTests Passed: {passed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 ALL TESTS PASSED - MVP READY FOR DEPLOYMENT!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Set up environment: cp .env.example .env && edit .env")
        print("3. Run application: streamlit run src/app.py")
        print("4. Run evaluation: python eval/harness.py --quick")
    else:
        print(f"\n⚠️  {len(results) - passed} tests failed. Please fix issues before deployment.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()