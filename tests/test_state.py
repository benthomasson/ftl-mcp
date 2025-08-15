"""Tests for StateManager and Pydantic models."""

import json
import pytest
from datetime import datetime
from typing import Dict, Any

from src.ftl_mcp.state import (
    StateManager,
    SessionData,
    SessionActivity,
    InventoryData,
    InventoryHost,
    InventoryGroup,
    MissionData,
    MissionAlert,
    state_manager,
)


class TestPydanticModels:
    """Test Pydantic model validation and serialization."""

    def test_session_activity_creation(self):
        """Test SessionActivity model creation and validation."""
        activity = SessionActivity(
            timestamp="2025-08-15T12:00:00",
            action="test_action",
            request_id="req_123",
            details="Test details"
        )
        
        assert activity.timestamp == "2025-08-15T12:00:00"
        assert activity.action == "test_action"
        assert activity.request_id == "req_123"
        assert activity.details == "Test details"

    def test_session_activity_optional_details(self):
        """Test SessionActivity with optional details field."""
        activity = SessionActivity(
            timestamp="2025-08-15T12:00:00",
            action="test_action",
            request_id="req_123"
        )
        
        assert activity.details is None

    def test_session_data_creation(self):
        """Test SessionData model creation and validation."""
        activities = [
            SessionActivity(
                timestamp="2025-08-15T12:00:00",
                action="session_started",
                request_id="req_123"
            )
        ]
        
        session = SessionData(
            session_id="session_123",
            session_name="Test Session",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=activities,
            session_data={"key": "value"}
        )
        
        assert session.session_id == "session_123"
        assert session.session_name == "Test Session"
        assert len(session.activities) == 1
        assert session.session_data["key"] == "value"

    def test_inventory_host_creation(self):
        """Test InventoryHost model creation."""
        host = InventoryHost(
            name="web01.example.com",
            vars={"ansible_host": "10.0.1.10", "server_role": "frontend"},
            groups=["webservers"]
        )
        
        assert host.name == "web01.example.com"
        assert host.vars["ansible_host"] == "10.0.1.10"
        assert "webservers" in host.groups

    def test_inventory_group_creation(self):
        """Test InventoryGroup model creation."""
        group = InventoryGroup(
            hosts=["web01.example.com", "web02.example.com"],
            vars={"http_port": 80},
            children=["databases"]
        )
        
        assert len(group.hosts) == 2
        assert group.vars["http_port"] == 80
        assert "databases" in group.children

    def test_inventory_data_creation(self):
        """Test InventoryData model creation."""
        hosts = {
            "web01.example.com": InventoryHost(
                name="web01.example.com",
                vars={"ansible_host": "10.0.1.10"},
                groups=["webservers"]
            )
        }
        
        groups = {
            "webservers": InventoryGroup(
                hosts=["web01.example.com"],
                vars={"http_port": 80},
                children=[]
            )
        }
        
        inventory = InventoryData(
            source_file="/path/to/inventory.yml",
            loaded_at="2025-08-15T12:00:00",
            total_hosts=1,
            total_groups=1,
            groups=groups,
            hosts=hosts,
            vars={"ansible_user": "deploy"}
        )
        
        assert inventory.total_hosts == 1
        assert inventory.total_groups == 1
        assert "webservers" in inventory.groups
        assert "web01.example.com" in inventory.hosts

    def test_mission_alert_creation(self):
        """Test MissionAlert model creation."""
        alert = MissionAlert(
            timestamp="2025-08-15T12:00:00",
            message="Low fuel warning"
        )
        
        assert alert.timestamp == "2025-08-15T12:00:00"
        assert alert.message == "Low fuel warning"

    def test_mission_data_creation(self):
        """Test MissionData model creation."""
        alerts = [
            MissionAlert(
                timestamp="2025-08-15T12:00:00",
                message="Mission started"
            )
        ]
        
        mission = MissionData(
            name="Test Mission",
            destination="Alpha Centauri",
            status="planning",
            start_time="2025-08-15T12:00:00",
            fuel_level=100.0,
            crew_count=5,
            distance_traveled=0.0,
            alerts=alerts
        )
        
        assert mission.name == "Test Mission"
        assert mission.destination == "Alpha Centauri"
        assert mission.fuel_level == 100.0
        assert len(mission.alerts) == 1

    def test_model_serialization(self):
        """Test Pydantic model JSON serialization."""
        activity = SessionActivity(
            timestamp="2025-08-15T12:00:00",
            action="test_action",
            request_id="req_123"
        )
        
        # Test model_dump
        data = activity.model_dump()
        assert isinstance(data, dict)
        assert data["action"] == "test_action"
        
        # Test model_dump_json
        json_str = activity.model_dump_json()
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["action"] == "test_action"

    def test_model_validation_from_dict(self):
        """Test Pydantic model validation from dictionary."""
        data = {
            "timestamp": "2025-08-15T12:00:00",
            "action": "test_action",
            "request_id": "req_123"
        }
        
        activity = SessionActivity.model_validate(data)
        assert activity.action == "test_action"
        assert activity.details is None


