"""State management for FTL MCP server."""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SessionActivity(BaseModel):
    """Model for session activity tracking."""

    timestamp: str
    action: str
    request_id: str
    details: Optional[str] = None


class SessionData(BaseModel):
    """Model for session data storage."""

    session_id: str
    session_name: str
    start_time: str
    client_id: str
    request_count: int
    last_activity: str
    activities: List[SessionActivity]
    session_data: Dict[str, str]


class InventoryHost(BaseModel):
    """Model for inventory host data."""

    name: str
    vars: Dict[str, Any]
    groups: List[str]


class InventoryGroup(BaseModel):
    """Model for inventory group data."""

    hosts: List[str]
    vars: Dict[str, Any]
    children: List[str]


class InventoryData(BaseModel):
    """Model for Ansible inventory data."""

    source_file: str
    loaded_at: str
    total_hosts: int
    total_groups: int
    groups: Dict[str, InventoryGroup]
    hosts: Dict[str, InventoryHost]
    vars: Dict[str, Any]


class MissionAlert(BaseModel):
    """Model for FTL mission alerts."""

    timestamp: str
    message: str


class MissionData(BaseModel):
    """Model for FTL mission data."""

    name: str
    destination: str
    status: str
    start_time: str
    fuel_level: float
    crew_count: int
    distance_traveled: float
    alerts: List[MissionAlert]


class StateManager:
    """Thread-safe state manager for FastMCP persistent storage."""

    def __init__(self):
        # Session storage
        self._sessions: Dict[str, SessionData] = {}

        # Inventory storage
        self._inventory: Optional[InventoryData] = None
        self._inventory_history: List[str] = []

        # Mission storage
        self._current_mission: Optional[MissionData] = None
        self._mission_history: List[str] = []
        self._last_completed_mission: Optional[Dict[str, Any]] = None

        # Generic storage for any other data
        self._generic_storage: Dict[str, Any] = {}

    # Session management methods
    def set_session(self, session_id: str, data: SessionData) -> None:
        """Store session data."""
        self._sessions[session_id] = data

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Retrieve session data."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> Dict[str, SessionData]:
        """Get all active sessions."""
        return self._sessions.copy()

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    # Inventory management methods
    def set_inventory(self, data: InventoryData) -> None:
        """Store inventory data."""
        self._inventory = data

    def get_inventory(self) -> Optional[InventoryData]:
        """Retrieve inventory data."""
        return self._inventory

    def set_inventory_history(self, history: List[str]) -> None:
        """Set inventory history."""
        self._inventory_history = history.copy()

    def get_inventory_history(self) -> List[str]:
        """Get inventory history."""
        return self._inventory_history.copy()

    def clear_inventory(self) -> None:
        """Clear inventory data."""
        self._inventory = None
        self._inventory_history = []

    # Mission management methods
    def set_current_mission(self, data: Optional[MissionData]) -> None:
        """Store current mission data."""
        self._current_mission = data

    def get_current_mission(self) -> Optional[MissionData]:
        """Retrieve current mission data."""
        return self._current_mission

    def set_mission_history(self, history: List[str]) -> None:
        """Set mission history."""
        self._mission_history = history.copy()

    def get_mission_history(self) -> List[str]:
        """Get mission history."""
        return self._mission_history.copy()

    def set_last_completed_mission(self, data: Optional[Dict[str, Any]]) -> None:
        """Store last completed mission."""
        self._last_completed_mission = data

    def get_last_completed_mission(self) -> Optional[Dict[str, Any]]:
        """Get last completed mission."""
        return self._last_completed_mission

    # Generic storage methods
    def set_generic(self, key: str, value: Any) -> None:
        """Store generic data."""
        self._generic_storage[key] = value

    def get_generic(self, key: str, default: Any = None) -> Any:
        """Retrieve generic data."""
        return self._generic_storage.get(key, default)

    def delete_generic(self, key: str) -> bool:
        """Delete generic data."""
        if key in self._generic_storage:
            del self._generic_storage[key]
            return True
        return False

    # Utility methods
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "active_sessions": len(self._sessions),
            "inventory_loaded": self._inventory is not None,
            "active_mission": self._current_mission is not None,
            "generic_items": len(self._generic_storage),
            "total_memory_items": (
                len(self._sessions)
                + (1 if self._inventory else 0)
                + (1 if self._current_mission else 0)
                + len(self._generic_storage)
            ),
        }

    def to_json(self, section: Optional[str] = None) -> str:
        """Export data as JSON for debugging/backup."""
        if section == "sessions":
            return json.dumps(
                {k: v.model_dump() for k, v in self._sessions.items()}, indent=2
            )
        elif section == "inventory" and self._inventory:
            return self._inventory.model_dump_json(indent=2)
        elif section == "mission" and self._current_mission:
            return self._current_mission.model_dump_json(indent=2)
        elif section == "generic":
            return json.dumps(self._generic_storage, indent=2)
        else:
            # Export all data
            return json.dumps(
                {
                    "sessions": {k: v.model_dump() for k, v in self._sessions.items()},
                    "inventory": (
                        self._inventory.model_dump() if self._inventory else None
                    ),
                    "inventory_history": self._inventory_history,
                    "current_mission": (
                        self._current_mission.model_dump()
                        if self._current_mission
                        else None
                    ),
                    "mission_history": self._mission_history,
                    "last_completed_mission": self._last_completed_mission,
                    "generic_storage": self._generic_storage,
                    "stats": self.get_stats(),
                },
                indent=2,
            )

    def clear_all(self) -> None:
        """Clear all stored data (for testing/reset)."""
        self._sessions.clear()
        self._inventory = None
        self._inventory_history = []
        self._current_mission = None
        self._mission_history = []
        self._last_completed_mission = None
        self._generic_storage.clear()


# Global state manager instance
state_manager = StateManager()
