from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    kapruka_mcp_url: str = Field(
        default="https://mcp.kapruka.com/mcp",
        alias="KAPRUKA_MCP_URL",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
