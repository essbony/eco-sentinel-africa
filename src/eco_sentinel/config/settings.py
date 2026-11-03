"""Configuration centralisée Eco Sentinel Africa (12-factor) — Meta API unifiée."""

import os
from functools import lru_cache

try:
    from pydantic import AliasChoices, Field, computed_field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    class Settings(BaseSettings):
        """Settings applicatifs chargés depuis l'environnement / .env (avec pydantic)."""

        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            populate_by_name=True,
        )

        app_name: str = Field(
            default="eco-sentinel-africa", validation_alias=AliasChoices("APP_NAME", "app_name")
        )
        env: str = Field(default="development", validation_alias=AliasChoices("ENV", "env"))
        debug: bool = Field(default=True, validation_alias=AliasChoices("DEBUG", "debug"))
        log_level: str = Field(
            default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "log_level")
        )
        api_host: str = Field(
            default="0.0.0.0"  # nosec B104  # noqa: S104, validation_alias=AliasChoices("API_HOST", "api_host")
        )
        api_port: int = Field(default=8000, validation_alias=AliasChoices("API_PORT", "api_port"))
        secret_key: str = Field(
            default="change-me-in-production",
            validation_alias=AliasChoices("SECRET_KEY", "secret_key"),
        )

        # ── Meta API unifiée (source unique) ──
        model_api_key: str = Field(
            default="",
            validation_alias=AliasChoices(
                "MODEL_API_KEY", "model_api_key", "OPENAI_API_KEY", "openai_api_key"
            ),
        )
        base_url: str = Field(
            default="https://api.meta.ai/v1",
            validation_alias=AliasChoices(
                "BASE_URL", "base_url", "OPENAI_BASE_URL", "OPENAI_ENDPOINT"
            ),
        )

        # ── Vision (Meta SAM 3.1) ──
        vision_provider: str = Field(
            default="meta", validation_alias=AliasChoices("VISION_PROVIDER", "vision_provider")
        )
        vision_model: str = Field(
            default="sam-3.1", validation_alias=AliasChoices("VISION_MODEL", "vision_model")
        )
        vision_timeout_s: float = Field(default=10.0)
        vision_categories: str = Field(default="waste,plastic_bottle,container,debris,dumping")
        vision_confidence_threshold: float = Field(default=0.5)

        # ── Router (Meta Muse Wonder) ──
        router_provider: str = Field(
            default="meta", validation_alias=AliasChoices("ROUTER_PROVIDER", "router_provider")
        )
        router_model: str = Field(
            default="muse-wonder-1.0", validation_alias=AliasChoices("ROUTER_MODEL", "router_model")
        )
        router_timeout_s: float = Field(default=15.0)

        # ── Agents spécialisés (Meta Muse Spark 1.3) ──
        spark_provider: str = Field(
            default="meta", validation_alias=AliasChoices("SPARK_PROVIDER", "spark_provider")
        )
        spark_model: str = Field(
            default="muse-spark-1.3", validation_alias=AliasChoices("SPARK_MODEL", "spark_model")
        )
        spark_timeout_s: float = Field(default=15.0)

        # ── Analyse (compat — utilise Meta si disponible) ──
        openai_api_key: str = Field(
            default="", validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key")
        )
        openai_model: str = Field(
            default="muse-spark-1.3", validation_alias=AliasChoices("OPENAI_MODEL", "openai_model")
        )
        openai_timeout_s: float = Field(default=20.0)

        # ── Ingestion vidéo ──
        ingestion_max_queue_size: int = Field(default=100)
        ingestion_sample_fps: float = Field(default=1.0)
        ingestion_max_image_bytes: int = Field(default=5_000_000)
        ingestion_allowed_sources: str = Field(default="*")

        # ── Événements / Alertes ──
        event_dedup_window_s: int = Field(default=5)
        event_persistence_threshold: int = Field(default=1)
        alert_min_risk: str = Field(default="medium")
        alert_min_confidence: float = Field(default=0.6)

        # ── Persistance ──
        database_url: str = Field(default="")

        # ── CORS (prod) ──
        cors_origins: str = Field(
            default="",
            validation_alias=AliasChoices("CORS_ORIGINS", "cors_origins"),
        )

        @property
        def cors_origins_list(self) -> list[str]:
            if not self.cors_origins.strip():
                return []
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

        # ── A2A ──
        a2a_enabled: bool = Field(default=True)
        a2a_timeout_s: float = Field(default=10.0)

        # ── Évaluation ──
        eval_target_url: str = Field(default="http://localhost:8000")
        eval_dataset: str = Field(default="evals/datasets/golden.jsonl")

        @computed_field  # type: ignore[misc]
        @property
        def effective_api_key(self) -> str:
            """Clé effective : MODEL_API_KEY prioritaire, fallback OPENAI_API_KEY."""
            if self.model_api_key:
                return self.model_api_key
            return self.openai_api_key

        @computed_field  # type: ignore[misc]
        @property
        def effective_base_url(self) -> str:
            """BASE_URL normalisée avec /v1."""
            url = (self.base_url or "https://api.meta.ai/v1").strip().rstrip("/")
            if not url.endswith("/v1"):
                url = url + "/v1"
            return url

        def is_meta_configured(self) -> bool:
            return bool(self.effective_api_key and self.effective_base_url)

        def provider_is_meta(self, provider: str) -> bool:
            return provider.strip().lower() == "meta" and self.is_meta_configured()

