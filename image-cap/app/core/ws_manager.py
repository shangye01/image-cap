# app/core/ws_manager.py
from fastapi import WebSocket
import threading
from typing import Any


class ProgressConnectionManager:
    """按用户名维度维护 websocket 连接，推送项目进度变化。"""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}
        self._lock = threading.Lock()

    async def connect(self, username: str, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.setdefault(username, set()).add(websocket)

    def disconnect(self, username: str, websocket: WebSocket) -> None:
        with self._lock:
            sockets = self._connections.get(username)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(username, None)

    async def emit_to_users(self, usernames: list[str], payload: dict[str, Any]) -> None:
        targets: list[WebSocket] = []
        with self._lock:
            for username in set(usernames):
                targets.extend(list(self._connections.get(username, set())))

        dead_connections: list[tuple[str, WebSocket]] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:
                dead_connections.append((payload.get("owner"), websocket))

        if dead_connections:
            with self._lock:
                for _, ws in dead_connections:
                    for name, sockets in list(self._connections.items()):
                        if ws in sockets:
                            sockets.discard(ws)
                            if not sockets:
                                self._connections.pop(name, None)


# 全局单例
progress_ws_manager = ProgressConnectionManager()