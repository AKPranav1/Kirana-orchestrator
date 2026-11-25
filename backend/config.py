"""One configuration boundary. Provider credentials remain server-side."""
import os
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    environment: Literal["development", "production"] = "development"
    mongo_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    database: str = "kirana_ai"
    store_id: str = "store_001"
    api_token: str = ""
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])
    notifications_enabled: bool = False
    demo_mode: bool = False
    max_pool_size: int = Field(50, ge=1, le=500)
    operation_timeout: int = Field(15, ge=1, le=60)

    @model_validator(mode="after")
    def production_configuration(self):
        if self.environment == "production" and (len(self.api_token) < 32 or "*" in self.allowed_origins or self.demo_mode):
            raise ValueError("Production requires a 32+ character operator token, explicit origins and demo mode disabled")
        return self

    @classmethod
    def from_env(cls):
        load_dotenv(ROOT / ".env")
        return cls(environment=os.getenv("KIRANA_ENV", "development"), mongo_uri=os.getenv("MONGO_URI", cls.model_fields["mongo_uri"].default),
                   database=os.getenv("MONGO_DB_NAME", "kirana_ai"), store_id=os.getenv("STORE_ID", "store_001"),
                   api_token=os.getenv("KIRANA_API_TOKEN", ""), notifications_enabled=os.getenv("NOTIFICATIONS_ENABLED", "false").lower() == "true",
                   demo_mode=os.getenv("KIRANA_DEMO_MODE", "false").lower() == "true",
                   allowed_origins=[v.strip() for v in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if v.strip()],
                   max_pool_size=int(os.getenv("MONGO_MAX_POOL_SIZE", "50")),
                   operation_timeout=int(os.getenv("MONGO_OPERATION_TIMEOUT", "15")))
