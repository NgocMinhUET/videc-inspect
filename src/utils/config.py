"""
Centralized configuration management for ViDEC-Inspect.

Loads and provides access to benchmark-wide settings including:
- Severity thresholds
- Taxonomy
- Camera parameters
- Verification requirements
"""

import yaml
from pathlib import Path
from typing import Dict, Any


class BenchmarkConfig:
    """Centralized benchmark configuration."""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self.load_config()
    
    def load_config(self, config_path: str = None):
        """Load benchmark configuration from YAML."""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "configs" / "benchmark_config.yaml"
        
        with open(config_path, 'r') as f:
            self._config = yaml.safe_load(f)
    
    @property
    def benchmark_name(self) -> str:
        return self._config['benchmark']['name']
    
    @property
    def benchmark_version(self) -> str:
        return self._config['benchmark']['version']
    
    @property
    def full_name(self) -> str:
        return self._config['benchmark']['full_name']
    
    def get_severity_thresholds(self, defect_class: str) -> Dict:
        """Get severity thresholds for a defect class."""
        return self._config['severity_thresholds'].get(defect_class, {})
    
    def classify_severity(self, defect_class: str, measurement: float) -> str:
        """
        Classify severity based on measurement.
        
        Args:
            defect_class: "crack" or "spall"
            measurement: width_mm for crack, depth_mm for spall
            
        Returns:
            severity: "minor", "moderate", or "severe"
        """
        thresholds = self.get_severity_thresholds(defect_class)
        
        if defect_class == "crack":
            # Based on width
            if measurement < thresholds['minor']['max_width_mm']:
                return "minor"
            elif measurement < thresholds['moderate']['max_width_mm']:
                return "moderate"
            else:
                return "severe"
        
        elif defect_class == "spall":
            # Based on depth
            if measurement < thresholds['minor']['max_depth_mm']:
                return "minor"
            elif measurement < thresholds['moderate']['max_depth_mm']:
                return "moderate"
            else:
                return "severe"
        
        else:
            return "unknown"
    
    def get_defect_classes(self) -> list:
        """Get list of defect classes."""
        return self._config['taxonomy']['defect_classes']
    
    def get_hard_negative_types(self) -> list:
        """Get list of hard negative types."""
        return self._config['taxonomy']['hard_negative_types']
    
    def get_verification_requirements(self, defect_class: str) -> Dict:
        """Get verification requirements for a defect class."""
        return self._config['verification'].get(defect_class, {})
    
    def get_camera_params(self) -> Dict:
        """Get camera parameters."""
        return self._config['camera']
    
    def get_config(self) -> Dict[str, Any]:
        """Get full configuration dictionary."""
        return self._config


# Singleton instance
benchmark_config = BenchmarkConfig()
