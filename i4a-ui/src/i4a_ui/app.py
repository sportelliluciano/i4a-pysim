import os
from fastapi import FastAPI
from pathlib import Path

from i4a_ui.services.events.service import NodeEventsService


def create_app():
    basedir = Path(__file__).resolve().parent
    new_app = FastAPI()
    new_app.state.assets_dir = os.environ.get("ASSETS_DIR", basedir / "assets")
    new_app.state.pysim_url = os.environ.get("PYSIM_URL", "http://pysim:8080")
    new_app.state.events_service = NodeEventsService(new_app.state.pysim_url)
    return new_app


app = create_app()
