"""WebSocket module for real-time metrics updates."""
from app.websocket.manager import manager
from app.websocket import router

__all__ = ["manager", "router"]
