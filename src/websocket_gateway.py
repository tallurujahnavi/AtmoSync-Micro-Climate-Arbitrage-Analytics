"""
websocket_gateway.py – Real-time WebSocket streaming gateway for commodities trading terminals.

Provides low-latency push notification streaming for trading desks:
1. Client subscription management (channel/container routing)
2. Framing and JSON payload serialization
3. Heartbeat keepalive and dead-connection reap
4. Broadcast backpressure and message queue monitoring
"""

import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any


@dataclass
class WSMessage:
    channel: str
    event_type: str
    payload: Dict[str, Any]
    timestamp_utc: float = field(default_factory=time.time)

    def to_frame(self) -> str:
        return json.dumps({
            "channel": self.channel,
            "event": self.event_type,
            "data": self.payload,
            "ts": self.timestamp_utc,
        })


@dataclass
class WSClientSession:
    client_id: str
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: float = field(default_factory=time.time)
    last_ping: float = field(default_factory=time.time)
    is_active: bool = True
    inbox: List[str] = field(default_factory=list)


class WebSocketGateway:
    """Manages active WebSocket client connections, channels, and message fanout."""

    def __init__(self, heartbeat_timeout_sec: float = 30.0):
        self.clients: Dict[str, WSClientSession] = {}
        self.heartbeat_timeout_sec = heartbeat_timeout_sec

    def register_client(self, client_id: str) -> WSClientSession:
        session = WSClientSession(client_id=client_id)
        self.clients[client_id] = session
        return session

    def disconnect_client(self, client_id: str):
        if client_id in self.clients:
            self.clients[client_id].is_active = False
            del self.clients[client_id]

    def subscribe(self, client_id: str, channel: str) -> bool:
        if client_id in self.clients and self.clients[client_id].is_active:
            self.clients[client_id].subscriptions.add(channel)
            return True
        return False

    def unsubscribe(self, client_id: str, channel: str) -> bool:
        if client_id in self.clients:
            self.clients[client_id].subscriptions.discard(channel)
            return True
        return False

    def receive_heartbeat(self, client_id: str) -> bool:
        if client_id in self.clients:
            self.clients[client_id].last_ping = time.time()
            return True
        return False

    def broadcast(self, channel: str, event_type: str, payload: Dict[str, Any]) -> int:
        """Fans out a message frame to all clients subscribed to channel or wildcard '*'."""
        msg = WSMessage(channel=channel, event_type=event_type, payload=payload)
        frame = msg.to_frame()
        delivered_count = 0

        for client in self.clients.values():
            if not client.is_active:
                continue
            if "*" in client.subscriptions or channel in client.subscriptions:
                client.inbox.append(frame)
                delivered_count += 1

        return delivered_count

    def reap_stale_connections(self) -> int:
        """Disconnects clients that haven't sent a heartbeat within the timeout window."""
        now = time.time()
        stale_ids = [
            cid for cid, client in self.clients.items()
            if (now - client.last_ping) > self.heartbeat_timeout_sec
        ]
        for cid in stale_ids:
            self.disconnect_client(cid)
        return len(stale_ids)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "connected_clients": len(self.clients),
            "active_subscriptions": sum(len(c.subscriptions) for c in self.clients.values()),
            "total_pending_messages": sum(len(c.inbox) for c in self.clients.values()),
        }
