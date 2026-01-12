from typing import Dict, Set
from fastapi import WebSocket
import json

class Hub:
    def __init__(self):
        self.rooms: Dict[str, Set[WebSocket]] = {}

    async def join(self, session_id: str, ws: WebSocket):
        self.rooms.setdefault(session_id, set()).add(ws)

    async def leave(self, session_id: str, ws: WebSocket):
        if session_id in self.rooms:
            self.rooms[session_id].discard(ws)
            if not self.rooms[session_id]:
                del self.rooms[session_id]

    async def broadcast(self, session_id: str, payload: dict):
        if session_id not in self.rooms:
            return
        msg = json.dumps(payload, ensure_ascii=False)
        dead = []
        for w in list(self.rooms[session_id]):
            try:
                await w.send_text(msg)
            except Exception:
                dead.append(w)
        for w in dead:
            self.rooms[session_id].discard(w)
