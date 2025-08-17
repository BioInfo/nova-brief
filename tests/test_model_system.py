#!/usr/bin/env python3
"""
Comprehensive test suite for the expanded model selection system.
Tests all model configurations, provider routing, and inference options.
"""

import os
import sys
from typing import Dict, Any
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.config import Config
from src.providers.openrouter_client import LLMClient


def test_model_catalog():
    """Test the complete model catalog and configurations."""
    print("=" * 60)
    print("🧪 TESTING MODEL CATALOG")
    print("=" * 60)
    
    # Get all available models
    available_models = Config.get_available_models_dict()
    total_models = len(available_models)
    
    print(f"📊 Total available models: {total_models}")
    assert total_models == 12, f"Expected 12 models, found {total_models}"
    print("✅ Model count correct")
    
    # Test base model coverage
    expected_base_models = {
        "claude-sonnet-4", "gemini-2.5-flash", "gemini-2.5-pro", 
        "kimi-k2", "gpt-oss-120b", "gpt-5-mini", "qwen3-235b"
    }
    
    found_base_models = set()
    for model_key in available_models.keys():
        base_model = model_key.split('-openrouter-')[0].split('-direct')[0]
        found_base_models.add(base_model)
    
    missing_models = expected_base_models - found_base_models
    assert not missing_models, f"Missing base models: {missing_models}"
    print("✅ All base models present")
    
    # Test provider distribution
    provider_counts = {}
    for config in available_models.values():
        provider_counts[config.provider] = provider_counts.get(config.provider, 0) + 1
    
    print(f"📈 Provider distribution: {provider_counts}")
    assert "openrouter" in provider_counts, "OpenRouter provider missing"
    assert provider_counts["openrouter"] >= 8, "Not enough OpenRouter models"
    print("✅ Provider distribution correct")
    
    # Test Cerebras support
    cerebras_models = Config.get_cerebras_supported_models()
    print(f"🧠 Cerebras supported models: {len(cerebras_models)}")
    assert len(cerebras_models) >= 2, "Not enough Cerebras-supported models"
    
    # Verify GPT-OSS-120B has both variants
    gpt_variants = [k for k in available_models.keys() if k.startswith("gpt-oss-120b")]
    assert len(gpt_variants) == 2, f"Expected 2 GPT-OSS-120B variants, found {len(gpt_variants)}"
    
    has_default = any("default" in variant for variant in gpt_variants)
    has_cerebras = any("cerebras" in variant for variant in gpt_variants)
    assert has_default and has_cerebras, "Missing GPT-OSS-120B variants"
    print("✅ Cerebras variants correct")
    
    print("\n✅ MODEL CATALOG TEST PASSED")
    return True


def test_model_configurations():
    """Test individual model configurations."""
    print("\n" + "=" * 60)
    print("🔧 TESTING MODEL CONFIGURATIONS")
    print("=" * 60)
    
    available_models = Config.get_available_models_dict()
    
    for model_key, config in available_models.items():
        print(f"\n🧪 Testing {model_key}:")
        
        # Test basic configuration attributes
        assert config.provider, f"Missing provider for {model_key}"
        assert config.model_id, f"Missing model_id for {model_key}"
        assert config.display_name, f"Missing display_name for {model_key}"
        assert config.api_key_env, f"Missing api_key_env for {model_key}"
        
        print(f"   ✅ Provider: {config.provider}")
        print(f"   ✅ Model ID: {config.model_id}")
        print(f"   ✅ Display: {config.display_name}")
        print(f"   ✅ API Key: {config.api_key_env}")
        
        # Test provider-specific attributes
        if config.provider in ["openrouter", "openai", "anthropic", "google"]:
            assert config.base_url, f"Missing base_url for {model_key}"
            print(f"   ✅ Base URL: {config.base_url}")
        
        # Test Cerebras configuration
        if "cerebras" in model_key:
            assert config.provider_params, f"Missing provider_params for Cerebras model {model_key}"
            assert config.provider_params.get("provider") == "cerebras", f"Invalid Cerebras config for {model_key}"
            print(f"   ✅ Cerebras params: {config.provider_params}")
        
        # Validate API key environment variable format
        assert config.api_key_env.endswith("_API_KEY"), f"Invalid API key env format: {config.api_key_env}"
        
    print("\n✅ MODEL CONFIGURATIONS TEST PASSED")
    return True


def test_provider_routing():
    """Test provider routing configurations."""
    print("\n" + "=" * 60)
    print("🌐 TESTING PROVIDER ROUTING")
    print("=" * 60)
    
    available_models = Config.get_available_models_dict()
    
    # Test OpenRouter models
    openrouter_models = Config.get_models_by_provider("openrouter")
    print(f"📊 OpenRouter models: {len(openrouter_models)}")
    
    for model_key, config in openrouter_models.items():
        assert config.provider == "openrouter"
        assert config.base_url == "https://openrouter.ai/api/v1"
        assert config.api_key_env == "OPENROUTER_API_KEY"
        print(f"   ✅ {model_key}: OpenRouter routing configured")
    
    # Test direct provider models
    direct_providers = ["openai", "anthropic", "google"]
    for provider in direct_providers:
        provider_models = Config.get_models_by_provider(provider)
        if provider_models:
            print(f"📊 {provider.title()} direct models: {len(provider_models)}")
            for model_key, config in provider_models.items():
                assert config.provider == provider
                assert config.api_key_env == f"{provider.upper()}_API_KEY"
                print(f"   ✅ {model_key}: Direct {provider} routing configured")
    
    print("\n✅ PROVIDER ROUTING TEST PASSED")
    return True


