"""
Project Inkling - Gossip Protocol

mDNS-based peer discovery and direct communication between Inklings on the same LAN.
Enables offline telegram exchange and dream sharing without internet.
"""

import asyncio
import json
import socket
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Callable
from enum import Enum

import aiohttp

from core.crypto import Identity
from core.telegram import TelegramCrypto


# mDNS service type
MDNS_SERVICE_TYPE = "_inkling._tcp.local."
GOSSIP_PORT = 8471


class PeerStatus(Enum):
    """Peer connection status."""
    DISCOVERED = "discovered"
    CONNECTED = "connected"
    VERIFIED = "verified"
    OFFLINE = "offline"


@dataclass
class Peer:
    """A discovered Inkling peer on the LAN."""
    public_key: str
    name: str
    host: str
    port: int
    encryption_key: Optional[str] = None  # X25519 key for telegrams
    status: PeerStatus = PeerStatus.DISCOVERED
    last_seen: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    @property
    def is_online(self) -> bool:
        # Consider offline if not seen in 5 minutes
        return time.time() - self.last_seen < 300


@dataclass
class GossipMessage:
    """A message in the gossip protocol."""
    type: str  # "hello", "dream", "telegram", "ping", "pong"
    sender_key: str
    payload: Dict
    signature: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "sender_key": self.sender_key,
            "payload": self.payload,
            "signature": self.signature,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "GossipMessage":
        return cls(
            type=data["type"],
            sender_key=data["sender_key"],
            payload=data["payload"],
            signature=data["signature"],
            timestamp=data.get("timestamp", time.time()),
        )


