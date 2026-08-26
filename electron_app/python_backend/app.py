from fastapi import FastAPI
from pydantic import BaseModel
import json, pathlib

app = FastAPI(title="Kruboo Settings Service")
DATA_FILE = pathlib.Path(__file__).with_name('config.json')

class Settings(BaseModel):
    volume: int = 50
    theme: str = "light"
    notifications: bool = True

def _load() -> Settings:
    if DATA_FILE.exists():
        return Settings(**json.loads(DATA_FILE.read_text()))
    return Settings()

def _save(settings: Settings):
    DATA_FILE.write_text(settings.json(indent=2))

@app.get("/api/settings", response_model=Settings)
def get_settings():
    return _load()

@app.put("/api/settings", response_model=Settings)
def update_settings(new: Settings):
    _save(new)
    return new