except ImportError:
    from dataclasses import dataclass

    def Field(default=None, **kwargs):  # type: ignore[no-redef]
        return default

    @dataclass
    class Settings:  # type: ignore[no-redef]
        app_name: str = os.getenv("APP_NAME", "eco-sentinel-africa")
        env: str = os.getenv("ENV", "development")
        debug: bool = os.getenv("DEBUG", "true").lower() in ("1", "true", "yes")
        log_level: str = os.getenv("LOG_LEVEL", "INFO")
        api_host: str = os.getenv("API_HOST", "0.0.0.0")  # nosec B104  # noqa: S104
        api_port: int = int(os.getenv("API_PORT", "8000"))
        secret_key: str = os.getenv("SECRET_KEY", "change-me-in-production")
        model_api_key: str = os.getenv("MODEL_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
        base_url: str = os.getenv("BASE_URL", "https://api.meta.ai/v1") or os.getenv(
            "OPENAI_BASE_URL", "https://api.meta.ai/v1"
        )
        vision_provider: str = os.getenv("VISION_PROVIDER", "meta")
        vision_model: str = os.getenv("VISION_MODEL", "sam-3.1")
        router_provider: str = os.getenv("ROUTER_PROVIDER", "meta")
        router_model: str = os.getenv("ROUTER_MODEL", "muse-wonder-1.0")
        spark_provider: str = os.getenv("SPARK_PROVIDER", "meta")
        spark_model: str = os.getenv("SPARK_MODEL", "muse-spark-1.3")
        openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
        openai_model: str = os.getenv("OPENAI_MODEL", "muse-spark-1.3")
        ingestion_max_queue_size: int = int(os.getenv("INGESTION_MAX_QUEUE_SIZE", "100"))
        ingestion_sample_fps: float = float(os.getenv("INGESTION_SAMPLE_FPS", "1.0"))
        ingestion_max_image_bytes: int = int(os.getenv("INGESTION_MAX_IMAGE_BYTES", "5000000"))
        event_dedup_window_s: int = int(os.getenv("EVENT_DEDUP_WINDOW_S", "60"))
        alert_min_risk: str = os.getenv("ALERT_MIN_RISK", "medium")
        database_url: str = os.getenv("DATABASE_URL", "")
        cors_origins: str = os.getenv("CORS_ORIGINS", "")

        @property
        def cors_origins_list(self) -> list[str]:
            if not self.cors_origins.strip():
                return []
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

        @property
        def effective_api_key(self) -> str:
            return self.model_api_key or self.openai_api_key

        @property
        def effective_base_url(self) -> str:
            url = (self.base_url or "https://api.meta.ai/v1").strip().rstrip("/")
            if not url.endswith("/v1"):
                url += "/v1"
            return url

        def is_meta_configured(self) -> bool:
            return bool(self.effective_api_key and self.effective_base_url)

        def provider_is_meta(self, provider: str) -> bool:
            return provider.strip().lower() == "meta" and self.is_meta_configured()

        def __post_init__(self):
            # Normalise base_url
            url = (self.base_url or "https://api.meta.ai/v1").strip().rstrip("/")
            if not url.endswith("/v1"):
                url += "/v1"
            self.base_url = url
            # Fallback si model_api_key vide mais openai_api_key présent
            if not self.model_api_key and self.openai_api_key:
                self.model_api_key = self.openai_api_key
            # Normalise providers vides -> mock
            if not self.spark_provider or not self.spark_provider.strip():
                self.spark_provider = "mock"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
