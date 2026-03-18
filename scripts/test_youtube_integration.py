"""
Unit tests for Phase 3: YouTube Integration.

Run with: python -m pytest scripts/test_youtube_integration.py -v
"""

import os
import sys
import unittest
from datetime import (
    datetime,
    timezone,
)
from unittest.mock import (
    MagicMock,
    patch,
)

# Ensure backend is importable
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
sys.path.insert(0, os.path.join(_root, "backend"))


class TestYouTubeOAuth(unittest.TestCase):
    """Tests for YouTubeOAuthService."""

    @patch("app.services.youtube.oauth.Flow")
    def test_get_authorization_url_returns_url_and_state(self, mock_flow_class):
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = (
            "https://accounts.google.com/o/oauth2/auth?scope=...",
            "test-state-xyz",
        )
        mock_flow_class.from_client_config.return_value = mock_flow

        from app.services.youtube.oauth import YouTubeOAuthService

        svc = YouTubeOAuthService()
        url, state = svc.get_authorization_url()

        self.assertIn("accounts.google.com", url)
        self.assertEqual(state, "test-state-xyz")
        mock_flow.authorization_url.assert_called_once_with(
            access_type="offline",
            include_granted_scopes="true",
        )

    @patch("app.services.youtube.oauth.Flow")
    def test_exchange_code_returns_token_dict(self, mock_flow_class):
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.token = "access123"
        mock_creds.refresh_token = "refresh456"
        mock_creds.expiry = datetime(2026, 3, 1, tzinfo=timezone.utc)
        mock_creds.scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        mock_flow.credentials = mock_creds
        mock_flow_class.from_client_config.return_value = mock_flow

        from app.services.youtube.oauth import YouTubeOAuthService

        svc = YouTubeOAuthService()
        result = svc.exchange_code_for_token("auth-code-xyz")

        self.assertEqual(result["access_token"], "access123")
        self.assertEqual(result["refresh_token"], "refresh456")
        self.assertIn("scope", result)


class TestYouTubeClient(unittest.TestCase):
    """Tests for YouTubeClient wrapper."""

    @patch("app.services.youtube.client.build")
    def test_get_live_chat_id_returns_id(self, mock_build):
        mock_service = MagicMock()
        mock_service.videos().list().execute.return_value = {
            "items": [{"liveStreamingDetails": {"activeLiveChatId": "chat123"}}]
        }
        mock_build.return_value = mock_service

        from app.services.youtube.client import YouTubeClient

        client = YouTubeClient("access_token")
        chat_id = client.get_live_chat_id("video123")
        self.assertEqual(chat_id, "chat123")

    @patch("app.services.youtube.client.build")
    def test_get_live_chat_id_returns_none_when_no_items(self, mock_build):
        mock_service = MagicMock()
        mock_service.videos().list().execute.return_value = {"items": []}
        mock_build.return_value = mock_service

        from app.services.youtube.client import YouTubeClient

        client = YouTubeClient("access_token")
        result = client.get_live_chat_id("nonexistent_video")
        self.assertIsNone(result)

    @patch("app.services.youtube.client.build")
    def test_list_messages_filters_text_events(self, mock_build):
        mock_service = MagicMock()
        mock_service.liveChatMessages().list().execute.return_value = {
            "items": [
                {
                    "id": "msg1",
                    "snippet": {
                        "type": "textMessageEvent",
                        "displayMessage": "Hello",
                        "publishedAt": "2026-01-01T00:00:00Z",
                    },
                    "authorDetails": {"displayName": "Alice", "channelId": "ch1"},
                },
                {
                    "id": "msg2",
                    "snippet": {
                        "type": "superChatEvent",
                        "displayMessage": "Donation",
                        "publishedAt": "2026-01-01T00:01:00Z",
                    },
                    "authorDetails": {"displayName": "Bob", "channelId": "ch2"},
                },
            ],
            "nextPageToken": "token_abc",
            "pollingIntervalMillis": 5000,
        }
        mock_build.return_value = mock_service

        from app.services.youtube.client import YouTubeClient

        client = YouTubeClient("access_token")
        result = client.list_messages("chat123")

        # Only the textMessageEvent should be included
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(result["messages"][0]["text"], "Hello")
        self.assertEqual(result["next_page_token"], "token_abc")

    @patch("app.services.youtube.client.build")
    def test_post_message_truncates_to_200_chars(self, mock_build):
        mock_service = MagicMock()
        mock_service.liveChatMessages().insert().execute.return_value = {"id": "posted_msg_1"}
        mock_build.return_value = mock_service

        from app.services.youtube.client import YouTubeClient

        client = YouTubeClient("access_token")
        long_text = "A" * 300
        msg_id = client.post_message("chat123", long_text)

        self.assertEqual(msg_id, "posted_msg_1")
        # Verify the text was truncated
        call_kwargs = mock_service.liveChatMessages().insert.call_args
        body = call_kwargs[1]["body"]
        posted_text = body["snippet"]["textMessageDetails"]["messageText"]
        self.assertEqual(len(posted_text), 200)


