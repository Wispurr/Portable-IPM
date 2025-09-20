# config.py: Configuration for the FastAPI application

from pydantic import BaseModel, Field
from typing import Literal
import json
import os

# Define the configuration model using Pydantic
class Config(BaseModel):
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8080, ge=1, le=65535)
    debug: bool = Field(default=True, description="Enable debug mode for development")
    UPLOAD_FOLDER: str = Field(default="./uploads")

# Attempt to load the configuration from a JSON file, or create a default one if it doesn't exist
config_path = "config.json"
if os.path.exists(config_path):
    with open(config_path, encoding="utf-8") as f:
        CONFIG = Config.model_validate_json(f.read())
else:
    CONFIG = Config()
    with open(config_path, mode="w", encoding="utf-8") as f:
        json.dump(CONFIG.model_dump(), f, indent=2, ensure_ascii=False)