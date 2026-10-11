"""Data cleaning and transformation pipeline for parsed values."""
from __future__ import annotations

import html
import re
from typing import Any, Callable
from urllib.parse import urljoin


class TransformRegistry:
    """Registry for string and value transformation functions."""
    _transforms: dict[str, Callable[..., Any]] = {}

    @classmethod
    def register(cls, name: str) -> Callable:
        """Decorator to register a custom transformation function."""
        def decorator(func: Callable) -> Callable:
            cls._transforms[name] = func
            return func
        return decorator

    @classmethod
    def get(cls, name: str) -> Callable[..., Any] | None:
        return cls._transforms.get(name)


@TransformRegistry.register("strip")
def transform_strip(value: Any, **_: Any) -> Any:
    if isinstance(value, str):
        # Collapse multiple whitespace and newlines
        return " ".join(value.split())
    if isinstance(value, list):
        return [transform_strip(v) for v in value]
    return value


@TransformRegistry.register("lowercase")
def transform_lowercase(value: Any, **_: Any) -> Any:
    if isinstance(value, str):
        return value.lower()
    if isinstance(value, list):
        return [transform_lowercase(v) for v in value]
    return value


@TransformRegistry.register("uppercase")
def transform_uppercase(value: Any, **_: Any) -> Any:
    if isinstance(value, str):
        return value.upper()
    if isinstance(value, list):
        return [transform_uppercase(v) for v in value]
    return value


@TransformRegistry.register("html_unescape")
def transform_html_unescape(value: Any, **_: Any) -> Any:
    if isinstance(value, str):
        return html.unescape(value)
    if isinstance(value, list):
        return [transform_html_unescape(v) for v in value]
    return value


@TransformRegistry.register("to_int")
def transform_to_int(value: Any, **_: Any) -> int | None:
    if value is None or isinstance(value, (int, float)):
        return int(value) if value is not None else None
    s = str(value)
    # Match integer sequence, ignoring commas
    cleaned = s.replace(",", "")
    match = re.search(r"[-+]?\d+", cleaned)
    if match:
        try:
            return int(match.group(0))
        except ValueError:
            return None
    return None


@TransformRegistry.register("to_float")
def transform_to_float(value: Any, **_: Any) -> float | None:
    if value is None or isinstance(value, (int, float)):
        return float(value) if value is not None else None
    s = str(value)
    # Remove currency symbols and comma separators
    cleaned = s.replace(",", "")
    match = re.search(r"[-+]?\d+(?:\.\d+)?", cleaned)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None


@TransformRegistry.register("resolve_url")
def transform_resolve_url(value: Any, base_url: str = "", **_: Any) -> Any:
    if isinstance(value, str) and base_url:
        return urljoin(base_url, value.strip())
    if isinstance(value, list) and base_url:
        return [urljoin(base_url, v.strip()) if isinstance(v, str) else v for v in value]
    return value


def apply_transforms(
    value: Any,
    transforms: list[str],
    base_url: str = "",
) -> Any:
    """Applies a chain of named transformations to an extracted value."""
    current = value
    for transform_spec in transforms:
        if current is None:
            break

        # Check for parameterized transform (e.g., "join:, ", "regex_replace:pattern:replace")
        parts = transform_spec.split(":", 1)
        name = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        if name == "join":
            delimiter = arg if arg is not None else ", "
            if isinstance(current, list):
                current = delimiter.join(str(item) for item in current if item is not None)
        elif name == "first":
            if isinstance(current, list) and len(current) > 0:
                current = current[0]
        elif name == "split":
            delimiter = arg if arg is not None else " "
            if isinstance(current, str):
                current = current.split(delimiter)
        elif name == "regex_search":
            pattern = arg or ""
            if isinstance(current, str):
                m = re.search(pattern, current)
                current = m.group(1) if (m and m.groups()) else (m.group(0) if m else None)
        elif name == "regex_replace":
            # format: regex_replace:from_pattern:to_pattern
            if arg and ":" in arg:
                sub_parts = arg.split(":", 1)
                pattern, repl = sub_parts[0], sub_parts[1]
                if isinstance(current, str):
                    current = re.sub(pattern, repl, current)
        elif name == "default":
            if current is None or (isinstance(current, str) and not current.strip()):
                current = arg
        else:
            func = TransformRegistry.get(name)
            if func:
                current = func(current, base_url=base_url)

    return current
