#!/usr/bin/env python3
"""
Quick test script to validate UI model selection functionality.
Tests that the UI can properly load and display all model options.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from src.config import Config


def test_ui_model_options():
    """Test that UI model selection data is properly formatted."""
    print("🖥️ TESTING UI MODEL SELECTION DATA")
    print("=" * 50)
    
    # Get available models and organize by base model (same as UI does)
    available_models_dict = Config.get_available_models_dict()
    
    # Organize models by base model for UI grouping
    model_groups = {}
    for base_model_key in Config.BASE_MODELS.keys():
        base_config = Config.BASE_MODELS[base_model_key]
        model_groups[base_model_key] = {
            'name': base_config['name'],
            'variants': Config.get_models_by_base_model(base_model_key),
            'supports_cerebras': base_config['supports_cerebras']
        }
    
    print(f"📊 Base model groups: {len(model_groups)}")
    
    # Simulate UI option creation
    total_options = 0
    for base_key, group_info in model_groups.items():
        group_name = f"📱 {group_info['name']}"
        if group_info['supports_cerebras']:
            group_name += " 🧠"
        
        print(f"\n{group_name}:")
        
        for variant_key, model_config in group_info['variants'].items():
            # Simulate UI status indicator
            status = "✅"  # Would check API key in real UI
            
            # Create descriptive display name (same logic as UI)
            provider_info = model_config.provider.title()
            if model_config.provider_params:
                if "cerebras" in str(model_config.provider_params):
                    provider_info += " + Cerebras 🧠"
                else:
                    provider_info += f" + {model_config.provider_params}"
            elif model_config.provider == "openrouter":
                provider_info += " (Default)"
            else:
                provider_info = f"Direct {provider_info}"
            
            display_name = f"{status} {group_info['name']} ({provider_info})"
            print(f"  {display_name}")
            total_options += 1
    
    print(f"\n📈 Total UI options: {total_options}")
    assert total_options == 12, f"Expected 12 UI options, got {total_options}"
    
    # Test model selection breakdown (UI details panel)
    test_model = "gpt-oss-120b-openrouter-cerebras"
    model_config = available_models_dict[test_model]
    
    print(f"\n🔍 Testing selection breakdown for: {test_model}")
    print(f"   🤖 Model: {model_config.model_id}")
    print(f"   🏢 Provider: {model_config.provider.title()}")
    
    if model_config.provider_params:
        print(f"   ⚙️ Inference: {model_config.provider_params}")
    else:
        print(f"   ⚙️ Inference: Default routing")
    
    if model_config.supports_cerebras:
        print("   🧠 Cerebras: Available")
    
    print("\n✅ UI MODEL SELECTION TEST PASSED")
    return True


def test_api_key_guidance():
    """Test API key guidance information."""
    print("\n🔑 TESTING API KEY GUIDANCE")
    print("=" * 50)
    
    # Test provider-specific guidance
    provider_guidance = {
        "google": "💡 Get Google AI API key: https://aistudio.google.com/app/apikey",
        "anthropic": "💡 Get Anthropic API key: https://console.anthropic.com/",
        "openai": "💡 Get OpenAI API key: https://platform.openai.com/api-keys",
        "openrouter": "💡 Get OpenRouter API key: https://openrouter.ai/keys"
    }
    
    available_models = Config.get_available_models_dict()
    
    # Test that each provider has guidance
    providers_found = set()
    for config in available_models.values():
        providers_found.add(config.provider)
    
    for provider in providers_found:
        assert provider in provider_guidance, f"Missing guidance for provider: {provider}"
        print(f"✅ {provider}: {provider_guidance[provider]}")
    
    print("\n✅ API KEY GUIDANCE TEST PASSED")
    return True


def main():
    """Run UI integration tests."""
    print("🚀 UI MODEL SELECTION INTEGRATION TEST")
    print("=" * 50)
    
    tests = [
        test_ui_model_options,
        test_api_key_guidance
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
    
    print("\n" + "=" * 50)
    print("🎯 UI TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Tests Passed: {passed}")
    print(f"❌ Tests Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL UI TESTS PASSED! Model selection UI ready.")
        return True
    else:
        print(f"\n⚠️ {failed} test(s) failed.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)