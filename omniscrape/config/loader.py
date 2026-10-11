"""Loader for scraper configuration files with YAML, JSON, and environment variable expansion."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
import yaml

from omniscrape.config.models import ScraperConfig

ENV_PATTERN = re.compile(r"\$\{([A-Za-z0-9_]+)(?::([^}]*))?\}")


def _expand_env_vars(content: str) -> str:
    """Replace ${VAR} or ${VAR:default} placeholders with environment variables."""
    def replace(match: re.Match) -> str:
        var_name = match.group(1)
        default_val = match.group(2) if match.group(2) is not None else ""
        return os.environ.get(var_name, default_val)
    return ENV_PATTERN.sub(replace, content)


class ConfigLoader:
    """Loads and validates ScraperConfig from various sources."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScraperConfig:
        """Create ScraperConfig from a raw Python dictionary."""
        return ScraperConfig.model_validate(data)

    @classmethod
    def from_yaml_string(cls, yaml_str: str) -> ScraperConfig:
        """Create ScraperConfig from a YAML string with env variable interpolation."""
        expanded = _expand_env_vars(yaml_str)
        data = yaml.safe_load(expanded) or {}
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, file_path: str | Path) -> ScraperConfig:
        """Load ScraperConfig from a YAML (.yaml, .yml) or JSON (.json) file."""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Configuration file not found: {path.resolve()}")

        raw_content = path.read_text(encoding="utf-8")
        expanded = _expand_env_vars(raw_content)

        if path.suffix.lower() in (".yaml", ".yml"):
            data = yaml.safe_load(expanded) or {}
        elif path.suffix.lower() == ".json":
            import json
            data = json.loads(expanded)
        else:
            # Fall back to yaml parser
            data = yaml.safe_load(expanded) or {}

        return cls.from_dict(data)