class GossipProtocol:
    """
    Handles peer-to-peer communication between Inklings on the same LAN.

    Features:
    - mDNS service advertisement and discovery
    - Direct encrypted messaging
    - Dream sharing without internet
    - Automatic peer tracking
    """

    def __init__(
        self,
        identity: Identity,
        telegram_crypto: TelegramCrypto,
        device_name: str = "Inkling",
        port: int = GOSSIP_PORT,
    ):
        self.identity = identity
        self.telegram_crypto = telegram_crypto
        self.device_name = device_name
        self.port = port

        self._peers: Dict[str, Peer] = {}  # public_key -> Peer
        self._running = False
        self._server: Optional[asyncio.Server] = None

        # Event callbacks
        self._on_peer_discovered: List[Callable[[Peer], None]] = []
        self._on_peer_lost: List[Callable[[Peer], None]] = []
        self._on_dream_received: List[Callable[[str, Dict], None]] = []
        self._on_telegram_received: List[Callable[[str, str], None]] = []

        # Message deduplication
        self._seen_messages: Set[str] = set()
        self._max_seen = 1000

    def on_peer_discovered(self, callback: Callable[[Peer], None]) -> None:
        """Register callback for peer discovery."""
        self._on_peer_discovered.append(callback)

    def on_peer_lost(self, callback: Callable[[Peer], None]) -> None:
        """Register callback for peer disconnection."""
        self._on_peer_lost.append(callback)

    def on_dream_received(self, callback: Callable[[str, Dict], None]) -> None:
        """Register callback for received dreams (sender_key, dream_data)."""
        self._on_dream_received.append(callback)

    def on_telegram_received(self, callback: Callable[[str, str], None]) -> None:
        """Register callback for received telegrams (sender_key, decrypted_content)."""
        self._on_telegram_received.append(callback)

    async def start(self) -> None:
        """Start the gossip protocol."""
        self._running = True

        # Start TCP server for incoming connections
        self._server = await asyncio.start_server(
            self._handle_connection,
            "0.0.0.0",
            self.port,
        )

        print(f"[Gossip] Listening on port {self.port}")

        # Start background tasks
        asyncio.create_task(self._mdns_advertise())
        asyncio.create_task(self._mdns_discover())
        asyncio.create_task(self._peer_maintenance())

    async def stop(self) -> None:
        """Stop the gossip protocol."""
        self._running = False

        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _mdns_advertise(self) -> None:
        """Advertise this device via mDNS."""
        try:
            from zeroconf import Zeroconf, ServiceInfo
        except ImportError:
            print("[Gossip] zeroconf not installed, mDNS disabled")
            return

        zc = Zeroconf()

        # Get local IP
        local_ip = self._get_local_ip()
        if not local_ip:
            print("[Gossip] Could not determine local IP")
            return

        # Create service info
        service_name = f"{self.device_name}.{MDNS_SERVICE_TYPE}"
        info = ServiceInfo(
            MDNS_SERVICE_TYPE,
            service_name,
            addresses=[socket.inet_aton(local_ip)],
            port=self.port,
            properties={
                "pk": self.identity.public_key_hex[:32],  # Truncated for mDNS limits
                "ek": self.telegram_crypto.public_key_hex[:32],
                "name": self.device_name,
            },
        )

        try:
            zc.register_service(info)
            print(f"[Gossip] Advertising as {service_name}")

            while self._running:
                await asyncio.sleep(30)

        finally:
            zc.unregister_service(info)
            zc.close()

    async def _mdns_discover(self) -> None:
        """Discover other Inklings via mDNS."""
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceListener
        except ImportError:
            return

        class InklingListener(ServiceListener):
            def __init__(self, gossip: "GossipProtocol"):
                self.gossip = gossip

            def add_service(self, zc, type_, name):
                asyncio.create_task(self.gossip._on_service_found(zc, type_, name))

            def remove_service(self, zc, type_, name):
                pass

            def update_service(self, zc, type_, name):
                pass

        zc = Zeroconf()
        listener = InklingListener(self)
        browser = ServiceBrowser(zc, MDNS_SERVICE_TYPE, listener)

        try:
            while self._running:
                await asyncio.sleep(10)
        finally:
            browser.cancel()
            zc.close()

    async def _on_service_found(self, zc, type_: str, name: str) -> None:
        """Handle discovered mDNS service."""
        try:
            from zeroconf import Zeroconf
        except ImportError:
            return

        info = zc.get_service_info(type_, name)
        if not info:
            return

        # Parse service info
        addresses = info.parsed_addresses()
        if not addresses:
            return

        host = addresses[0]
        port = info.port
        props = info.properties

        # Skip self
        pk_prefix = props.get(b"pk", b"").decode()
        if pk_prefix and self.identity.public_key_hex.startswith(pk_prefix):
            return

        # Connect to get full public key
        await self._connect_to_peer(host, port)

    async def _connect_to_peer(self, host: str, port: int) -> Optional[Peer]:
        """Connect to a peer and exchange hello messages."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )

            # Send hello
            hello = self._create_hello_message()
            writer.write(json.dumps(hello.to_dict()).encode() + b"\n")
            await writer.drain()

            # Receive hello response
            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not data:
                writer.close()
                return None

            response = GossipMessage.from_dict(json.loads(data))

            if response.type != "hello":
                writer.close()
                return None

            # Create peer
            peer = Peer(
                public_key=response.sender_key,
                name=response.payload.get("name", "Unknown"),
                host=host,
                port=port,
                encryption_key=response.payload.get("encryption_key"),
                status=PeerStatus.CONNECTED,
            )

            # Store peer
            self._peers[peer.public_key] = peer

            # Notify listeners
            for callback in self._on_peer_discovered:
                try:
                    callback(peer)
                except Exception:
                    pass

            print(f"[Gossip] Connected to {peer.name} at {peer.address}")

            writer.close()
            await writer.wait_closed()

            return peer

        except Exception as e:
            print(f"[Gossip] Failed to connect to {host}:{port}: {e}")
            return None

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ) -> None:
        """Handle incoming peer connection."""
        addr = writer.get_extra_info("peername")

        try:
            # Read message
            data = await asyncio.wait_for(reader.readline(), timeout=10.0)
            if not data:
                return

            message = GossipMessage.from_dict(json.loads(data))

            # Handle based on type
            if message.type == "hello":
                # Send hello response
                hello = self._create_hello_message()
                writer.write(json.dumps(hello.to_dict()).encode() + b"\n")
                await writer.drain()

                # Register peer if not known
                if message.sender_key not in self._peers:
                    peer = Peer(
                        public_key=message.sender_key,
                        name=message.payload.get("name", "Unknown"),
                        host=addr[0],
                        port=message.payload.get("port", GOSSIP_PORT),
                        encryption_key=message.payload.get("encryption_key"),
                        status=PeerStatus.CONNECTED,
                    )
                    self._peers[peer.public_key] = peer

                    for callback in self._on_peer_discovered:
                        try:
                            callback(peer)
                        except Exception:
                            pass

            elif message.type == "dream":
                await self._handle_dream(message)

            elif message.type == "telegram":
                await self._handle_telegram(message)

            elif message.type == "ping":
                # Respond with pong
                pong = self._create_message("pong", {})
                writer.write(json.dumps(pong.to_dict()).encode() + b"\n")
                await writer.drain()

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            print(f"[Gossip] Connection error from {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    def _create_hello_message(self) -> GossipMessage:
        """Create a hello message for peer introduction."""
        payload = {
            "name": self.device_name,
            "port": self.port,
            "encryption_key": self.telegram_crypto.public_key_hex,
        }
        return self._create_message("hello", payload)

    def _create_message(self, msg_type: str, payload: Dict) -> GossipMessage:
        """Create and sign a gossip message."""
        # Sign the payload
        sign_data = json.dumps({
            "type": msg_type,
            "payload": payload,
            "timestamp": time.time(),
        }, sort_keys=True).encode()

        signature = self.identity.sign(sign_data).hex()

        return GossipMessage(
            type=msg_type,
            sender_key=self.identity.public_key_hex,
            payload=payload,
            signature=signature,
        )

    async def _handle_dream(self, message: GossipMessage) -> None:
        """Handle received dream."""
        # Check for duplicate
        msg_id = f"{message.sender_key}:{message.timestamp}"
        if msg_id in self._seen_messages:
            return

        self._seen_messages.add(msg_id)
        if len(self._seen_messages) > self._max_seen:
            # Remove oldest
            self._seen_messages = set(list(self._seen_messages)[-500:])

        # Update peer last_seen
        if message.sender_key in self._peers:
            self._peers[message.sender_key].last_seen = time.time()

        # Notify listeners
        for callback in self._on_dream_received:
            try:
                callback(message.sender_key, message.payload)
            except Exception:
                pass

    async def _handle_telegram(self, message: GossipMessage) -> None:
        """Handle received encrypted telegram."""
        payload = message.payload

        # Check if it's for us
        if payload.get("to_key") != self.identity.public_key_hex:
            return

        # Decrypt
        try:
            content = self.telegram_crypto.decrypt(
                encrypted_content_base64=payload["encrypted_content"],
                nonce_hex=payload["nonce"],
                sender_public_key_hex=payload["sender_encryption_key"],
            )

            # Notify listeners
            for callback in self._on_telegram_received:
                try:
                    callback(message.sender_key, content)
                except Exception:
                    pass

        except Exception as e:
            print(f"[Gossip] Failed to decrypt telegram: {e}")

    async def _peer_maintenance(self) -> None:
        """Periodically check peer health and remove stale peers."""
        while self._running:
            await asyncio.sleep(60)

            now = time.time()
            stale_peers = []

            for pk, peer in self._peers.items():
                if now - peer.last_seen > 300:  # 5 minutes
                    peer.status = PeerStatus.OFFLINE
                    stale_peers.append(pk)

            for pk in stale_peers:
                peer = self._peers.pop(pk, None)
                if peer:
                    for callback in self._on_peer_lost:
                        try:
                            callback(peer)
                        except Exception:
                            pass

    async def send_dream(self, dream_data: Dict) -> int:
        """
        Broadcast a dream to all connected peers.

        Returns:
            Number of peers notified
        """
        message = self._create_message("dream", dream_data)
        count = 0

        for peer in self._peers.values():
            if peer.status != PeerStatus.OFFLINE:
                try:
                    await self._send_to_peer(peer, message)
                    count += 1
                except Exception:
                    pass

        return count

    async def send_telegram_to_peer(
        self,
        peer_public_key: str,
        content: str,
    ) -> bool:
        """
        Send an encrypted telegram directly to a LAN peer.

        Returns:
            True if sent successfully
        """
        peer = self._peers.get(peer_public_key)
        if not peer or not peer.encryption_key:
            return False

        # Encrypt
        encrypted, nonce = self.telegram_crypto.encrypt(content, peer.encryption_key)

        payload = {
            "to_key": peer_public_key,
            "encrypted_content": encrypted,
            "nonce": nonce,
            "sender_encryption_key": self.telegram_crypto.public_key_hex,
        }

        message = self._create_message("telegram", payload)

        try:
            await self._send_to_peer(peer, message)
            return True
        except Exception as e:
            print(f"[Gossip] Failed to send telegram to {peer.name}: {e}")
            return False

    async def _send_to_peer(self, peer: Peer, message: GossipMessage) -> None:
        """Send a message to a specific peer."""
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(peer.host, peer.port),
            timeout=5.0
        )

        try:
            writer.write(json.dumps(message.to_dict()).encode() + b"\n")
            await writer.drain()
            peer.last_seen = time.time()
        finally:
            writer.close()
            await writer.wait_closed()

    def _get_local_ip(self) -> Optional[str]:
        """Get local IP address."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None

    @property
    def peers(self) -> List[Peer]:
        """Get list of known peers."""
        return list(self._peers.values())

    @property
    def online_peers(self) -> List[Peer]:
        """Get list of online peers."""
        return [p for p in self._peers.values() if p.is_online]

    def get_peer(self, public_key: str) -> Optional[Peer]:
        """Get a specific peer by public key."""
        return self._peers.get(public_key)
