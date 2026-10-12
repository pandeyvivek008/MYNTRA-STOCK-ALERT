import asyncio
from fastapi import WebSocket

class LiveHub:
    def __init__(self): self.clients: set[WebSocket] = set()
    async def connect(self, websocket: WebSocket):
        await websocket.accept(); self.clients.add(websocket)
    def disconnect(self, websocket: WebSocket): self.clients.discard(websocket)
    async def broadcast(self, payload: dict):
        stale = []
        for client in list(self.clients):
            try: await client.send_json(payload)
            except Exception: stale.append(client)
        for client in stale: self.disconnect(client)

hub = LiveHub()
