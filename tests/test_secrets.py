"""Tests for secrets management functionality."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastmcp import Client

from ftl_mcp.secrets import SecretsManager, SecretMetadata


class TestSecretsManager:
    """Tests for SecretsManager class."""
    
    def test_secrets_manager_initialization(self):
        """Test SecretsManager initialization."""
        manager = SecretsManager()
        
        assert manager._secrets is not None
        assert manager._metadata is not None
        assert manager._encryption_key is not None
    
    def test_set_and_get_secret(self):
        """Test setting and getting a secret."""
        manager = SecretsManager()
        
        # Set a secret
        success = manager.set_secret("test_key", "test_value", "Test secret")
        assert success is True
        
        # Get the secret
        value = manager.get_secret("test_key")
        assert value == "test_value"
        
        # Check if secret exists
        assert manager.has_secret("test_key") is True
        assert manager.has_secret("nonexistent") is False
    
    def test_secret_metadata(self):
        """Test secret metadata functionality."""
        manager = SecretsManager()
        
        # Set a secret with metadata
        manager.set_secret("meta_test", "value", "Description", ["tag1", "tag2"])
        
        # Get metadata
        metadata = manager.get_secret_metadata("meta_test")
        assert metadata is not None
        assert metadata.name == "meta_test"
        assert metadata.description == "Description"
        assert "tag1" in metadata.tags
        assert "tag2" in metadata.tags
    
    def test_list_secret_names(self):
        """Test listing secret names."""
        manager = SecretsManager()
        
        # Add some secrets
        manager.set_secret("secret1", "value1")
        manager.set_secret("secret2", "value2")
        
        names = manager.list_secret_names()
        assert "secret1" in names
        assert "secret2" in names
    
    def test_case_insensitive_access(self):
        """Test that secret access is case-insensitive."""
        manager = SecretsManager()
        
        manager.set_secret("TestKey", "test_value")
        
        assert manager.get_secret("testkey") == "test_value"
        assert manager.get_secret("TESTKEY") == "test_value"
        assert manager.has_secret("testkey") is True
    
    @patch.dict(os.environ, {"FTL_SECRET_API_KEY": "secret_api_key"})
    def test_load_from_environment(self):
        """Test loading secrets from environment variables."""
        manager = SecretsManager()
        
        # Should have loaded from environment
        assert manager.has_secret("api_key") is True
        assert manager.get_secret("api_key") == "secret_api_key"
        
        # Check metadata
        metadata = manager.get_secret_metadata("api_key")
        assert metadata is not None
        assert "environment" in metadata.tags
    
    def test_get_stats(self):
        """Test getting statistics about secrets."""
        manager = SecretsManager()
        
        manager.set_secret("test1", "value1", tags=["runtime"])
        manager.set_secret("test2", "value2", tags=["runtime", "test"])
        
        stats = manager.get_stats()
        assert stats["total_secrets"] >= 2
        assert "runtime" in stats["tags"]
        assert stats["has_encryption_key"] is True
    
    def test_encryption_key_generation(self):
        """Test encryption key generation and encoding."""
        manager = SecretsManager()
        
        key_b64 = manager.get_encryption_key_b64()
        assert isinstance(key_b64, str)
        assert len(key_b64) > 0


class TestSecretsManagerIntegration:
    """Integration tests for secrets manager with MCP server."""
    
    @pytest.mark.asyncio
    async def test_get_secrets_status_empty(self):
        """Test getting secrets status when no secrets are loaded."""
        from src.ftl_mcp.server import mcp
        
        async with Client(mcp) as client:
            result = await client.call_tool("get_secrets_status", {})
            
            assert result.data["status"] == "success"
            assert "statistics" in result.data
            assert "secrets" in result.data
            assert "loading_instructions" in result.data
    
    
    @pytest.mark.asyncio
    async def test_check_nonexistent_secret(self):
        """Test checking for a nonexistent secret."""
        from src.ftl_mcp.server import mcp
        
        async with Client(mcp) as client:
            result = await client.call_tool("check_secret_exists", {
                "name": "nonexistent_secret"
            })
            
            assert result.data["exists"] is False
            assert result.data["secret_name"] == "nonexistent_secret"
            assert "metadata" not in result.data
    
    
    @pytest.mark.asyncio 
    async def test_secrets_status_basic_functionality(self):
        """Test basic secrets status functionality."""
        from src.ftl_mcp.server import mcp
        
        async with Client(mcp) as client:
            # Get status (should work even with no secrets)
            result = await client.call_tool("get_secrets_status", {})
            
            assert result.data["status"] == "success"
            assert "statistics" in result.data
            assert "secrets" in result.data
            assert "loading_instructions" in result.data
            
            # Check loading instructions are present
            instructions = result.data["loading_instructions"]
            assert "environment_variables" in instructions
            assert "encrypted_file" in instructions


class TestSecretIntegrationWithAnsible:
    """Test secrets integration with Ansible execution."""
    
    @pytest.mark.asyncio
    async def test_ssh_credentials_integration(self):
        """Test that SSH credentials from secrets are used in inventory."""
        from src.ftl_mcp.server import mcp
        from src.ftl_mcp.ftl_integration import FTLExecutor
        from src.ftl_mcp.secrets import secrets_manager
        
        # Set SSH credentials directly in secrets manager
        secrets_manager.set_secret("ssh_user", "testuser")
        secrets_manager.set_secret("ssh_key_file", "/path/to/key.pem")
        
        try:
            # Create FTL executor and test inventory creation
            executor = FTLExecutor()
            inventory = executor._create_basic_inventory(["test.example.com"])
            
            # Check that SSH credentials are included
            assert inventory["all"]["vars"]["ansible_user"] == "testuser"
            assert inventory["all"]["vars"]["ansible_ssh_private_key_file"] == "/path/to/key.pem"
            
        finally:
            # Clean up secrets to avoid affecting other tests
            if "ssh_user" in secrets_manager._secrets:
                del secrets_manager._secrets["ssh_user"]
                del secrets_manager._metadata["ssh_user"]
            if "ssh_key_file" in secrets_manager._secrets:
                del secrets_manager._secrets["ssh_key_file"]
                del secrets_manager._metadata["ssh_key_file"]


class TestSecretsReload:
    """Test secrets reload functionality."""
    
    def test_reload_secrets_basic(self):
        """Test basic reload functionality."""
        manager = SecretsManager()
        
        # Add some secrets first
        manager.set_secret("runtime_secret", "runtime_value", "Runtime secret", ["runtime"])
        
        # Add a mock environment secret manually to simulate loaded state
        manager._secrets["env_secret"] = "env_value"
        manager._metadata["env_secret"] = SecretMetadata(
            name="env_secret",
            description="Environment secret",
            created_at="2023-01-01T00:00:00",
            updated_at="2023-01-01T00:00:00",
            tags=["environment"]
        )
        
        initial_count = len(manager._secrets)
        
        # Reload secrets
        result = manager.reload_secrets()
        
        # Check results
        assert result["status"] == "success"
        assert result["initial_count"] == initial_count
        
        # All secrets should be cleared and only external sources reloaded
        assert not manager.has_secret("runtime_secret")  # Runtime secrets are not preserved
        assert not manager.has_secret("env_secret")      # Mock env secret gone (not in actual environment)
    
    @patch.dict(os.environ, {"FTL_SECRET_RELOAD_TEST": "new_env_value"})
    def test_reload_with_environment_changes(self):
        """Test reloading when environment variables change."""
        manager = SecretsManager()
        
        # Should have loaded the environment variable
        assert manager.has_secret("reload_test")
        assert manager.get_secret("reload_test") == "new_env_value"
        
        # Add a runtime secret
        manager.set_secret("runtime_secret", "runtime_value", "Runtime secret", ["runtime"])
        
        initial_count = len(manager._secrets)
        
        # Reload secrets
        result = manager.reload_secrets()
        
        # Check that environment secret is still there but runtime secret is gone
        assert result["status"] == "success"
        assert manager.has_secret("reload_test")
        assert manager.get_secret("reload_test") == "new_env_value"
        assert not manager.has_secret("runtime_secret")  # Runtime secrets not preserved
        
        # Check that environment secret is properly tagged
        metadata = manager.get_secret_metadata("reload_test")
        assert metadata is not None
        assert "environment" in metadata.tags


class TestReloadSecretsMCP:
    """Test reload_secrets MCP tool integration."""
    
    @pytest.mark.asyncio
    async def test_reload_secrets_mcp_tool(self):
        """Test reload_secrets MCP tool."""
        from src.ftl_mcp.server import mcp
        
        async with Client(mcp) as client:
            result = await client.call_tool("reload_secrets", {})
            
            assert result.data["status"] == "success"
            assert "reload_summary" in result.data
            assert "message" in result.data
            
            summary = result.data["reload_summary"]
            assert "initial_secret_count" in summary
            assert "final_secret_count" in summary
            assert "reloaded_from_environment" in summary
            assert "reloaded_from_encrypted_file" in summary
    
    @patch.dict(os.environ, {"FTL_SECRET_MCP_TEST": "mcp_test_value"})
    @pytest.mark.asyncio
    async def test_reload_secrets_mcp_with_environment(self):
        """Test reload_secrets MCP tool with environment variables."""
        from src.ftl_mcp.server import mcp
        
        async with Client(mcp) as client:
            result = await client.call_tool("reload_secrets", {})
            
            assert result.data["status"] == "success"
            
            # Check that environment secret was loaded
            summary = result.data["reload_summary"]
            assert summary["reloaded_from_environment"] >= 1
            
            # Verify the secret exists (using check_secret_exists tool)
            check_result = await client.call_tool("check_secret_exists", {"name": "mcp_test"})
            assert check_result.data["exists"] is True