"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).with_name(".env"))


@dataclass(frozen=True)
class Settings:
    subscription_id: str
    resource_group: str
    vm_name: str
    environment: str
    allowed_environments: tuple[str, ...]
    frontend_origin: str

    @classmethod
    def from_environment(cls) -> "Settings":
        allowed = tuple(
            value.strip().upper()
            for value in os.getenv("ALLOWED_ENVIRONMENTS", "DEV,TEST").split(",")
            if value.strip()
        )
        environment = os.getenv("AZURE_ENVIRONMENT", "DEV").strip().upper()
        return cls(
            subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", "").strip(),
            resource_group=os.getenv("AZURE_RESOURCE_GROUP", "").strip(),
            vm_name=os.getenv("AZURE_VM_NAME", "").strip(),
            environment=environment,
            allowed_environments=allowed,
            frontend_origin=os.getenv("FRONTEND_ORIGIN", "http://localhost:5500").strip(),
        )

    def validate(self) -> None:
        missing = [
            name
            for name, value in (
                ("AZURE_SUBSCRIPTION_ID", self.subscription_id),
                ("AZURE_RESOURCE_GROUP", self.resource_group),
                ("AZURE_VM_NAME", self.vm_name),
            )
            if not value
        ]
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        if self.environment not in self.allowed_environments:
            raise ValueError(
                f"Environment '{self.environment}' is not allowed. "
                f"Allowed environments: {', '.join(self.allowed_environments)}"
            )
        if self.environment not in {"DEV", "TEST"}:
            raise ValueError("Only DEV and TEST environments may be controlled by this application")


settings = Settings.from_environment()
