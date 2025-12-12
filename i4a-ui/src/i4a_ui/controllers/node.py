import requests

from typing import Annotated
from fastapi import Path


from i4a_ui.app import app


@app.get("/nodes")
def get_nodes():
    return requests.get(f"{app.state.pysim_url}/nodes").json()


@app.get("/nodes/{node_id}/events")
def get_node_events(
    node_id: Annotated[str, Path(title="Unique ID of node")],
    stream: str,
):
    return app.state.events_service.get_events(node_id, stream=stream)


@app.get("/nodes/{node_id}/events/{device}")
def get_events(
    node_id: Annotated[str, Path(title="Unique ID of node")],
    stream: str,
    device: Annotated[str, Path(title="Device (north, east, south, west, center)")],
):
    return app.state.events_service.get_events(node_id, device=device, stream=stream)


@app.get("/nodes/{node_id}/status")
def get_node_status(
    node_id: Annotated[str, Path(title="Unique ID of node")],
):
    return app.state.events_service.get_status(node_id)


@app.get("/nodes/{node_id}/status/{device}")
def get_status(
    node_id: Annotated[str, Path(title="Unique ID of node")],
    device: Annotated[str, Path(title="Device (north, east, south, west, center)")],
):
    return app.state.events_service.get_status(node_id, device)


@app.post("/clear")
def clear_events():
    return requests.post(f"{app.state.pysim_url}/clear", json=[]).json()
