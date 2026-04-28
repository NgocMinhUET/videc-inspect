SCENARIO_CFG = {
    "name": "ViDECInspect_HoloOcean_Smoke",
    "world": "PierHarbor",
    "package_name": "Ocean",
    "main_agent": "auv0",
    "ticks_per_sec": 30,
    "agents": [
        {
            "agent_name": "auv0",
            "agent_type": "HoveringAUV",
            "control_scheme": 0,
            "location": [0.0, 0.0, -5.0],
            "rotation": [0.0, 0.0, 0.0],
            "sensors": [
                {
                    "sensor_type": "RGBCamera",
                    "sensor_name": "FrontRGB",
                    "socket": "CameraRightSocket",
                    "Hz": 5,
                    "configuration": {
                        "CaptureWidth": 640,
                        "CaptureHeight": 480
                    }
                },
                {
                    "sensor_type": "DepthCamera",
                    "sensor_name": "FrontDepth",
                    "socket": "CameraLeftSocket",
                    "Hz": 5,
                    "configuration": {
                        "CaptureWidth": 640,
                        "CaptureHeight": 480
                    }
                }
            ]
        }
    ]
}
