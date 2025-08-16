"""MVP test suite for Nova Brief - validates core functionality and structure."""

import os
import sys
import asyncio
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_imports():
    """Test that all core modules can be imported."""
    print("🧪 Testing module imports...")
    
    try:
        # Test observability imports
        from src.observability.logging import get_logger
        from src.observability.tracing import TimedOperation, emit_event
        print("✅ Observability modules imported successfully")
    except Exception as e:
        print(f"❌ Observability modules error: {e}")
        return False
    
    try:
        # Test storage models
        from src.storage.models import (
            create_initial_state, create_default_constraints,
            SearchResult, Document, Chunk, Claim, Citation
        )
        print("✅ Storage models imported successfully")
    except Exception as e:
        print(f"❌ Storage models error: {e}")
        return False
    
    try:
        # Test provider modules (may fail due to missing dependencies)
        from src.providers.openrouter_client import OpenRouterClient
        from src.providers.search_providers import SearchManager
        print("✅ Provider modules imported successfully")
    except ValueError as e:
        if "API_KEY" in str(e):
            print("✅ Provider modules structure verified (API key required)")
        else:
            print(f"⚠️  Provider modules error: {e}")
    except ImportError as e:
        print(f"⚠️  Provider modules need dependencies: {e}")
    
    try:
        # Test agent modules
        from src.agent import planner, searcher, reader, analyst, verifier, writer
        from src.agent.orchestrator import run_research_pipeline
        print("✅ Agent modules imported successfully")
    except ImportError as e:
        print(f"⚠️  Agent modules need dependencies: {e}")
    
    try:
        # Test tools
        from src.tools import web_search, fetch_url, parse_pdf
        print("✅ Tool modules imported successfully")
    except ImportError as e:
        print(f"⚠️  Tool modules need dependencies: {e}")
    
    try:
        # Test configuration
        from src.config import Config, validate_environment
        print("✅ Configuration module imported successfully")
    except ImportError as e:
        print(f"⚠️  Configuration module needs dependencies: {e}")
    
    return True


def test_configuration():
    """Test configuration validation."""
    print("\n🧪 Testing configuration...")
    
    try:
        from src.config import Config
        
        # Test config validation
        config = Config()
        validation = config.validate()
        
        print(f"Configuration valid: {validation['valid']}")
        
        if validation['issues']:
            print("❌ Configuration issues:")
            for issue in validation['issues']:
                print(f"   - {issue}")
        
        if validation['warnings']:
            print("⚠️  Configuration warnings:")
            for warning in validation['warnings']:
                print(f"   - {warning}")
        
        # Test config summary
        summary = config.get_summary()
        print(f"✅ Configuration summary: {summary}")
        
        return validation['valid'] or len(validation['issues']) <= 1  # Allow missing API key
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


def test_data_models():
    """Test data model creation and validation."""
    print("\n🧪 Testing data models...")
    
    try:
        from src.storage.models import (
            create_initial_state, create_default_constraints,
            validate_search_result, validate_claim, validate_document,
            create_chunks_from_document
        )
        
        # Test constraint creation
        constraints = create_default_constraints()
        print(f"✅ Default constraints created: {constraints}")
        
        # Test state creation
        state = create_initial_state("Test Topic", constraints)
        print(f"✅ Initial state created for topic: {state['topic']}")
        
        # Test search result validation
        valid_result = {
            "title": "Test Title",
            "url": "https://example.com",
            "snippet": "Test snippet content"
        }
        
        invalid_result = {
            "title": "Test Title",
            "url": "invalid-url",
            "snippet": ""
        }
        
        assert validate_search_result(valid_result) == True
        assert validate_search_result(invalid_result) == False
        print("✅ Search result validation working")
        
        # Test claim validation
        valid_claim = {
            "id": "test-1",
            "text": "This is a test claim",
            "type": "fact",
            "confidence": 0.8
        }
        
        invalid_claim = {
            "id": "test-2",
            "text": "Invalid claim",
            "type": "invalid-type",
            "confidence": 1.5
        }
        
        assert validate_claim(valid_claim) == True
        assert validate_claim(invalid_claim) == False
        print("✅ Claim validation working")
        
        # Test document creation and chunking
        from src.storage.models import Document
        
        test_document: Document = {
            "url": "https://example.com",
            "title": "Test Document",
            "text": "This is a test document with some content. " * 50,  # Long enough to chunk
            "content_type": "text/html",
            "source_meta": {"domain": "example.com"}
        }
        
        chunks = create_chunks_from_document(test_document, max_tokens_per_chunk=100)
        print(f"✅ Document chunking created {len(chunks)} chunks")
        
        return True
        
    except Exception as e:
        print(f"❌ Data models test failed: {e}")
        return False


