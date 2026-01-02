"""WebSocket connection manager."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class ConnectionInfo:
    """Information about a WebSocket connection."""

    def __init__(self, websocket: WebSocket, connection_id: str):
        """Initialize connection info.

        Args:
            websocket: WebSocket instance.
            connection_id: Unique connection identifier.
        """
        self.websocket = websocket
        self.connection_id = connection_id
        self.connected_at = datetime.now(timezone.utc)
        self.last_heartbeat = datetime.now(timezone.utc)
        self.is_alive = True


class WebSocketManager:
    """Manages WebSocket connections with heartbeat and reconnection support."""

    def __init__(self):
        """Initialize WebSocket manager."""
        self.active_connections: Dict[str, Dict[str, ConnectionInfo]] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        session_id: str,
        websocket: WebSocket,
        connection_id: Optional[str] = None
    ) -> str:
        """Connect a WebSocket to a session.

        Args:
            session_id: Session ID.
            websocket: WebSocket connection.
            connection_id: Optional connection ID for reconnection.

        Returns:
            Connection ID.
        """
        await websocket.accept()

        if connection_id is None:
            import uuid
            connection_id = str(uuid.uuid4())

        if session_id not in self.active_connections:
            self.active_connections[session_id] = {}

        conn_info = ConnectionInfo(websocket, connection_id)
        self.active_connections[session_id][connection_id] = conn_info

        logger.info(
            f"WebSocket connected",
            extra={
                "session_id": session_id,
                "connection_id": connection_id,
                "total_connections": len(self.active_connections[session_id])
            }
        )

        if self.heartbeat_task is None or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        return connection_id

    def disconnect(self, session_id: str, connection_id: str) -> None:
        """Disconnect a WebSocket from a session.

        Args:
            session_id: Session ID.
            connection_id: Connection ID.
        """
        if session_id in self.active_connections:
            if connection_id in self.active_connections[session_id]:
                del self.active_connections[session_id][connection_id]
                logger.info(
                    f"WebSocket disconnected",
                    extra={"session_id": session_id, "connection_id": connection_id}
                )

            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def send_personal_message(
        self,
        session_id: str,
        connection_id: str,
        message: Dict[str, Any]
    ) -> bool:
        """Send a message to a specific WebSocket.

        Args:
            session_id: Session ID.
            connection_id: Connection ID.
            message: Message dictionary.

        Returns:
            True if sent successfully.
        """
        if session_id not in self.active_connections:
            return False

        if connection_id not in self.active_connections[session_id]:
            return False

        conn_info = self.active_connections[session_id][connection_id]
        try:
            await conn_info.websocket.send_json(message)
            return True
        except WebSocketDisconnect:
            self.disconnect(session_id, connection_id)
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def broadcast_to_session(
        self,
        session_id: str,
        message: Dict[str, Any],
        exclude_connection: Optional[str] = None
    ) -> int:
        """Broadcast a message to all connections in a session.

        Args:
            session_id: Session ID.
            message: Message dictionary.
            exclude_connection: Optional connection ID to exclude.

        Returns:
            Number of successful sends.
        """
        if session_id not in self.active_connections:
            return 0

        successful = 0
        failed_connections = []

        for connection_id, conn_info in self.active_connections[session_id].items():
            if exclude_connection and connection_id == exclude_connection:
                continue

            try:
                await conn_info.websocket.send_json(message)
                successful += 1
            except WebSocketDisconnect:
                failed_connections.append(connection_id)
            except Exception as e:
                logger.error(f"Failed to broadcast to connection {connection_id}: {e}")
                failed_connections.append(connection_id)

        for connection_id in failed_connections:
            self.disconnect(session_id, connection_id)

        return successful

    async def broadcast_to_all(self, message: Dict[str, Any]) -> int:
        """Broadcast a message to all active connections.

        Args:
            message: Message dictionary.

        Returns:
            Number of successful sends.
        """
        successful = 0
        for session_id in list(self.active_connections.keys()):
            successful += await self.broadcast_to_session(session_id, message)
        return successful

    async def send_heartbeat(self, session_id: str, connection_id: str) -> bool:
        """Send heartbeat ping to connection.

        Args:
            session_id: Session ID.
            connection_id: Connection ID.

        Returns:
            True if heartbeat sent successfully.
        """
        return await self.send_personal_message(
            session_id,
            connection_id,
            {"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()}
        )

    async def _heartbeat_loop(self) -> None:
        """Background task to send periodic heartbeats."""
        while True:
            try:
                await asyncio.sleep(settings.websocket_heartbeat_interval)

                for session_id in list(self.active_connections.keys()):
                    for connection_id in list(self.active_connections[session_id].keys()):
                        await self.send_heartbeat(session_id, connection_id)

            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")

    def get_session_count(self, session_id: str) -> int:
        """Get number of connections for a session.

        Args:
            session_id: Session ID.

        Returns:
            Number of active connections.
        """
        if session_id not in self.active_connections:
            return 0
        return len(self.active_connections[session_id])

    def get_total_connections(self) -> int:
        """Get total number of active connections.

        Returns:
            Total number of connections.
        """
        return sum(len(conns) for conns in self.active_connections.values())


manager = WebSocketManager()