class TestYouTubeQuotaService(unittest.TestCase):
    """Tests for YouTubeQuotaService (Redis-backed)."""

    @patch("app.services.youtube.quota.redis_lib")
    def test_check_quota_returns_true_when_under_limit(self, mock_redis_lib):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "100"  # 100 used out of 10000
        mock_redis_lib.from_url.return_value = mock_redis

        from app.services.youtube.quota import YouTubeQuotaService

        svc = YouTubeQuotaService()
        self.assertTrue(svc.check_quota("teacher-1", "poll"))

    @patch("app.services.youtube.quota.redis_lib")
    def test_check_quota_returns_false_when_exceeded(self, mock_redis_lib):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "9999"  # only 1 unit left, poll costs 5
        mock_redis_lib.from_url.return_value = mock_redis

        from app.services.youtube.quota import YouTubeQuotaService

        svc = YouTubeQuotaService()
        self.assertFalse(svc.check_quota("teacher-1", "poll"))

    @patch("app.services.youtube.quota.redis_lib")
    def test_record_usage_uses_pipeline(self, mock_redis_lib):
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_redis.pipeline.return_value = mock_pipe
        mock_redis_lib.from_url.return_value = mock_redis

        from app.services.youtube.quota import YouTubeQuotaService

        svc = YouTubeQuotaService()
        svc.record_usage("teacher-1", "post")

        mock_pipe.incrby.assert_called_once()
        mock_pipe.expire.assert_called_once()
        mock_pipe.execute.assert_called_once()

    @patch("app.services.youtube.quota.redis_lib")
    def test_check_quota_handles_none_from_redis(self, mock_redis_lib):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # key doesn't exist
        mock_redis_lib.from_url.return_value = mock_redis

        from app.services.youtube.quota import YouTubeQuotaService

        svc = YouTubeQuotaService()
        # None means 0 used, should allow any operation
        self.assertTrue(svc.check_quota("teacher-1", "post"))


class TestYouTubePollingService(unittest.TestCase):
    """Tests for YouTubePollingService."""

    @patch("app.services.youtube.polling.YouTubeClient")
    def test_get_live_chat_id_delegates_to_client(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.get_live_chat_id.return_value = "live_chat_xyz"
        mock_client_class.return_value = mock_client

        from app.services.youtube.polling import YouTubePollingService

        svc = YouTubePollingService()
        result = svc.get_live_chat_id("video123", "access_token")

        self.assertEqual(result, "live_chat_xyz")
        mock_client.get_live_chat_id.assert_called_once_with("video123")

    @patch("app.services.youtube.polling.YouTubeClient")
    def test_fetch_messages_delegates_to_client(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.list_messages.return_value = {
            "messages": [{"text": "test question"}],
            "next_page_token": None,
            "polling_interval_ms": 5000,
        }
        mock_client_class.return_value = mock_client

        from app.services.youtube.polling import YouTubePollingService

        svc = YouTubePollingService()
        result = svc.fetch_live_chat_messages("chat123", "access_token")

        self.assertEqual(len(result["messages"]), 1)
        mock_client.list_messages.assert_called_once_with("chat123", None)


class TestYouTubePostingService(unittest.TestCase):
    """Tests for YouTubePostingService."""

    @patch("app.services.youtube.posting.YouTubeClient")
    def test_post_message_delegates_to_client(self, mock_client_class):
        mock_client = MagicMock()
        mock_client.post_message.return_value = "msg_id_abc"
        mock_client_class.return_value = mock_client

        from app.services.youtube.posting import YouTubePostingService

        svc = YouTubePostingService()
        result = svc.post_message("chat123", "Test answer text", "access_token")

        self.assertEqual(result, "msg_id_abc")
        mock_client.post_message.assert_called_once_with("chat123", "Test answer text")


if __name__ == "__main__":
    unittest.main()
