"""YouTube Data API v3 client wrapper."""

import logging
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)


class YouTubeClient:
    """Thin wrapper around the YouTube Data API v3."""

    SCOPES = [
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/youtube.force-ssl",
    ]

    def __init__(
        self,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expiry=None,
    ):
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
        )
        self._service = build("youtube", "v3", credentials=creds)

    def get_live_chat_id(self, video_id: str) -> Optional[str]:
        """Get the active live chat ID for a video.

        Args:
            video_id: YouTube video ID.

        Returns:
            Live chat ID or None if not found.
        """
        resp = self._service.videos().list(part="liveStreamingDetails", id=video_id).execute()
        items = resp.get("items", [])
        if not items:
            return None
        return items[0].get("liveStreamingDetails", {}).get("activeLiveChatId")

    def get_video_info(self, video_id: str) -> Optional[dict]:
        """Get basic video info including title and live status.

        Args:
            video_id: YouTube video ID.

        Returns:
            Dict with title, is_live, live_chat_id or None if not found.
        """
        resp = self._service.videos().list(part="snippet,liveStreamingDetails", id=video_id).execute()
        items = resp.get("items", [])
        if not items:
            return None
        item = items[0]
        snippet = item.get("snippet", {})
        streaming = item.get("liveStreamingDetails", {})
        return {
            "title": snippet.get("title", ""),
            "is_live": bool(streaming.get("activeLiveChatId")),
            "live_chat_id": streaming.get("activeLiveChatId"),
        }

    def list_messages(self, live_chat_id: str, page_token: Optional[str] = None) -> dict:
        """List live chat messages.

        Args:
            live_chat_id: Live chat ID.
            page_token: Optional pagination token.

        Returns:
            Dict with messages list, next_page_token, polling_interval_ms.
        """
        req = self._service.liveChatMessages().list(
            liveChatId=live_chat_id,
            part="snippet,authorDetails",
            pageToken=page_token,
        )
        resp = req.execute()
        messages = [
            {
                "youtube_comment_id": m["id"],
                "author_name": m["authorDetails"]["displayName"],
                "author_channel_id": m["authorDetails"]["channelId"],
                "text": m["snippet"]["displayMessage"],
                "published_at": m["snippet"]["publishedAt"],
            }
            for m in resp.get("items", [])
            if m["snippet"]["type"] == "textMessageEvent"
        ]
        return {
            "messages": messages,
            "next_page_token": resp.get("nextPageToken"),
            "polling_interval_ms": resp.get("pollingIntervalMillis", 5000),
        }

    def post_message(self, live_chat_id: str, text: str) -> str:
        """Post a message to live chat.

        Args:
            live_chat_id: Live chat ID.
            text: Message text (truncated to 200 chars).

        Returns:
            Posted message ID.
        """
        resp = (
            self._service.liveChatMessages()
            .insert(
                part="snippet",
                body={
                    "snippet": {
                        "liveChatId": live_chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {"messageText": text[:200]},
                    }
                },
            )
            .execute()
        )
        return resp["id"]

    @staticmethod
    def refresh_access_token(refresh_token: str) -> dict:
        """Refresh an expired access token.

        Args:
            refresh_token: Refresh token string.

        Returns:
            Dict with access_token and expires_at.
        """
        creds = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
        )
        creds.refresh(Request())
        return {"access_token": creds.token, "expires_at": creds.expiry}
