"""
HoloOcean Scenario for ViDEC-Inspect v0.1
Flat Wall Inspection with RGB + Depth + IMU + DVL

This scenario creates a minimal inspection setup:
- HoveringAUV robot
- RGB camera (1920x1080, 5Hz)
- Depth camera (1920x1080, 5Hz)
- IMU (30Hz)
- DVL (10Hz)

Usage:
    import holoocean
    from configs.scenarios.flat_wall_rgbd_v01 import get_scenario
    
    scenario = get_scenario()
    env = holoocean.make(scenario_cfg=scenario)
"""

import numpy as np


def get_scenario(
    world="SimpleUnderwater",
    camera_resolution=(1920, 1080),
    camera_hz=5,
    depth_hz=5,
    imu_hz=30,
    dvl_hz=10,
    ticks_per_sec=30,
):
    """
    Generate HoloOcean scenario configuration for flat wall inspection.
    
    Args:
        world: HoloOcean world name
        camera_resolution: (width, height) for RGB and depth cameras
        camera_hz: RGB camera capture rate
        depth_hz: Depth camera capture rate
        imu_hz: IMU sensor rate
        dvl_hz: DVL sensor rate
        ticks_per_sec: Simulation ticks per second
        
    Returns:
        scenario_cfg: Dictionary for holoocean.make(scenario_cfg=...)
    """
    
    scenario = {
        "name": "FlatWallInspection_v01",
        "world": world,
        "package_name": "Ocean",
        "ticks_per_sec": ticks_per_sec,
        
        "agents": [
            {
                "agent_name": "auv0",
                "agent_type": "HoveringAUV",
                
                # Initial pose: 2m in front of wall, centered
                "sensors": [
                    {
                        "sensor_type": "RGBCamera",
                        "sensor_name": "FrontCamera",
                        "configuration": {
                            "CaptureWidth": camera_resolution[0],
                            "CaptureHeight": camera_resolution[1],
                            "TicksPerCapture": ticks_per_sec // camera_hz if camera_hz > 0 else ticks_per_sec,
                        },
                        "location": [0.3, 0.0, 0.0],  # Slightly forward from center
                        "rotation": [0, 0, 0],
                    },
                    {
                        "sensor_type": "DepthCamera",
                        "sensor_name": "FrontDepth",
                        "configuration": {
                            "CaptureWidth": camera_resolution[0],
                            "CaptureHeight": camera_resolution[1],
                            "TicksPerCapture": ticks_per_sec // depth_hz if depth_hz > 0 else ticks_per_sec,
                        },
                        "location": [0.3, 0.0, 0.0],
                        "rotation": [0, 0, 0],
                    },
                    {
                        "sensor_type": "IMUSensor",
                        "sensor_name": "IMU",
                        "configuration": {
                            "TicksPerCapture": ticks_per_sec // imu_hz if imu_hz > 0 else 1,
                        },
                    },
                    {
                        "sensor_type": "DVLSensor",
                        "sensor_name": "DVL",
                        "configuration": {
                            "TicksPerCapture": ticks_per_sec // dvl_hz if dvl_hz > 0 else 3,
                            "Range": 10.0,  # 10m range
                        },
                    },
                ],
                
                "control_scheme": 0,  # Direct force control
                "location": [0, 0, -2],  # Start at 2m depth
                "rotation": [0, 0, 0],
            }
        ],
        
        # Simple environment settings
        "window_width": 1280,
        "window_height": 720,
    }
    
    return scenario


