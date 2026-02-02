"""
Project Inkling - Cloud API Client

Handles communication with the Vercel backend for:
- Oracle (AI proxy)
- Dreams (plant/fish)
- Telegrams (Phase 2)

Includes offline queue for network resilience.
"""

import asyncio
import json
import time
import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import aiohttp

from .crypto import Identity


@dataclass
class QueuedRequest:
    """A request waiting to be sent."""
    id: int
    endpoint: str
    payload: Dict[str, Any]
    created_at: float
    retry_count: int = 0
    max_retries: int = 5


class OfflineQueue:
    """
    SQLite-backed queue for requests when offline.

    Stores requests locally and retries when connection restored.
    """

    def __init__(self, db_path: str = "~/.inkling/queue.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the queue database."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at REAL NOT NULL,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 5
            )
        """)
        conn.commit()
        conn.close()

    def add(self, endpoint: str, payload: Dict[str, Any], max_retries: int = 5) -> int:
        """Add a request to the queue."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "INSERT INTO queue (endpoint, payload, created_at, max_retries) VALUES (?, ?, ?, ?)",
            (endpoint, json.dumps(payload), time.time(), max_retries)
        )
        request_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return request_id

    def get_pending(self, limit: int = 10) -> List[QueuedRequest]:
        """Get pending requests to retry."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT id, endpoint, payload, created_at, retry_count, max_retries "
            "FROM queue WHERE retry_count < max_retries ORDER BY created_at LIMIT ?",
            (limit,)
        )
        requests = []
        for row in cursor:
            requests.append(QueuedRequest(
                id=row[0],
                endpoint=row[1],
                payload=json.loads(row[2]),
                created_at=row[3],
                retry_count=row[4],
                max_retries=row[5],
            ))
        conn.close()
        return requests

    def mark_success(self, request_id: int) -> None:
        """Remove a successfully sent request."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("DELETE FROM queue WHERE id = ?", (request_id,))
        conn.commit()
        conn.close()

    def mark_retry(self, request_id: int) -> None:
        """Increment retry count for a failed request."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE queue SET retry_count = retry_count + 1 WHERE id = ?",
            (request_id,)
        )
        conn.commit()
        conn.close()

    def cleanup_expired(self, max_age_hours: int = 24) -> int:
        """Remove requests older than max_age_hours or exceeded retries."""
        conn = sqlite3.connect(self.db_path)
        cutoff = time.time() - (max_age_hours * 3600)
        cursor = conn.execute(
            "DELETE FROM queue WHERE created_at < ? OR retry_count >= max_retries",
            (cutoff,)
        )
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    @property
    def size(self) -> int:
        """Number of pending requests."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM queue WHERE retry_count < max_retries")
        count = cursor.fetchone()[0]
        conn.close()
        return count


