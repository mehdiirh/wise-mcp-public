import re
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WISE_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    mcp_signing_secret: SecretStr
    api_base_url: str = "https://api.wise.ad/api"
    timeout_seconds: float = Field(default=30, gt=0, le=120)
    max_response_bytes: int = Field(default=4_194_304, ge=1024, le=33_554_432)
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]"]

    @field_validator("mcp_signing_secret")
    @classmethod
    def validate_signing_secret(cls, value: SecretStr) -> SecretStr:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value.get_secret_value()):
            raise ValueError("WISE_MCP_SIGNING_SECRET must contain 64 hexadecimal characters")
        return value

    @field_validator("api_base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
            or url.query
            or url.fragment
        ):
            raise ValueError("Use an HTTP(S) API root without credentials, query, or fragment")
        if url.scheme == "http" and url.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise ValueError("HTTPS is required except for loopback development backends")
        return value.rstrip("/")
