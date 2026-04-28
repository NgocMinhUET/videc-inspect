"""
Minimal HoloOcean scenario for smoke testing ViDEC-Inspect integration.

This scenario provides:
- Simple underwater environment
- AUV agent with front RGB and Depth cameras
- Flat wall target for inspection

Usage:
    from configs.scenarios.holoocean_smoke_flatwall import SCENARIO_CFG
"""

SCENARIO_CFG = {
    "name": "FlatWallInspection",
    "package_name": "Ocean",
    "world": "SimpleUnderwater",
    "main_agent": "auv0",
    "ticks_per_sec": 30,
    "agents": [
        {
            "agent_name": "auv0",
            "agent_type": "HoveringAUV",
            "sensors": [
                {
                    "sensor_type": "RGBCamera",
                    "sensor_name": "FrontRGB",
                    "configuration": {
                        "CaptureWidth": 1920,
                        "CaptureHeight": 1080,
                        "FOV": 90.0,
                    },
                    "location": [0.5, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                },
                {
                    "sensor_type": "DepthCamera",
                    "sensor_name": "FrontDepth",
                    "configuration": {
                        "CaptureWidth": 1920,
                        "CaptureHeight": 1080,
                        "FOV": 90.0,
                    },
                    "location": [0.5, 0.0, 0.0],
                    "rotation": [0.0, 0.0, 0.0],
                },
            ],
            "control_scheme": 0,
            "location": [0.0, 0.0, -5.0],
            "rotation": [0.0, 0.0, 0.0],
        }
    ],
}
