# Config loader for the pipeline
from pathlib import Path
from typing import Any, Dict

import yaml
from pydantic import BaseModel


class PipelineConfig(BaseModel):
    """Configuration model for the entire pipeline."""

    # Will be loaded from YAML at runtime
    model_config = {"extra": "allow"}


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "settings.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    return config


def get_config() -> Dict[str, Any]:
    """Get the global pipeline configuration (singleton)."""
    return load_config()
