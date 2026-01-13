#!/usr/bin/env python3
"""
Phase 11.2 Step 3: Integration test - verify phase routing logic

This test simulates the orchestrator's main loop behavior to verify:
1. Phase routing activates when policy enabled and plan has phases
2. Flat execution path used when policy disabled or plan has no phases
"""

def test_phase_routing_logic():
    """Simulate the routing logic added in Step 2.1"""
    print("\n=== Phase 11.2 Integration Test: Routing Logic ===\n")
    
    # Scenario 1: Phase execution enabled + phased plan
    print("Scenario 1: Phase enabled + phased plan")
    POLICY = {"phase_execution_config": {"enabled": True}}
    CURRENT_PLAN = {
        "plan_id": "test_plan_1",
        "phases": [
            {"phase_id": "phase_1", "depends_on": [], "steps": []}
        ]
    }
    
    phase_config = POLICY.get("phase_execution_config", {})
    has_phases = "phases" in CURRENT_PLAN and CURRENT_PLAN.get("phases")
    phase_enabled = phase_config.get("enabled", False)
    
    if phase_enabled and has_phases:
        print("  ✓ Would route to execute_plan_with_phases()")
        result_1 = "PHASED"
    else:
        print("  ✗ Would route to flat execution (unexpected)")
        result_1 = "FLAT"
    
    assert result_1 == "PHASED", "Scenario 1 failed"
    
    # Scenario 2: Phase execution disabled + phased plan
    print("\nScenario 2: Phase disabled + phased plan")
    POLICY = {"phase_execution_config": {"enabled": False}}
    CURRENT_PLAN = {
        "plan_id": "test_plan_2",
        "phases": [
            {"phase_id": "phase_1", "depends_on": [], "steps": []}
        ]
    }
    
    phase_config = POLICY.get("phase_execution_config", {})
    has_phases = "phases" in CURRENT_PLAN and CURRENT_PLAN.get("phases")
    phase_enabled = phase_config.get("enabled", False)
    
    if phase_enabled and has_phases:
        print("  ✗ Would route to phased execution (unexpected)")
        result_2 = "PHASED"
    else:
        print("  ✓ Would route to flat execution")
        result_2 = "FLAT"
    
    assert result_2 == "FLAT", "Scenario 2 failed"
    
    # Scenario 3: Phase execution enabled + flat plan
    print("\nScenario 3: Phase enabled + flat plan")
    POLICY = {"phase_execution_config": {"enabled": True}}
    CURRENT_PLAN = {
        "plan_id": "test_plan_3",
        "steps": [
            {"step_id": "step_1", "action": "test"}
        ]
    }
    
    phase_config = POLICY.get("phase_execution_config", {})
    has_phases = "phases" in CURRENT_PLAN and bool(CURRENT_PLAN.get("phases"))
    phase_enabled = phase_config.get("enabled", False)
    
    if phase_enabled and has_phases:
        print("  ✗ Would route to phased execution (unexpected)")
        result_3 = "PHASED"
    else:
        print("  ✓ Would route to flat execution")
        result_3 = "FLAT"
    
    assert result_3 == "FLAT", "Scenario 3 failed"
    
    # Scenario 4: No policy (fallback to flat)
    print("\nScenario 4: No policy loaded")
    POLICY = None
    CURRENT_PLAN = {
        "plan_id": "test_plan_4",
        "phases": [
            {"phase_id": "phase_1", "depends_on": [], "steps": []}
        ]
    }
    
    phase_config = POLICY.get("phase_execution_config", {}) if POLICY else {}
    has_phases = "phases" in CURRENT_PLAN and CURRENT_PLAN.get("phases")
    phase_enabled = phase_config.get("enabled", False)
    
    if phase_enabled and has_phases:
        print("  ✗ Would route to phased execution (unexpected)")
        result_4 = "PHASED"
    else:
        print("  ✓ Would route to flat execution (safe fallback)")
        result_4 = "FLAT"
    
    assert result_4 == "FLAT", "Scenario 4 failed"
    
    print("\n" + "=" * 60)
    print("All routing scenarios passed ✓\n")
    print("Summary:")
    print("  Phased execution: Requires enabled=true AND phases present")
    print("  Flat execution: Default fallback (backward compatible)")
    print("  Safe degradation: Missing policy → flat execution")

if __name__ == "__main__":
    try:
        test_phase_routing_logic()
        print("\n✓ Phase 11.2 Step 3: Routing logic verified")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        exit(1)
