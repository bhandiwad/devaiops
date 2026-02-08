from pathlib import Path

import pytest

from config.loader import ConfigLoader
from config.validator import SchemaValidationError


def test_load_platform_config_and_catalog():
    repo_root = Path(__file__).resolve().parents[3]
    loader = ConfigLoader(repo_root)
    store = loader.load_all()
    assert store.platform_config.modules["module_catalog_path"]
    assert store.module_catalog.modules
    assert store.provider_profiles
    assert store.tenant_specs


def test_platform_config_schema_validation(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    loader = ConfigLoader(repo_root)
    bad_config = tmp_path / "bad.yaml"
    bad_config.write_text("{}")
    with pytest.raises(SchemaValidationError):
        loader.load_platform_config(str(bad_config))
