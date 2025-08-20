#!/usr/bin/env python3
"""
Test UI integration with Phase 4 features.
Verifies that quality scores flow from orchestrator to UI components.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agent.orchestrator import run_research_pipeline
from storage.models import create_default_constraints

async def test_ui_integration():
    """Test that orchestrator populates quality scores for UI display."""
    print("🧪 Testing UI Integration with Phase 4 Quality Scores")
    print("=" * 60)
    
    try:
        # Create minimal constraints for quick test
        constraints = create_default_constraints()
        constraints['max_rounds'] = 1
        constraints['per_domain_cap'] = 2
        constraints['fetch_timeout_s'] = 10
        
        print("📝 Running research pipeline with judge evaluation...")
        
        # Run pipeline
        result = await run_research_pipeline(
            topic="Brief test of AI applications",
            constraints=constraints,
            selected_model="gpt-oss-120b-openrouter-cerebras"
        )
        
        print(f"✅ Pipeline completed: success={result.get('success')}")
        
        if not result.get('success'):
            print(f"❌ Pipeline failed: {result.get('error')}")
            return False
        
        # Check for quality scores at top level (what UI looks for)
        quality_keys = [
            'overall_quality_score',
            'comprehensiveness_score', 
            'synthesis_score',
            'clarity_score',
            'justification'
        ]
        
        print("\n🎯 Checking Quality Scores in Results:")
        scores_found = 0
        for key in quality_keys:
            if key in result and result[key] is not None:
                value = result[key]
                if key == 'justification':
                    print(f"  ✅ {key}: {value[:50]}..." if len(str(value)) > 50 else f"  ✅ {key}: {value}")
                else:
                    print(f"  ✅ {key}: {value}")
                scores_found += 1
            else:
                print(f"  ❌ {key}: Not found")
        
        # Check report metadata as well
        report = result.get('report', {})
        if 'metadata' in report:
            print("\n📊 Checking Quality Scores in Report Metadata:")
            metadata = report['metadata']
            metadata_scores = 0
            for key in quality_keys:
                if key in metadata and metadata[key] is not None:
                    value = metadata[key]
                    if key == 'justification':
                        print(f"  ✅ {key}: {value[:50]}..." if len(str(value)) > 50 else f"  ✅ {key}: {value}")
                    else:
                        print(f"  ✅ {key}: {value}")
                    metadata_scores += 1
                else:
                    print(f"  ❌ {key}: Not found in metadata")
        
        print(f"\n📈 Summary:")
        print(f"  - Quality scores in top-level results: {scores_found}/{len(quality_keys)}")
        print(f"  - Report generated: {'✅' if report else '❌'}")
        print(f"  - Report has metadata: {'✅' if 'metadata' in report else '❌'}")
        
        # Success criteria: At least overall_quality_score should be present
        success = (
            result.get('success') and 
            'overall_quality_score' in result and 
            result['overall_quality_score'] is not None
        )
        
        if success:
            print("🎉 UI Integration Test PASSED!")
            print("   Quality scores are properly flowing from orchestrator to UI")
            return True
        else:
            print("❌ UI Integration Test FAILED!")
            print("   Quality scores are not properly populated for UI display")
            return False
            
    except Exception as e:
        print(f"❌ UI Integration Test FAILED with exception: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ui_integration())
    sys.exit(0 if success else 1)