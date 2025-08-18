#!/usr/bin/env python3
"""Test script for Heterogeneous Agent Policies configuration system."""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.config import Config


def test_agent_model_selection():
    """Test agent-specific model selection."""
    print("🤖 Testing agent model selection...")
    
    try:
        # Test different agents with different preferences
        test_cases = [
            ("planner", "speed"),
            ("planner", "balanced"), 
            ("planner", "quality"),
            ("analyst", "balanced"),
            ("writer", "quality"),
            ("verifier", "quality"),
            ("searcher", "balanced")  # This should return None (no LLM required)
        ]
        
        for agent_name, preference in test_cases:
            model = Config.get_agent_model(agent_name, preference)
            
            if agent_name == "searcher":
                if model is None:
                    print(f"  ✅ {agent_name} ({preference}): No LLM required (correct)")
                else:
                    print(f"  ⚠️  {agent_name} ({preference}): Got model '{model}' but shouldn't need LLM")
            else:
                if model:
                    print(f"  ✅ {agent_name} ({preference}): {model}")
                else:
                    print(f"  ❌ {agent_name} ({preference}): No model selected")
        
        return True
    except Exception as e:
        print(f"  ❌ Agent model selection test failed: {e}")
        return False


def test_audience_specific_models():
    """Test audience-specific model selection for writer."""
    print("📝 Testing audience-specific writer models...")
    
    try:
        audiences = ["Executive", "Technical", "General"]
        preferences = ["speed", "balanced", "quality"]
        
        for audience in audiences:
            for preference in preferences:
                model = Config.get_agent_model("writer", preference, audience)
                if model:
                    print(f"  ✅ Writer ({audience}, {preference}): {model}")
                else:
                    print(f"  ❌ Writer ({audience}, {preference}): No model selected")
        
        return True
    except Exception as e:
        print(f"  ❌ Audience-specific model test failed: {e}")
        return False


def test_agent_parameters():
    """Test agent-specific parameter selection."""
    print("⚙️ Testing agent parameters...")
    
    try:
        agents = ["planner", "analyst", "writer", "verifier"]
        
        for agent in agents:
            params = Config.get_agent_parameters(agent)
            
            if "temperature" in params and "max_tokens" in params:
                print(f"  ✅ {agent}: temp={params['temperature']}, max_tokens={params['max_tokens']}")
            else:
                print(f"  ❌ {agent}: Missing required parameters")
        
        # Test audience-specific parameters for writer
        for audience in ["Executive", "Technical", "General"]:
            params = Config.get_agent_parameters("writer", audience)
            print(f"  ✅ Writer ({audience}): temp={params['temperature']}")
        
        return True
    except Exception as e:
        print(f"  ❌ Agent parameters test failed: {e}")
        return False


def test_agent_model_listing():
    """Test listing available models for agents."""
    print("📋 Testing agent model listing...")
    
    try:
        test_agents = ["planner", "analyst", "writer", "verifier", "searcher"]
        
        for agent in test_agents:
            models = Config.list_agent_models(agent, "balanced")
            
            if agent == "searcher":
                if len(models) == 0:
                    print(f"  ✅ {agent}: No models (correct - no LLM needed)")
                else:
                    print(f"  ⚠️  {agent}: Has models but shouldn't need LLM")
            else:
                if len(models) > 0:
                    print(f"  ✅ {agent}: {len(models)} available models")
                    print(f"    Primary: {models[0]}")
                else:
                    print(f"  ❌ {agent}: No available models")
        
        return True
    except Exception as e:
        print(f"  ❌ Agent model listing test failed: {e}")
        return False


def test_policy_validation():
    """Test agent policy validation."""
    print("🔍 Testing agent policy validation...")
    
    try:
        validation = Config.validate_agent_policies()
        
        if validation["valid"]:
            print("  ✅ All agent policies are valid")
        else:
            print("  ❌ Agent policy validation failed:")
            for issue in validation["issues"]:
                print(f"    - {issue}")
        
        if validation["warnings"]:
            print("  ⚠️  Warnings:")
            for warning in validation["warnings"]:
                print(f"    - {warning}")
        
        return validation["valid"]
    except Exception as e:
        print(f"  ❌ Policy validation test failed: {e}")
        return False


def test_policy_retrieval():
    """Test retrieving complete agent policies."""
    print("📊 Testing policy retrieval...")
    
    try:
        agents = ["planner", "analyst", "writer", "verifier", "searcher"]
        
        for agent in agents:
            policy = Config.get_agent_policy(agent)
            
            if policy:
                requirements = policy.get("model_requirements", {})
                llm_required = policy.get("llm_required", True)
                
                print(f"  ✅ {agent}: {policy['description']}")
                print(f"    LLM required: {llm_required}")
                if requirements:
                    req_summary = ", ".join(f"{k}:{v}" for k, v in list(requirements.items())[:3])
                    print(f"    Requirements: {req_summary}")
            else:
                print(f"  ❌ {agent}: No policy found")
        
        return True
    except Exception as e:
        print(f"  ❌ Policy retrieval test failed: {e}")
        return False


def test_config_summary():
    """Test configuration summary with agent policies."""
    print("📋 Testing configuration summary...")
    
    try:
        summary = Config.get_summary()
        
        required_fields = [
            "selected_model", "selected_research_mode", "agent_policies_count"
        ]
        
        missing_fields = [field for field in required_fields if field not in summary]
        
        if not missing_fields:
            print(f"  ✅ Configuration summary complete")
            print(f"    Selected model: {summary['selected_model']}")
            print(f"    Research mode: {summary['selected_research_mode']}")
            print(f"    Agent policies: {summary['agent_policies_count']}")
        else:
            print(f"  ❌ Missing fields in summary: {missing_fields}")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Configuration summary test failed: {e}")
        return False


def main():
    """Run all agent policy tests."""
    print("🧪 Testing Heterogeneous Agent Policies configuration system...\n")
    
    tests = [
        test_agent_model_selection,
        test_audience_specific_models,
        test_agent_parameters,
        test_agent_model_listing,
        test_policy_validation,
        test_policy_retrieval,
        test_config_summary
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test execution failed: {e}")
            results.append(False)
        print()  # Add spacing between tests
    
    success_count = sum(results)
    total_count = len(results)
    
    print(f"🏁 Agent Policies Tests: {success_count}/{total_count} passed")
    
    if success_count == total_count:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        exit(exit_code)
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        exit(1)
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        exit(1)