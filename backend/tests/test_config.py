import os
import pytest
from app.core.config import Settings

def test_settings_defaults():
    settings = Settings()
    # Assuming default cluster name from plan
    assert settings.cluster_name == "workstation-cluster"
    assert settings.workstation_image == "gitpod/openvscode-server:latest"
    assert settings.region == "us-central1"

def test_settings_env_override():
    os.environ["CLUSTER_NAME"] = "custom-cluster"
    settings = Settings()
    assert settings.cluster_name == "custom-cluster"
    # Cleanup
    del os.environ["CLUSTER_NAME"]