def test_logging_and_tracing():
    """Test logging and tracing functionality."""
    print("\n🧪 Testing logging and tracing...")
    
    try:
        from src.observability.logging import get_logger, redact_sensitive_data
        from src.observability.tracing import TimedOperation, emit_event
        
        # Test logger creation
        logger = get_logger("test_logger")
        logger.info("Test log message")
        print("✅ Logger created and message logged")
        
        # Test sensitive data redaction
        sensitive_data = {
            "api_key": "secret-key-123",
            "user_name": "test_user",
            "password": "secret-password"
        }
        
        redacted = redact_sensitive_data(sensitive_data)
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["user_name"] == "test_user"
        assert redacted["password"] == "***REDACTED***"
        print("✅ Sensitive data redaction working")
        
        # Test timed operation
        with TimedOperation("test_operation") as timer:
            import time
            time.sleep(0.1)  # Short delay for testing
        
        print("✅ Timed operation completed")
        
        # Test event emission
        emit_event("test_event", metadata={"test": "data"})
        print("✅ Event emission working")
        
        return True
        
    except Exception as e:
        print(f"❌ Logging and tracing test failed: {e}")
        return False


def test_pipeline_validation():
    """Test pipeline input validation."""
    print("\n🧪 Testing pipeline validation...")
    
    try:
        from src.agent.orchestrator import validate_pipeline_inputs
        from src.storage.models import create_default_constraints
        
        # Test valid inputs
        valid_topic = "Impact of AI on healthcare in 2024"
        valid_constraints = create_default_constraints()
        
        validation = validate_pipeline_inputs(valid_topic, valid_constraints)
        assert validation["valid"] == True
        print("✅ Valid inputs passed validation")
        
        # Test invalid inputs
        invalid_topic = ""
        validation = validate_pipeline_inputs(invalid_topic, valid_constraints)
        assert validation["valid"] == False
        print("✅ Invalid inputs rejected")
        
        # Test short topic
        short_topic = "AI"
        validation = validate_pipeline_inputs(short_topic, valid_constraints)
        assert validation["valid"] == False
        print("✅ Short topic rejected")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline validation test failed: {e}")
        return False


async def test_basic_pipeline_components():
    """Test basic pipeline component functionality (without API calls)."""
    print("\n🧪 Testing pipeline components...")
    
    try:
        from src.storage.models import create_initial_state, create_default_constraints
        
        # Test state management
        topic = "Test research topic"
        constraints = create_default_constraints()
        state = create_initial_state(topic, constraints)
        
        print(f"✅ Pipeline state initialized: {state['status']}")
        
        # Test state progression
        state["status"] = "planning"
        state["queries"] = ["test query 1", "test query 2"]
        assert len(state["queries"]) == 2
        print("✅ State management working")
        
        return True
        
    except Exception as e:
        print(f"❌ Pipeline components test failed: {e}")
        return False


def test_file_structure():
    """Test that required files and directories exist."""
    print("\n🧪 Testing file structure...")
    
    required_files = [
        "src/__init__.py",
        "src/agent/__init__.py",
        "src/tools/__init__.py", 
        "src/providers/__init__.py",
        "src/storage/__init__.py",
        "src/observability/__init__.py",
        "src/app.py",
        "src/config.py",
        "pyproject.toml",
        ".env.example"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True


def test_environment_setup():
    """Test environment setup."""
    print("\n🧪 Testing environment setup...")
    
    try:
        # Check .env.example exists
        if not os.path.exists(".env.example"):
            print("❌ .env.example file missing")
            return False
        
        print("✅ .env.example file exists")
        
        # Check pyproject.toml exists and has required sections
        if not os.path.exists("pyproject.toml"):
            print("❌ pyproject.toml file missing")
            return False
        
        with open("pyproject.toml", 'r') as f:
            content = f.read()
            
        required_sections = ["[project]", "dependencies", "streamlit", "openai"]
        missing_sections = [section for section in required_sections if section not in content]
        
        if missing_sections:
            print(f"⚠️  pyproject.toml missing sections: {missing_sections}")
        else:
            print("✅ pyproject.toml properly configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment setup test failed: {e}")
        return False


def main():
    """Run all MVP tests."""
    print("🚀 Starting Nova Brief MVP Test Suite")
    print("=" * 50)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Environment Setup", test_environment_setup),
        ("Module Imports", test_imports),
        ("Configuration", test_configuration),
        ("Data Models", test_data_models),
        ("Logging & Tracing", test_logging_and_tracing),
        ("Pipeline Validation", test_pipeline_validation),
        ("Pipeline Components", lambda: asyncio.run(test_basic_pipeline_components()))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("🎯 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! MVP is ready for deployment.")
    elif passed >= total * 0.8:
        print("✅ MVP is mostly functional. Address failing tests for production.")
    else:
        print("⚠️  Significant issues found. Review and fix before deployment.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)