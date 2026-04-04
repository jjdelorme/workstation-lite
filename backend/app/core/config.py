import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    gcp_project_id: Optional[str] = os.environ.get("GOOGLE_CLOUD_PROJECT")
    region: str = "us-central1"
    cluster_name: str = "workstation-cluster"
    workstation_image: str = "gitpod/openvscode-server:latest"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.gcp_project_id:
            try:
                import google.auth
                _, project = google.auth.default()
                if project:
                    self.gcp_project_id = project
            except Exception:
                pass

settings = Settings()