def get_inspection_trajectory(
    wall_width=6.0,
    wall_height=3.0,
    standoff_distance=1.5,
    horizontal_overlap=0.3,
    vertical_overlap=0.3,
    camera_fov_deg=90,
):
    """
    Generate lawnmower survey trajectory for flat wall inspection.
    
    Args:
        wall_width: Wall width in meters
        wall_height: Wall height in meters
        standoff_distance: Distance from wall in meters
        horizontal_overlap: Overlap ratio between horizontal passes
        vertical_overlap: Overlap ratio between vertical strips
        camera_fov_deg: Camera field of view in degrees
        
    Returns:
        waypoints: List of (x, y, z, yaw) tuples in world frame
    """
    
    # Calculate coverage per frame
    fov_rad = np.deg2rad(camera_fov_deg)
    frame_width = 2 * standoff_distance * np.tan(fov_rad / 2)
    frame_height = frame_width * (9.0 / 16.0)  # Assuming 16:9 aspect ratio
    
    # Calculate strip spacing
    horizontal_step = frame_width * (1 - horizontal_overlap)
    vertical_step = frame_height * (1 - vertical_overlap)
    
    # Generate waypoints
    waypoints = []
    
    num_vertical_strips = int(np.ceil(wall_height / vertical_step))
    num_horizontal_points = int(np.ceil(wall_width / horizontal_step))
    
    for v in range(num_vertical_strips):
        z = -wall_height / 2 + v * vertical_step
        
        # Alternate direction for lawnmower pattern
        if v % 2 == 0:
            x_range = np.linspace(-wall_width / 2, wall_width / 2, num_horizontal_points)
        else:
            x_range = np.linspace(wall_width / 2, -wall_width / 2, num_horizontal_points)
        
        for x in x_range:
            # (x, y, z, yaw) where y is distance from wall
            waypoints.append((x, -standoff_distance, z, 0.0))
    
    return waypoints


def get_closeup_waypoint(defect_position, standoff_distance=0.8):
    """
    Generate close-up inspection waypoint for a detected defect.
    
    Args:
        defect_position: (x, y, z) position of defect in world frame
        standoff_distance: Close-up inspection distance in meters
        
    Returns:
        waypoint: (x, y, z, yaw) tuple
    """
    x, y, z = defect_position
    
    # Position robot closer to defect
    waypoint = (x, y - standoff_distance, z, 0.0)
    
    return waypoint


# Example usage
if __name__ == "__main__":
    import holoocean
    
    print("=" * 60)
    print("ViDEC-Inspect v0.1: HoloOcean Scenario Test")
    print("=" * 60)
    
    # Get scenario configuration
    scenario = get_scenario()
    
    print("\n[INFO] Scenario configuration generated:")
    print(f"  World: {scenario['world']}")
    print(f"  Agent: {scenario['agents'][0]['agent_type']}")
    print(f"  Sensors: {len(scenario['agents'][0]['sensors'])}")
    for sensor in scenario['agents'][0]['sensors']:
        print(f"    - {sensor['sensor_type']}: {sensor['sensor_name']}")
    
    print("\n[INFO] Attempting to create HoloOcean environment...")
    
    try:
        env = holoocean.make(scenario_cfg=scenario)
        
        print("[SUCCESS] Environment created!")
        print("\n[INFO] Running 10 ticks to test sensors...")
        
        for i in range(10):
            state = env.tick()
            
            if i == 0:
                print("\n[INFO] Available sensors in state:")
                for key in state.keys():
                    if isinstance(state[key], np.ndarray):
                        print(f"  - {key}: shape {state[key].shape}, dtype {state[key].dtype}")
        
        print("\n[SUCCESS] Sensor test completed!")
        print("\n[INFO] Generating inspection trajectory...")
        
        waypoints = get_inspection_trajectory(
            wall_width=6.0,
            wall_height=3.0,
            standoff_distance=1.5,
        )
        
        print(f"[INFO] Generated {len(waypoints)} waypoints")
        print(f"  First waypoint: {waypoints[0]}")
        print(f"  Last waypoint: {waypoints[-1]}")
        
        env.__del__()
        print("\n[SUCCESS] flat_wall_rgbd_v01.py is working correctly!")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to create environment: {e}")
        print("\nTroubleshooting:")
        print("  1. Make sure HoloOcean is installed: pip install holoocean")
        print("  2. Install Ocean package: python -c \"import holoocean; holoocean.install('Ocean')\"")
        print("  3. Check available worlds: python -c \"import holoocean; print(holoocean.packagemanager.get_worlds())\"")