def test_configuration_validation():
    """Test configuration validation system."""
    print("\n" + "=" * 60)
    print("🛡️ TESTING CONFIGURATION VALIDATION")
    print("=" * 60)
    
    available_models = Config.get_available_models_dict()
    
    # Test valid model validation
    for model_key in list(available_models.keys())[:3]:  # Test first 3 models
        validation = Config.validate_model_config(model_key)
        assert "valid" in validation
        assert "issues" in validation
        assert "warnings" in validation
        print(f"   ✅ {model_key}: Validation structure correct")
    
    # Test invalid model validation
    invalid_validation = Config.validate_model_config("invalid-model-key")
    assert not invalid_validation["valid"]
    assert len(invalid_validation["issues"]) > 0
    print("   ✅ Invalid model rejection working")
    
    # Test overall configuration validation
    overall_validation = Config.validate()
    assert "valid" in overall_validation
    print(f"   ✅ Overall config validation: {overall_validation['valid']}")
    
    print("\n✅ CONFIGURATION VALIDATION TEST PASSED")
    return True


def test_llm_client_initialization():
    """Test LLM client initialization for different models."""
    print("\n" + "=" * 60)
    print("🤖 TESTING LLM CLIENT INITIALIZATION")
    print("=" * 60)
    
    # Test models that should work with OpenRouter API key
    test_models = [
        "gpt-oss-120b-openrouter-default",
        "gpt-oss-120b-openrouter-cerebras",
        "claude-sonnet-4-openrouter-default",
        "qwen3-235b-openrouter-default"
    ]
    
    for model_key in test_models:
        try:
            client = LLMClient(model_key=model_key)
            assert client.model, f"Client model not set for {model_key}"
            assert client.provider, f"Client provider not set for {model_key}"
            print(f"   ✅ {model_key}: Client initialized successfully")
            print(f"      Model: {client.model}")
            print(f"      Provider: {client.provider}")
        except ValueError as e:
            if "API key is required" in str(e):
                print(f"   ⚠️ {model_key}: Requires API key (expected)")
            else:
                print(f"   ❌ {model_key}: Unexpected error: {e}")
                return False
        except Exception as e:
            print(f"   ❌ {model_key}: Failed to initialize: {e}")
            return False
    
    print("\n✅ LLM CLIENT INITIALIZATION TEST PASSED")
    return True


def test_helper_methods():
    """Test configuration helper methods."""
    print("\n" + "=" * 60)
    print("🔍 TESTING HELPER METHODS")
    print("=" * 60)
    
    # Test get_available_models
    model_keys = Config.get_available_models()
    assert len(model_keys) == 12, f"Expected 12 model keys, got {len(model_keys)}"
    print(f"   ✅ get_available_models: {len(model_keys)} models")
    
    # Test get_models_by_base_model
    gpt_models = Config.get_models_by_base_model("gpt-oss-120b")
    assert len(gpt_models) == 2, f"Expected 2 GPT-OSS-120B variants, got {len(gpt_models)}"
    print(f"   ✅ get_models_by_base_model: {len(gpt_models)} GPT variants")
    
    # Test get_cerebras_supported_models
    cerebras_models = Config.get_cerebras_supported_models()
    assert len(cerebras_models) >= 2, f"Expected ≥2 Cerebras models, got {len(cerebras_models)}"
    print(f"   ✅ get_cerebras_supported_models: {len(cerebras_models)} models")
    
    # Test get_current_model_config
    current_config = Config.get_current_model_config()
    if current_config:
        assert hasattr(current_config, 'provider')
        assert hasattr(current_config, 'model_id')
        print(f"   ✅ get_current_model_config: {current_config.display_name}")
    else:
        print("   ⚠️ get_current_model_config: No current config (expected if SELECTED_MODEL not set)")
    
    # Test configuration summary
    summary = Config.get_summary()
    required_keys = ["selected_model", "provider", "model_id", "api_key_configured"]
    for key in required_keys:
        assert key in summary, f"Missing key in summary: {key}"
    print(f"   ✅ get_summary: All required keys present")
    
    print("\n✅ HELPER METHODS TEST PASSED")
    return True


def main():
    """Run all tests."""
    print("🚀 NOVA BRIEF MODEL SYSTEM TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_model_catalog,
        test_model_configurations,
        test_provider_routing,
        test_configuration_validation,
        test_llm_client_initialization,
        test_helper_methods
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_func.__name__} FAILED: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print("🎯 TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    print(f"📊 Total Tests: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Model system is working correctly.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed. Please review the output above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)