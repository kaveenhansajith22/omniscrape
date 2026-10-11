import os
import pytest
from omniscrape.config.loader import ConfigLoader
from omniscrape.config.models import EngineType, PaginationType


def test_config_from_dict():
    data = {
        "name": "test_scraper",
        "start_urls": "https://example.com",
        "item": {
            "container_selector": ".card",
            "fields": {
                "title": {"selector": "h1", "extract": "text"}
            }
        }
    }
    config = ConfigLoader.from_dict(data)
    assert config.name == "test_scraper"
    assert config.start_urls == ["https://example.com"]
    assert config.engine == EngineType.STATIC
    assert "title" in config.item.fields


def test_config_env_var_interpolation():
    os.environ["TEST_TARGET_URL"] = "https://example.org/catalog"
    yaml_content = """
    name: "env_scraper"
    start_urls:
      - "${TEST_TARGET_URL}"
    item:
      container_selector: ".item"
    pagination:
      type: "next_button"
      selector: "a.next"
    """
    config = ConfigLoader.from_yaml_string(yaml_content)
    assert config.start_urls == ["https://example.org/catalog"]
    assert config.pagination.type == PaginationType.NEXT_BUTTON
