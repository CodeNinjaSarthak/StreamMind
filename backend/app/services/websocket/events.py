"""WebSocket event handlers and event builders."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


class WebSocketEventType(str, Enum):
    """WebSocket event types."""

    PING = "ping"
    PONG = "pong"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"

    COMMENT_CREATED = "comment_created"
    COMMENT_CLASSIFIED = "comment_classified"

    CLUSTER_CREATED = "cluster_created"
    CLUSTER_UPDATED = "cluster_updated"

    ANSWER_READY = "answer_ready"
    ANSWER_POSTED = "answer_posted"

    QUOTA_ALERT = "quota_alert"
    QUOTA_EXCEEDED = "quota_exceeded"

    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


class WebSocketEventService:
    """Service for building and handling WebSocket events."""

    @staticmethod
    def create_base_event(
        event_type: WebSocketEventType, data: Optional[Dict[str, Any]] = None, message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a base event structure.

        Args:
            event_type: Type of the event.
            data: Optional event data.
            message: Optional message.

        Returns:
            Event message dictionary.
        """
        return {
            "type": event_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
            "message": message,
        }

    def create_connected_event(self, connection_id: str, session_id: str) -> Dict[str, Any]:
        """Create a connection established event.

        Args:
            connection_id: Connection identifier.
            session_id: Session identifier.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.CONNECTED,
            data={"connection_id": connection_id, "session_id": session_id},
            message="WebSocket connected successfully",
        )

    def create_comment_created_event(self, comment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a comment created event.

        Args:
            comment_data: Comment data dictionary.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.COMMENT_CREATED, data=comment_data, message="New comment received"
        )

    def create_comment_classified_event(self, comment_id: str, is_question: bool, confidence: float) -> Dict[str, Any]:
        """Create a comment classified event.

        Args:
            comment_id: Comment identifier.
            is_question: Whether comment is classified as question.
            confidence: Classification confidence score.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.COMMENT_CLASSIFIED,
            data={"comment_id": comment_id, "is_question": is_question, "confidence": confidence},
            message=f"Comment classified as {'question' if is_question else 'not a question'}",
        )

    def create_cluster_created_event(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a cluster created event.

        Args:
            cluster_data: Cluster data dictionary.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.CLUSTER_CREATED,
            data=cluster_data,
            message=f"New cluster created: {cluster_data.get('title', 'Untitled')}",
        )

    def create_cluster_updated_event(self, cluster_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a cluster updated event.

        Args:
            cluster_data: Cluster data dictionary.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.CLUSTER_UPDATED,
            data=cluster_data,
            message=f"Cluster updated: {cluster_data.get('title', 'Untitled')}",
        )

    def create_answer_ready_event(self, answer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create an answer ready event.

        Args:
            answer_data: Answer data dictionary.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.ANSWER_READY, data=answer_data, message="Answer generated and ready for review"
        )

    def create_answer_posted_event(self, answer_id: str, cluster_id: str) -> Dict[str, Any]:
        """Create an answer posted event.

        Args:
            answer_id: Answer identifier.
            cluster_id: Cluster identifier.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.ANSWER_POSTED,
            data={"answer_id": answer_id, "cluster_id": cluster_id},
            message="Answer posted to YouTube",
        )

    def create_quota_alert_event(self, quota_type: str, used: int, limit: int) -> Dict[str, Any]:
        """Create a quota alert event.

        Args:
            quota_type: Type of quota.
            used: Amount used.
            limit: Quota limit.

        Returns:
            Event message dictionary.
        """
        percentage = (used / limit * 100) if limit > 0 else 0
        return self.create_base_event(
            WebSocketEventType.QUOTA_ALERT,
            data={"quota_type": quota_type, "used": used, "limit": limit, "percentage": percentage},
            message=f"Quota alert: {quota_type} at {percentage:.1f}%",
        )

    def create_error_event(self, error_message: str, error_code: Optional[str] = None) -> Dict[str, Any]:
        """Create an error event.

        Args:
            error_message: Error message.
            error_code: Optional error code.

        Returns:
            Event message dictionary.
        """
        return self.create_base_event(
            WebSocketEventType.ERROR, data={"error_code": error_code} if error_code else {}, message=error_message
        )


event_service = WebSocketEventService()
