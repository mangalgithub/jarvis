import asyncio
import json
import logging
from typing import Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.auth import verify_token_from_query

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        # Map user_id -> list of active websockets
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("[websockets] User %s connected. Total connections for user: %d", user_id, len(self.active_connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("[websockets] User %s disconnected.", user_id)

    async def broadcast_to_user(self, user_id: str, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as exc:
                    logger.error("[websockets] Failed to send message to %s: %s", user_id, exc)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str, token: str = None):
    try:
        if not token:
            await websocket.close(code=1008)
            return
        actual_user_id = verify_token_from_query(token)
    except Exception as e:
        logger.error("Websocket auth failed: %s", e)
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, actual_user_id)
    try:
        while True:
            # We don't really expect client to send anything, but we keep connection open
            data = await websocket.receive_text()
            # Can handle incoming messages if needed, e.g. ping/pong
    except WebSocketDisconnect:
        manager.disconnect(websocket, actual_user_id)
