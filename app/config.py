# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class AppConfig(BaseSettings):
    """
    Application configuration model.
    Loads settings from environment variables.
    Pydantic-settings will automatically attempt to load from an .env file
    if `python-dotenv` is installed and the env_file is specified.
    """
    # GitHub API Configuration
    GITHUB_TOKEN: str  # No default, must be set in environment
    GITHUB_REPO_OWNER: str  # No default, must be set in environment
    GITHUB_REPO_NAME: str  # No default, must be set in environment
    GITHUB_FILE_PATH: str = "prompt_manifest.json"  # Default path for the committed file
    GITHUB_BRANCH: str = "main"  # Default branch to commit to

    # Pydantic-settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",  # Specifies the .env file to load variables from
        env_file_encoding='utf-8',  # Encoding of the .env file
        extra='ignore'  # Ignore extra fields in the environment that are not defined in the model
    )

# Create a single, importable instance of the configuration settings.
# This instance will be populated when this module is first imported.
# If required environment variables (like GITHUB_TOKEN) are missing,
# Pydantic will raise a ValidationError.
settings = AppConfig()