class TestStateManager:
    """Test StateManager functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.state_manager = StateManager()

    def test_state_manager_initialization(self):
        """Test StateManager initializes with empty state."""
        assert len(self.state_manager.list_sessions()) == 0
        assert self.state_manager.get_inventory() is None
        assert self.state_manager.get_current_mission() is None
        
        stats = self.state_manager.get_stats()
        assert stats["active_sessions"] == 0
        assert stats["inventory_loaded"] is False
        assert stats["active_mission"] is False

    def test_session_management(self):
        """Test session storage and retrieval."""
        # Create session data
        activities = [
            SessionActivity(
                timestamp="2025-08-15T12:00:00",
                action="session_started",
                request_id="req_123"
            )
        ]
        
        session = SessionData(
            session_id="session_123",
            session_name="Test Session",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=activities,
            session_data={"key": "value"}
        )
        
        # Store session
        self.state_manager.set_session("session_123", session)
        
        # Retrieve session
        retrieved = self.state_manager.get_session("session_123")
        assert retrieved is not None
        assert retrieved.session_name == "Test Session"
        assert retrieved.session_data["key"] == "value"
        
        # List sessions
        sessions = self.state_manager.list_sessions()
        assert len(sessions) == 1
        assert "session_123" in sessions

    def test_session_deletion(self):
        """Test session deletion."""
        session = SessionData(
            session_id="session_123",
            session_name="Test Session",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=[],
            session_data={}
        )
        
        self.state_manager.set_session("session_123", session)
        assert self.state_manager.get_session("session_123") is not None
        
        # Delete session
        result = self.state_manager.delete_session("session_123")
        assert result is True
        assert self.state_manager.get_session("session_123") is None
        
        # Try to delete non-existent session
        result = self.state_manager.delete_session("nonexistent")
        assert result is False

    def test_inventory_management(self):
        """Test inventory storage and retrieval."""
        # Create inventory data
        hosts = {
            "web01.example.com": InventoryHost(
                name="web01.example.com",
                vars={"ansible_host": "10.0.1.10"},
                groups=["webservers"]
            )
        }
        
        groups = {
            "webservers": InventoryGroup(
                hosts=["web01.example.com"],
                vars={"http_port": 80},
                children=[]
            )
        }
        
        inventory = InventoryData(
            source_file="/path/to/inventory.yml",
            loaded_at="2025-08-15T12:00:00",
            total_hosts=1,
            total_groups=1,
            groups=groups,
            hosts=hosts,
            vars={"ansible_user": "deploy"}
        )
        
        # Store inventory
        self.state_manager.set_inventory(inventory)
        self.state_manager.set_inventory_history(["inventory1.yml", "inventory2.yml"])
        
        # Retrieve inventory
        retrieved = self.state_manager.get_inventory()
        assert retrieved is not None
        assert retrieved.total_hosts == 1
        assert "webservers" in retrieved.groups
        
        # Test history
        history = self.state_manager.get_inventory_history()
        assert len(history) == 2
        assert "inventory1.yml" in history

    def test_inventory_clearing(self):
        """Test inventory clearing."""
        inventory = InventoryData(
            source_file="/path/to/inventory.yml",
            loaded_at="2025-08-15T12:00:00",
            total_hosts=0,
            total_groups=0,
            groups={},
            hosts={},
            vars={}
        )
        
        self.state_manager.set_inventory(inventory)
        self.state_manager.set_inventory_history(["test.yml"])
        
        assert self.state_manager.get_inventory() is not None
        assert len(self.state_manager.get_inventory_history()) == 1
        
        # Clear inventory
        self.state_manager.clear_inventory()
        assert self.state_manager.get_inventory() is None
        assert len(self.state_manager.get_inventory_history()) == 0

    def test_mission_management(self):
        """Test mission storage and retrieval."""
        # Create mission data
        alerts = [
            MissionAlert(
                timestamp="2025-08-15T12:00:00",
                message="Mission started"
            )
        ]
        
        mission = MissionData(
            name="Test Mission",
            destination="Alpha Centauri",
            status="planning",
            start_time="2025-08-15T12:00:00",
            fuel_level=100.0,
            crew_count=5,
            distance_traveled=0.0,
            alerts=alerts
        )
        
        # Store mission
        self.state_manager.set_current_mission(mission)
        self.state_manager.set_mission_history(["Mission 1", "Mission 2"])
        
        # Retrieve mission
        retrieved = self.state_manager.get_current_mission()
        assert retrieved is not None
        assert retrieved.name == "Test Mission"
        assert retrieved.fuel_level == 100.0
        assert len(retrieved.alerts) == 1
        
        # Test history
        history = self.state_manager.get_mission_history()
        assert len(history) == 2
        assert "Mission 1" in history

    def test_mission_completion(self):
        """Test mission completion workflow."""
        mission = MissionData(
            name="Test Mission",
            destination="Alpha Centauri",
            status="active",
            start_time="2025-08-15T12:00:00",
            fuel_level=50.0,
            crew_count=5,
            distance_traveled=100.0,
            alerts=[]
        )
        
        self.state_manager.set_current_mission(mission)
        
        # Complete mission
        completion_data = {
            "mission_name": "Test Mission",
            "total_distance": 100.0,
            "final_fuel": 50.0
        }
        
        self.state_manager.set_last_completed_mission(completion_data)
        self.state_manager.set_current_mission(None)
        
        assert self.state_manager.get_current_mission() is None
        retrieved_completion = self.state_manager.get_last_completed_mission()
        assert retrieved_completion["mission_name"] == "Test Mission"

    def test_generic_storage(self):
        """Test generic key-value storage."""
        # Store generic data
        self.state_manager.set_generic("test_key", {"data": "value"})
        self.state_manager.set_generic("number", 42)
        self.state_manager.set_generic("list", [1, 2, 3])
        
        # Retrieve generic data
        assert self.state_manager.get_generic("test_key")["data"] == "value"
        assert self.state_manager.get_generic("number") == 42
        assert self.state_manager.get_generic("list") == [1, 2, 3]
        assert self.state_manager.get_generic("nonexistent") is None
        assert self.state_manager.get_generic("nonexistent", "default") == "default"

    def test_generic_storage_deletion(self):
        """Test generic storage deletion."""
        self.state_manager.set_generic("test_key", "value")
        assert self.state_manager.get_generic("test_key") == "value"
        
        # Delete existing key
        result = self.state_manager.delete_generic("test_key")
        assert result is True
        assert self.state_manager.get_generic("test_key") is None
        
        # Try to delete non-existent key
        result = self.state_manager.delete_generic("nonexistent")
        assert result is False

    def test_statistics(self):
        """Test StateManager statistics."""
        # Initially empty
        stats = self.state_manager.get_stats()
        assert stats["active_sessions"] == 0
        assert stats["inventory_loaded"] is False
        assert stats["active_mission"] is False
        assert stats["generic_items"] == 0
        assert stats["total_memory_items"] == 0
        
        # Add some data
        session = SessionData(
            session_id="session_123",
            session_name="Test",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=[],
            session_data={}
        )
        self.state_manager.set_session("session_123", session)
        
        inventory = InventoryData(
            source_file="/test.yml",
            loaded_at="2025-08-15T12:00:00",
            total_hosts=0,
            total_groups=0,
            groups={},
            hosts={},
            vars={}
        )
        self.state_manager.set_inventory(inventory)
        
        self.state_manager.set_generic("key1", "value1")
        self.state_manager.set_generic("key2", "value2")
        
        # Check updated stats
        stats = self.state_manager.get_stats()
        assert stats["active_sessions"] == 1
        assert stats["inventory_loaded"] is True
        assert stats["active_mission"] is False
        assert stats["generic_items"] == 2
        assert stats["total_memory_items"] == 4  # 1 session + 1 inventory + 2 generic

    def test_json_export(self):
        """Test JSON export functionality."""
        # Add test data
        session = SessionData(
            session_id="session_123",
            session_name="Test",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=[],
            session_data={"key": "value"}
        )
        self.state_manager.set_session("session_123", session)
        
        self.state_manager.set_generic("test", {"data": "value"})
        
        # Test section exports
        sessions_json = self.state_manager.to_json("sessions")
        assert isinstance(sessions_json, str)
        sessions_data = json.loads(sessions_json)
        assert "session_123" in sessions_data
        
        generic_json = self.state_manager.to_json("generic")
        assert isinstance(generic_json, str)
        generic_data = json.loads(generic_json)
        assert generic_data["test"]["data"] == "value"
        
        # Test full export
        full_json = self.state_manager.to_json()
        assert isinstance(full_json, str)
        full_data = json.loads(full_json)
        assert "sessions" in full_data
        assert "inventory" in full_data
        assert "stats" in full_data

    def test_clear_all(self):
        """Test clearing all state data."""
        # Add some data
        session = SessionData(
            session_id="session_123",
            session_name="Test",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=[],
            session_data={}
        )
        self.state_manager.set_session("session_123", session)
        
        inventory = InventoryData(
            source_file="/test.yml",
            loaded_at="2025-08-15T12:00:00",
            total_hosts=0,
            total_groups=0,
            groups={},
            hosts={},
            vars={}
        )
        self.state_manager.set_inventory(inventory)
        
        self.state_manager.set_generic("test", "value")
        
        # Verify data exists
        assert len(self.state_manager.list_sessions()) == 1
        assert self.state_manager.get_inventory() is not None
        assert self.state_manager.get_generic("test") == "value"
        
        # Clear all
        self.state_manager.clear_all()
        
        # Verify all data is cleared
        assert len(self.state_manager.list_sessions()) == 0
        assert self.state_manager.get_inventory() is None
        assert self.state_manager.get_current_mission() is None
        assert self.state_manager.get_generic("test") is None
        
        stats = self.state_manager.get_stats()
        assert stats["total_memory_items"] == 0


class TestGlobalStateManager:
    """Test the global state_manager instance."""

    def test_global_state_manager_exists(self):
        """Test that global state_manager instance exists and is StateManager."""
        assert state_manager is not None
        assert isinstance(state_manager, StateManager)

    def test_global_state_manager_isolation(self):
        """Test that global state manager maintains isolation across tests."""
        # This test should run independently
        initial_stats = state_manager.get_stats()
        
        # The global instance might have data from other tests
        # So we just verify it's functional
        state_manager.set_generic("isolation_test", "value")
        assert state_manager.get_generic("isolation_test") == "value"
        
        # Clean up
        state_manager.delete_generic("isolation_test")
        assert state_manager.get_generic("isolation_test") is None


class TestStateManagerIntegration:
    """Integration tests for StateManager with complex scenarios."""

    def setup_method(self):
        """Set up test environment."""
        self.state_manager = StateManager()

    def test_complete_session_workflow(self):
        """Test a complete session workflow with multiple operations."""
        # Start session
        session = SessionData(
            session_id="workflow_session",
            session_name="Workflow Test",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=[
                SessionActivity(
                    timestamp="2025-08-15T12:00:00",
                    action="session_started",
                    request_id="req_1"
                )
            ],
            session_data={}
        )
        
        self.state_manager.set_session("workflow_session", session)
        
        # Add session data
        session.session_data["user_pref"] = "dark_mode"
        session.request_count += 1
        session.activities.append(
            SessionActivity(
                timestamp="2025-08-15T12:01:00",
                action="data_update",
                request_id="req_2"
            )
        )
        self.state_manager.set_session("workflow_session", session)
        
        # Verify workflow
        retrieved = self.state_manager.get_session("workflow_session")
        assert retrieved.request_count == 2
        assert len(retrieved.activities) == 2
        assert retrieved.session_data["user_pref"] == "dark_mode"

    def test_concurrent_data_management(self):
        """Test managing multiple data types simultaneously."""
        # Create session
        session = SessionData(
            session_id="concurrent_session",
            session_name="Concurrent Test",
            start_time="2025-08-15T12:00:00",
            client_id="client_123",
            request_count=1,
            last_activity="2025-08-15T12:00:00",
            activities=[],
            session_data={"key": "value"}
        )
        
        # Create mission
        mission = MissionData(
            name="Concurrent Mission",
            destination="Test System",
            status="active",
            start_time="2025-08-15T12:00:00",
            fuel_level=75.0,
            crew_count=5,
            distance_traveled=50.0,
            alerts=[]
        )
        
        # Create inventory
        inventory = InventoryData(
            source_file="/concurrent.yml",
            loaded_at="2025-08-15T12:00:00",
            total_hosts=2,
            total_groups=1,
            groups={
                "web": InventoryGroup(hosts=["web1", "web2"], vars={}, children=[])
            },
            hosts={
                "web1": InventoryHost(name="web1", vars={}, groups=["web"]),
                "web2": InventoryHost(name="web2", vars={}, groups=["web"])
            },
            vars={}
        )
        
        # Store all data
        self.state_manager.set_session("concurrent_session", session)
        self.state_manager.set_current_mission(mission)
        self.state_manager.set_inventory(inventory)
        self.state_manager.set_generic("config", {"setting": "value"})
        
        # Verify all data coexists
        assert self.state_manager.get_session("concurrent_session") is not None
        assert self.state_manager.get_current_mission() is not None
        assert self.state_manager.get_inventory() is not None
        assert self.state_manager.get_generic("config") is not None
        
        # Check stats
        stats = self.state_manager.get_stats()
        assert stats["active_sessions"] == 1
        assert stats["inventory_loaded"] is True
        assert stats["active_mission"] is True
        assert stats["generic_items"] == 1
        assert stats["total_memory_items"] == 4

    def test_data_persistence_and_modification(self):
        """Test data persistence and modification over time."""
        # Create initial mission
        mission = MissionData(
            name="Persistence Test",
            destination="Test System",
            status="planning",
            start_time="2025-08-15T12:00:00",
            fuel_level=100.0,
            crew_count=5,
            distance_traveled=0.0,
            alerts=[]
        )
        
        self.state_manager.set_current_mission(mission)
        
        # Modify mission - simulate mission progress
        mission.status = "active"
        mission.fuel_level = 80.0
        mission.distance_traveled = 25.0
        mission.alerts.append(
            MissionAlert(
                timestamp="2025-08-15T13:00:00",
                message="Course correction completed"
            )
        )
        
        self.state_manager.set_current_mission(mission)
        
        # Verify persistence of changes
        retrieved = self.state_manager.get_current_mission()
        assert retrieved.status == "active"
        assert retrieved.fuel_level == 80.0
        assert retrieved.distance_traveled == 25.0
        assert len(retrieved.alerts) == 1
        assert retrieved.alerts[0].message == "Course correction completed"

    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge cases."""
        # Test retrieving non-existent data
        assert self.state_manager.get_session("nonexistent") is None
        assert self.state_manager.get_inventory() is None
        assert self.state_manager.get_current_mission() is None
        assert self.state_manager.get_generic("nonexistent") is None
        
        # Test deleting non-existent data
        assert self.state_manager.delete_session("nonexistent") is False
        assert self.state_manager.delete_generic("nonexistent") is False
        
        # Test empty collections
        assert len(self.state_manager.list_sessions()) == 0
        assert len(self.state_manager.get_inventory_history()) == 0
        assert len(self.state_manager.get_mission_history()) == 0
        
        # Test stats with empty state
        stats = self.state_manager.get_stats()
        for key in ["active_sessions", "generic_items", "total_memory_items"]:
            assert stats[key] == 0
        for key in ["inventory_loaded", "active_mission"]:
            assert stats[key] is False