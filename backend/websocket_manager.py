"""WebSocket connection manager for real-time updates."""
from fastapi import WebSocket
from typing import Dict, Set, Any
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasts events to connected clients."""

    def __init__(self):
        # Store active connections
        self.active_connections: Set[WebSocket] = set()
        # Map call_id to connections interested in that call
        self.call_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)

        # Remove from all call subscriptions
        for call_id, subscribers in self.call_subscriptions.items():
            subscribers.discard(websocket)

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    def subscribe_to_call(self, websocket: WebSocket, call_id: str):
        """Subscribe a connection to updates for a specific call."""
        if call_id not in self.call_subscriptions:
            self.call_subscriptions[call_id] = set()
        self.call_subscriptions[call_id].add(websocket)
        logger.info(f"WebSocket subscribed to call {call_id}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_to_call(self, call_id: str, message: dict):
        """Broadcast a message to all clients subscribed to a specific call."""
        print(f"")
        print(f"🔴 [WEBSOCKET] Broadcasting to call subscribers")
        print(f"   Call ID: {call_id}")
        print(f"   Message type: {message.get('type')}")
        print(f"   All call subscriptions: {list(self.call_subscriptions.keys())}")

        if call_id not in self.call_subscriptions:
            print(f"   ⚠️  No subscribers found for call_id: {call_id}")
            return

        disconnected = set()
        subscribers = self.call_subscriptions[call_id].copy()
        print(f"   ✅ Found {len(subscribers)} subscribers for call_id: {call_id}")

        for connection in subscribers:
            try:
                print(f"   📤 Sending message to subscriber...")
                await connection.send_json(message)
                print(f"   ✅ Message sent successfully")
            except Exception as e:
                logger.error(f"Error broadcasting to call subscriber: {e}")
                print(f"   ❌ Failed to send to subscriber: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

        print(f"   ✅ Broadcast complete (sent to {len(subscribers) - len(disconnected)} clients)")

    # ========================================================================
    # Event Helper Methods (matching frontend WSEvent types)
    # ========================================================================

    async def emit_call_started(self, call_id: str, elder_id: str):
        """Emit call_started event."""
        await self.broadcast({
            "type": "call_started",
            "data": {
                "call_id": call_id,
                "elder_id": elder_id
            }
        })

    async def emit_call_status(self, call_id: str, status: str):
        """Emit call_status event."""
        await self.broadcast({
            "type": "call_status",
            "data": {
                "call_id": call_id,
                "status": status
            }
        })

    async def emit_transcript_update(self, call_id: str, transcript_line: dict, room_name: str = None):
        """Emit transcript_update event. Broadcasts to both call_id and room_name subscribers."""
        print(f"")
        print(f"🟣 [WS_MANAGER] emit_transcript_update called")
        print(f"   Call ID: {call_id}")
        print(f"   Room name: {room_name}")
        print(f"   Transcript line: {transcript_line.get('speaker')} - {transcript_line.get('text', '')[:50]}...")

        message = {
            "type": "transcript_update",
            "data": transcript_line
        }

        # Broadcast to call_id subscribers
        print(f"   📡 Broadcasting to call_id: {call_id}")
        await self.broadcast_to_call(call_id, message)

        # Also broadcast to room_name subscribers if provided
        if room_name and room_name != call_id:
            print(f"   📡 Also broadcasting to room_name: {room_name}")
            await self.broadcast_to_call(room_name, message)

        print(f"   ✅ emit_transcript_update complete")

    async def emit_biometric_update(self, call_id: str, biometric_data: dict):
        """Emit biometric_update event."""
        await self.broadcast_to_call(call_id, {
            "type": "biometric_update",
            "data": biometric_data
        })

    async def emit_wellbeing_update(self, call_id: str, wellbeing_data: dict, room_name: str = None):
        """Emit wellbeing_update event. Broadcasts to both call_id and room_name subscribers."""
        message = {
            "type": "wellbeing_update",
            "data": wellbeing_data
        }
        await self.broadcast_to_call(call_id, message)
        if room_name and room_name != call_id:
            await self.broadcast_to_call(room_name, message)

    async def emit_profile_update(self, call_id: str, profile_fact: dict, room_name: str = None):
        """Emit profile_update event. Broadcasts to both call_id and room_name subscribers."""
        message = {
            "type": "profile_update",
            "data": profile_fact
        }
        await self.broadcast_to_call(call_id, message)
        if room_name and room_name != call_id:
            await self.broadcast_to_call(room_name, message)

    async def emit_concern_detected(self, call_id: str, concern: dict, room_name: str = None):
        """Emit concern_detected event. Broadcasts to both call_id and room_name subscribers."""
        message = {
            "type": "concern_detected",
            "data": concern
        }
        await self.broadcast_to_call(call_id, message)
        if room_name and room_name != call_id:
            await self.broadcast_to_call(room_name, message)

    async def emit_village_action_started(self, call_id: str, action: dict):
        """Emit village_action_started event."""
        await self.broadcast_to_call(call_id, {
            "type": "village_action_started",
            "data": action
        })

    async def emit_village_action_update(self, call_id: str, action_id: str,
                                         status: str, response: str = None):
        """Emit village_action_update event."""
        data = {
            "id": action_id,
            "status": status
        }
        if response:
            data["response"] = response

        await self.broadcast_to_call(call_id, {
            "type": "village_action_update",
            "data": data
        })

    async def emit_call_ended(self, call_id: str, summary: dict):
        """Emit call_ended event."""
        await self.broadcast_to_call(call_id, {
            "type": "call_ended",
            "data": {
                "call_id": call_id,
                "summary": summary
            }
        })

    async def emit_timer_update(self, call_id: str, elapsed_seconds: int):
        """Emit timer_update event."""
        await self.broadcast_to_call(call_id, {
            "type": "timer_update",
            "data": {
                "elapsed_seconds": elapsed_seconds
            }
        })


# Global connection manager instance
ws_manager = ConnectionManager()
