"""
HoloOcean Smoke Test for ViDEC-Inspect

This script performs a minimal test of HoloOcean integration:
1. Initialize HoloOceanFlatWallSource
2. Capture one frame (RGB + Depth)
3. Save outputs to verify pipeline works

Usage:
    conda activate holoocean
    python scripts/run_holoocean_smoke_test.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np

from configs.scenarios.holoocean_smoke_flatwall import SCENARIO_CFG
from src.scene import HoloOceanFlatWallSource, CapturePose, CaptureConditions
from src.utils.vis import depth_to_colormap


def main():
    """Run HoloOcean smoke test."""
    print("=" * 72)
    print("HoloOcean Smoke Test")
    print("=" * 72)
    
    out_dir = Path("data/raw/holoocean_smoke")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nInitializing HoloOcean source...")
    print(f"Scenario: {SCENARIO_CFG.get('name', 'unknown')}")
    
    source = HoloOceanFlatWallSource(
        scenario_cfg=SCENARIO_CFG,
        show_viewport=False,
        disable_viewport_rendering=True,
        warmup_steps=10,
    )

    try:
        print("\nDefining capture pose...")
        pose = CapturePose(
            x_m=0.0,
            y_m=-1.5,
            z_m=-5.0,
            roll_deg=0.0,
            pitch_deg=0.0,
            yaw_deg=180.0,
            standoff_distance_m=1.5,
            view_angle_deg=0.0,
        )

        print("Defining environmental conditions...")
        conditions = CaptureConditions(
            water_clarity="moderate",
            lighting="normal",
            visibility_m=8.5,
            artificial_light=True,
            ambient_illumination_lux=300.0,
        )

        print("\nCapturing frame from HoloOcean...")
        capture = source.capture(pose=pose, conditions=conditions, seed=42)

        print("✓ Capture successful!")
        
        rgb = capture.rgb
        depth = capture.depth

        # Save outputs
        rgb_path = out_dir / "rgb.png"
        depth_npy_path = out_dir / "depth.npy"
        depth_vis_path = out_dir / "depth.png"

        print("\nSaving outputs...")
        
        # Handle RGBA or RGB
        if rgb.shape[-1] == 4:
            rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGBA2BGRA)
        else:
            rgb_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        depth_vis = depth_to_colormap(depth)

        cv2.imwrite(str(rgb_path), rgb_bgr)
        np.save(depth_npy_path, depth)
        cv2.imwrite(str(depth_vis_path), cv2.cvtColor(depth_vis, cv2.COLOR_RGB2BGR))

        print("\n" + "=" * 72)
        print("✓ Smoke test PASSED")
        print("=" * 72)
        print("\nSaved outputs:")
        print(f"  RGB:       {rgb_path}")
        print(f"  Depth NPY: {depth_npy_path}")
        print(f"  Depth VIS: {depth_vis_path}")
        print("\nCapture info:")
        print(f"  Source:          {capture.source_name}")
        print(f"  RGB shape:       {capture.rgb.shape}")
        print(f"  Depth shape:     {capture.depth.shape}")
        print(f"  Pixel-to-meter:  {capture.pixel_to_meter:.6f}")
        print(f"  Robot position:  {capture.robot_state.get('position_m', 'N/A')}")
        print(f"  Camera distance: {capture.camera_state.get('distance_to_wall_m', 'N/A')} m")
        print("=" * 72)
        
        return 0

    except Exception as e:
        print("\n" + "=" * 72)
        print("✗ Smoke test FAILED")
        print("=" * 72)
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 72)
        return 1
        
    finally:
        print("\nClosing HoloOcean environment...")
        source.close()
        print("✓ Cleanup complete")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
