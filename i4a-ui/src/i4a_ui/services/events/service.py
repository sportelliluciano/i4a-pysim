import requests

from .model.event import Event, Status


class NodeEventsService:
    def __init__(self, pysim_url):
        self.pysim_url = pysim_url

    def clear(self):
        requests.post(f"{self.pysim_url}/clear", json=[])

    def get_events(self, node_id, device=None, stream=None):
        url = f"{self.pysim_url}/nodes/{node_id}/events"
        
        if device:
            url += f"/{device}"
        
        if stream:
            url += f"?stream={stream}"
        
        return [Event(**ev).json() for ev in requests.get(url).json()]

    def get_status(self, node_id, device=None):
        url = f"{self.pysim_url}/nodes/{node_id}/status"
        
        if device:
            url += f"/{device}"
            return Status(requests.get(url).json()).json()
        
        return {k: Status(v).json() for k, v in requests.get(url).json().items()}
