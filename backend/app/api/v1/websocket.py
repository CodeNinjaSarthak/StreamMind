"""WebSocket API routes."""

import json
import logging
from typing import Optional

from app.core.security import verify_token
from app.db.models.streaming_session import StreamingSession
from app.db.session import SessionLocal
from app.services.websocket.events import event_service
from app.services.websocket.manager import manager
from fastapi import (
    APIRouter,
    Query,
    WebSocket,
    WebSocketDisconnect,
)

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    connection_id: Optional[str] = Query(None),
) -> None:
    """WebSocket endpoint for real-time updates.

    Args:
        websocket: WebSocket connection.
        session_id: Session ID (UUID string).
        connection_id: Optional connection ID for reconnection.
    """
    conn_id = None
    try:
        conn_id = await manager.connect(session_id, websocket, connection_id)

        # Expect the first message to be {"type": "auth", "token": "<jwt>"}
        try:
            raw = await websocket.receive_text()
            first_msg = json.loads(raw)
        except WebSocketDisconnect:
            manager.disconnect(session_id, conn_id)
            return
        except Exception:
            try:
                await websocket.close(code=4001, reason="Auth message required")
            except Exception:
                pass
            manager.disconnect(session_id, conn_id)
            return

        if first_msg.get("type") != "auth" or not first_msg.get("token"):
            try:
                await websocket.close(code=4001, reason="Auth message required")
            except Exception:
                pass
            manager.disconnect(session_id, conn_id)
            return

        payload = verify_token(first_msg["token"])
        if not payload:
            try:
                await websocket.close(code=4001, reason="Invalid token")
            except Exception:
                pass
            manager.disconnect(session_id, conn_id)
            return

        db = SessionLocal()
        try:
            session_obj = db.query(StreamingSession).filter(StreamingSession.id == session_id).first()
            if not session_obj or str(session_obj.teacher_id) != payload.get("sub"):
                try:
                    await websocket.close(code=4003, reason="Forbidden")
                except Exception:
                    pass
                manager.disconnect(session_id, conn_id)
                return
        finally:
            db.close()

        await websocket.send_json(event_service.create_connected_event(conn_id, session_id))

        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                msg_type = message.get("type")

                if msg_type == "pong":
                    logger.debug(f"Received pong from {conn_id}")
                    continue

                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                else:
                    logger.info(f"Received message: {msg_type} from {conn_id}")
                    await websocket.send_json({"type": "ack", "message": "Message received"})

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {conn_id}")
                await websocket.send_json(
                    event_service.create_error_event("Invalid JSON format", error_code="INVALID_JSON")
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {conn_id}")
        if conn_id:
            manager.disconnect(session_id, conn_id)

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if conn_id:
            manager.disconnect(session_id, conn_id)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
