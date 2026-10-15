"""Platform settings loaded from environment variables (and optional .env).

Secrets are declared as ``SecretStr`` and never logged. Every path is
resolvable without credentials so scoring/corpus features work offline.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SEED = 20260929  # matches the research freeze


class Settings(BaseSettings):
    """Environment-driven configuration; see platform/.env.example."""

    model_config = SettingsConfigDict(
        env_prefix="MASLD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        secrets_dir=None,
    )

    # NOTE: credentials carry no prefix (industry-standard names).
    openrouter_api_key: SecretStr | None = Field(None, alias="OPENROUTER_API_KEY")
    huggingface_token: SecretStr | None = Field(None, alias="HUGGINGFACE_TOKEN")
    ngrok_authtoken: SecretStr | None = Field(None, alias="NGROK_AUTHTOKEN")

    root: Path = Field(default=Path(__file__).resolve().parents[3])
    data_dir: Path = Path("data")  # resolved relative to the platform dir in __init__
    db_url: str = ""
    seed: int = _DEFAULT_SEED
    #: Benchmark profile (domain vocabulary); see profiles/*.yaml.
    profile: Path = Field(
        default=Path(__file__).resolve().parents[2] / "profiles" / "masld.yaml",
        alias="MASLD_PROFILE",
    )

    drive_sync_dir: Path | None = Field(None, alias="DRIVE_SYNC_DIR")
    google_credentials: Path | None = Field(None, alias="GOOGLE_APPLICATION_CREDENTIALS")

    device: str = ""  # "", "cpu", "mps", "cuda"

    def resolved_data_dir(self) -> Path:
        """Data dir; relative paths anchor to the platform directory."""
        p = self.data_dir
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / p
        p.mkdir(parents=True, exist_ok=True)
        return p

    def resolved_db_url(self) -> str:
        if self.db_url:
            return self.db_url
        return f"sqlite:///{self.resolved_data_dir() / 'masld.db'}"

    def prompts_dir(self) -> Path:
        return self.root / "prompts"

    def archives_dir(self) -> Path:
        return self.root / "results" / "frontier_runs"

    def bridge_dir(self) -> Path:
        base = self.drive_sync_dir
        if base is None:
            raise ValueError("DRIVE_SYNC_DIR is not configured")
        d = Path(base) / "masld-bridge"
        d.mkdir(parents=True, exist_ok=True)
        return d


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide cached settings (tests call ``get_settings.cache_clear()``)."""
    return Settings()
