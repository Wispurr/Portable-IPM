from pydantic import BaseModel, Field
from typing import Literal
import json


class Config(BaseModel):
    host: Literal["0.0.0.0"] = Field(default="0.0.0.0")
    port: Literal[8080] = Field(default=8080, ge=1, le=65535)


try:
    CONFIG = Config.model_validate_json(open("config.json", encoding="utf-8").read())
except:
    CONFIG = Config()

with open("config.json", mode="w", encoding="utf-8") as f:
    json.dump(CONFIG.model_dump(), f, indent=2, ensure_ascii=False)