class APIClient:
    """
    Client for the Inkling cloud API.

    Handles:
    - Request signing with device identity
    - Challenge-response authentication
    - Automatic retries with backoff
    - Offline queue for network resilience
    """

    def __init__(
        self,
        identity: Identity,
        api_base: str = "https://your-project.vercel.app/api",
        timeout: int = 30,
    ):
        self.identity = identity
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout

        self._session: Optional[aiohttp.ClientSession] = None
        self._queue = OfflineQueue()
        self._current_nonce: Optional[str] = None
        self._nonce_expires: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get_nonce(self) -> Optional[str]:
        """Get a fresh challenge nonce from the server."""
        # Return cached nonce if still valid (with 30s buffer)
        if self._current_nonce and time.time() < self._nonce_expires - 30:
            nonce = self._current_nonce
            self._current_nonce = None  # Use once
            return nonce

        try:
            session = await self._get_session()
            async with session.get(f"{self.api_base}/oracle") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._current_nonce = data.get("nonce")
                    self._nonce_expires = time.time() + 300  # 5 min validity
                    nonce = self._current_nonce
                    self._current_nonce = None
                    return nonce
        except Exception as e:
            print(f"[API] Failed to get nonce: {e}")

        return None

    async def _send_signed_request(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        use_nonce: bool = True,
    ) -> Dict[str, Any]:
        """
        Send a signed request to the API.

        Args:
            endpoint: API endpoint (e.g., "/oracle")
            payload: Request payload
            use_nonce: Whether to include challenge nonce

        Returns:
            Response data

        Raises:
            APIError: On request failure
        """
        # Get nonce if needed
        nonce = None
        if use_nonce:
            nonce = await self._get_nonce()

        # Sign the payload
        signed = self.identity.sign_payload(payload, nonce)

        # Send request
        session = await self._get_session()
        url = f"{self.api_base}{endpoint}"

        async with session.post(url, json=signed) as resp:
            data = await resp.json()

            if resp.status == 200:
                return data
            elif resp.status == 401:
                raise AuthenticationError(data.get("error", "Authentication failed"))
            elif resp.status == 429:
                raise RateLimitError(data.get("error", "Rate limit exceeded"))
            elif resp.status == 403:
                raise ForbiddenError(data.get("error", "Forbidden"))
            else:
                raise APIError(f"API error {resp.status}: {data.get('error', 'Unknown')}")

    async def oracle(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
    ) -> Dict[str, Any]:
        """
        Call the Oracle (AI proxy) endpoint.

        Args:
            messages: Chat messages [{"role": "user", "content": "..."}]
            system_prompt: System prompt for AI

        Returns:
            Response with content, tokens_used, provider, model
        """
        payload = {
            "messages": messages,
            "system_prompt": system_prompt,
        }

        return await self._send_signed_request("/oracle", payload)

    async def plant_dream(
        self,
        content: str,
        mood: Optional[str] = None,
        face: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post a dream to the Night Pool.

        Args:
            content: Dream text (max 280 chars)
            mood: Current mood
            face: Face expression

        Returns:
            Response with dream id and remaining quota
        """
        payload = {
            "content": content,
            "mood": mood,
            "face": face,
        }

        try:
            return await self._send_signed_request("/plant", payload)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            # Queue for later if offline
            self._queue.add("/plant", payload)
            raise OfflineError(f"Request queued: {e}")

    async def fish_dream(self) -> Optional[Dict[str, Any]]:
        """
        Fetch a random dream from the Night Pool.

        Returns:
            Dream data or None if pool is empty
        """
        result = await self._send_signed_request("/fish", {})
        return result.get("dream")

    async def send_telegram(
        self,
        to_public_key: str,
        encrypted_content: str,
        content_nonce: str,
        sender_encryption_key: str,
    ) -> Dict[str, Any]:
        """
        Send an encrypted telegram to another device.

        Args:
            to_public_key: Recipient's Ed25519 public key
            encrypted_content: Base64 encrypted message
            content_nonce: Encryption nonce (hex)
            sender_encryption_key: Sender's X25519 public key

        Returns:
            Response with telegram_id and remaining quota
        """
        payload = {
            "to_public_key": to_public_key,
            "encrypted_content": encrypted_content,
            "content_nonce": content_nonce,
            "sender_encryption_key": sender_encryption_key,
        }

        try:
            return await self._send_signed_request("/telegram", payload)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self._queue.add("/telegram", payload)
            raise OfflineError(f"Telegram queued: {e}")

    async def get_telegrams(self) -> List[Dict[str, Any]]:
        """
        Fetch pending telegrams from inbox.

        Returns:
            List of encrypted telegram dicts
        """
        session = await self._get_session()
        url = f"{self.api_base}/telegram?public_key={self.identity.public_key_hex}"

        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("telegrams", [])
            else:
                return []

    async def send_postcard(
        self,
        image_data: str,
        width: int,
        height: int,
        caption: Optional[str] = None,
        to_public_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a postcard (1-bit pixel art).

        Args:
            image_data: Base64 compressed bitmap
            width: Image width
            height: Image height
            caption: Optional caption (max 60 chars)
            to_public_key: Recipient (None = public)

        Returns:
            Response with postcard_id
        """
        payload = {
            "image_data": image_data,
            "width": width,
            "height": height,
            "caption": caption,
            "to_public_key": to_public_key,
        }

        try:
            return await self._send_signed_request("/postcard", payload)
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self._queue.add("/postcard", payload)
            raise OfflineError(f"Postcard queued: {e}")

    async def get_postcards(self, public: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch postcards.

        Args:
            public: If True, fetch public postcards. If False, fetch inbox.

        Returns:
            List of postcard dicts
        """
        session = await self._get_session()

        if public:
            url = f"{self.api_base}/postcard?public=true"
        else:
            url = f"{self.api_base}/postcard?public_key={self.identity.public_key_hex}"

        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("postcards", [])
            else:
                return []

    async def flush_queue(self) -> int:
        """
        Retry queued requests.

        Returns:
            Number of successfully sent requests
        """
        pending = self._queue.get_pending()
        success_count = 0

        for req in pending:
            try:
                await self._send_signed_request(req.endpoint, req.payload)
                self._queue.mark_success(req.id)
                success_count += 1
            except (aiohttp.ClientError, asyncio.TimeoutError):
                self._queue.mark_retry(req.id)
            except APIError:
                # Permanent failure, remove from queue
                self._queue.mark_success(req.id)

        return success_count

    @property
    def queue_size(self) -> int:
        """Number of requests in offline queue."""
        return self._queue.size

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            "api_base": self.api_base,
            "queue_size": self.queue_size,
            "device_id": self.identity.public_key_hex[:16] + "...",
        }


# Exceptions
class APIError(Exception):
    """Base API error."""
    pass


class AuthenticationError(APIError):
    """Authentication failed."""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded."""
    pass


class ForbiddenError(APIError):
    """Access forbidden (banned device)."""
    pass


class OfflineError(APIError):
    """Request queued due to network failure."""
    pass
