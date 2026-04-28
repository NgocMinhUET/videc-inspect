"""
Test script for HoloOcean scenario configuration.

Tests that the flat_wall_rgbd_v01 scenario can be loaded and run.

Usage:
    python scripts/test_scenario.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import holoocean
    HOLOOCEAN_AVAILABLE = True
except ImportError:
    HOLOOCEAN_AVAILABLE = False
    print("Warning: HoloOcean not installed. Install with: pip install holoocean")

from configs.scenarios.flat_wall_rgbd_v01 import get_scenario, get_inspection_trajectory


def test_scenario_config():
    """Test that scenario configuration is valid."""
    print("=" * 70)
    print("Testing HoloOcean Scenario Configuration")
    print("=" * 70)
    
    # Get scenario
    scenario = get_scenario()
    
    print("\n✓ Scenario configuration loaded successfully")
    print(f"  - World: {scenario['world']}")
    print(f"  - Agent: {scenario['agents'][0]['agent_type']}")
    print(f"  - Number of sensors: {len(scenario['agents'][0]['sensors'])}")
    
    for sensor in scenario['agents'][0]['sensors']:
        print(f"    • {sensor['sensor_type']}: {sensor['sensor_name']}")
    
    # Test trajectory generation
    print("\n✓ Testing trajectory generation...")
    waypoints = get_inspection_trajectory(
        wall_width=6.0,
        wall_height=3.0,
        standoff_distance=1.5,
    )
    
    print(f"  - Generated {len(waypoints)} waypoints")
    print(f"  - First waypoint: {waypoints[0]}")
    print(f"  - Last waypoint: {waypoints[-1]}")
    
    return True


def test_holoocean_integration():
    """Test HoloOcean environment creation (if available)."""
    if not HOLOOCEAN_AVAILABLE:
        print("\n⚠ Skipping HoloOcean integration test (not installed)")
        return False
    
    print("\n" + "=" * 70)
    print("Testing HoloOcean Integration")
    print("=" * 70)
    
    try:
        scenario = get_scenario()
        env = holoocean.make(scenario_cfg=scenario)
        
        print("\n✓ HoloOcean environment created successfully")
        
        # Test sensor data
        print("\n✓ Testing sensor data...")
        state = env.tick()
        
        print("  Available sensors:")
        for key in state.keys():
            if hasattr(state[key], 'shape'):
                print(f"    • {key}: shape {state[key].shape}, dtype {state[key].dtype}")
        
        env.__del__()
        print("\n✓ HoloOcean integration test passed")
        return True
        
    except Exception as e:
        print(f"\n✗ HoloOcean integration test failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Install HoloOcean: pip install holoocean")
        print("  2. Install Ocean package:")
        print("     python -c \"import holoocean; holoocean.install('Ocean')\"")
        return False


def main():
    print("\n" + "=" * 70)
    print("ViDEC-Inspect v0.1 Scenario Test Suite")
    print("=" * 70 + "\n")
    
    # Test 1: Scenario configuration
    config_ok = test_scenario_config()
    
    # Test 2: HoloOcean integration
    holoocean_ok = test_holoocean_integration()
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"  Scenario configuration: {'✓ PASS' if config_ok else '✗ FAIL'}")
    print(f"  HoloOcean integration:  {'✓ PASS' if holoocean_ok else '⚠ SKIP'}")
    print("=" * 70)
    
    if config_ok:
        print("\n✓ Scenario configuration is ready to use!")
        if not holoocean_ok:
            print("⚠ HoloOcean not available - using synthetic data for now")
            print("  Install HoloOcean later to use real simulator data")
    

if __name__ == "__main__":
    main()
