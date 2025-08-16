"""Secure secrets management for FTL MCP server.

This module provides secure storage and retrieval of sensitive data like
API keys, passwords, and tokens. Secrets are never logged or exposed to
MCP clients like Claude Code.
"""

import os
import base64
import json
from pathlib import Path
from typing import Dict, Optional, Any
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field

from .tools import get_current_time as _get_current_time


class SecretMetadata(BaseModel):
    """Metadata for a stored secret."""
    name: str
    description: str = ""
    created_at: str
    updated_at: str
    tags: list[str] = Field(default_factory=list)


class SecretsManager:
    """Secure secrets manager that hides sensitive data from MCP clients.
    
    Secrets are loaded from:
    1. Environment variables (most secure)
    2. Encrypted files (secondary)
    3. External secret services (future)
    
    Secrets are NEVER exposed through MCP tools or logged.
    """
    
    def __init__(self):
        self._secrets: Dict[str, str] = {}
        self._metadata: Dict[str, SecretMetadata] = {}
        self._encryption_key: Optional[bytes] = None
        self._load_encryption_key()
        self._load_secrets()
    
    def _load_encryption_key(self):
        """Load or generate encryption key for file-based secrets."""
        key_env = os.getenv("FTL_MCP_ENCRYPTION_KEY")
        if key_env:
            try:
                self._encryption_key = base64.urlsafe_b64decode(key_env.encode())
            except Exception:
                # Generate new key if invalid
                self._encryption_key = Fernet.generate_key()
        else:
            # Generate new key
            self._encryption_key = Fernet.generate_key()
    
    def _load_secrets(self):
        """Load secrets from various sources."""
        self._load_from_environment()
        self._load_from_encrypted_file()
    
    def _load_from_environment(self):
        """Load secrets from environment variables.
        
        Environment variables with FTL_SECRET_ prefix are loaded as secrets.
        Example: FTL_SECRET_API_KEY=secret_value
        """
        current_time = _get_current_time()
        
        for env_var, value in os.environ.items():
            if env_var.startswith("FTL_SECRET_"):
                secret_name = env_var[11:].lower()  # Remove FTL_SECRET_ prefix
                self._secrets[secret_name] = value
                self._metadata[secret_name] = SecretMetadata(
                    name=secret_name,
                    description=f"Loaded from environment variable {env_var}",
                    created_at=current_time,
                    updated_at=current_time,
                    tags=["environment", "auto-loaded"]
                )
    
    def _load_from_encrypted_file(self):
        """Load secrets from encrypted file if it exists."""
        secrets_file = Path.home() / ".ftl_mcp_secrets.enc"
        if not secrets_file.exists():
            return
        
        try:
            fernet = Fernet(self._encryption_key)
            encrypted_data = secrets_file.read_bytes()
            decrypted_data = fernet.decrypt(encrypted_data)
            secrets_data = json.loads(decrypted_data.decode())
            
            current_time = _get_current_time()
            
            for secret_name, secret_info in secrets_data.items():
                if isinstance(secret_info, dict):
                    self._secrets[secret_name] = secret_info["value"]
                    self._metadata[secret_name] = SecretMetadata(
                        name=secret_name,
                        description=secret_info.get("description", ""),
                        created_at=secret_info.get("created_at", current_time),
                        updated_at=secret_info.get("updated_at", current_time),
                        tags=secret_info.get("tags", ["encrypted-file"])
                    )
                else:
                    # Legacy format - just the value
                    self._secrets[secret_name] = secret_info
                    self._metadata[secret_name] = SecretMetadata(
                        name=secret_name,
                        description="Loaded from encrypted file",
                        created_at=current_time,
                        updated_at=current_time,
                        tags=["encrypted-file", "legacy"]
                    )
        except Exception:
            # Silently fail - don't expose decryption errors
            pass
    
    def get_secret(self, name: str) -> Optional[str]:
        """Get a secret value by name.
        
        Args:
            name: Secret name (case-insensitive)
            
        Returns:
            Secret value or None if not found
        """
        return self._secrets.get(name.lower())
    
    def has_secret(self, name: str) -> bool:
        """Check if a secret exists.
        
        Args:
            name: Secret name (case-insensitive)
            
        Returns:
            True if secret exists
        """
        return name.lower() in self._secrets
    
    def list_secret_names(self) -> list[str]:
        """List all secret names (safe to expose).
        
        Returns:
            List of secret names
        """
        return list(self._secrets.keys())
    
    def get_secret_metadata(self, name: str) -> Optional[SecretMetadata]:
        """Get metadata for a secret (safe to expose).
        
        Args:
            name: Secret name (case-insensitive)
            
        Returns:
            Secret metadata or None if not found
        """
        return self._metadata.get(name.lower())
    
    def set_secret(self, name: str, value: str, description: str = "", tags: list[str] = None) -> bool:
        """Set a secret value (for runtime configuration).
        
        Args:
            name: Secret name
            value: Secret value
            description: Optional description
            tags: Optional tags
            
        Returns:
            True if successful
        """
        current_time = _get_current_time()
        secret_name = name.lower()
        
        self._secrets[secret_name] = value
        self._metadata[secret_name] = SecretMetadata(
            name=secret_name,
            description=description,
            created_at=current_time,
            updated_at=current_time,
            tags=tags or ["runtime"]
        )
        return True
    
    def save_to_encrypted_file(self) -> bool:
        """Save secrets to encrypted file.
        
        Returns:
            True if successful
        """
        try:
            secrets_data = {}
            for name, value in self._secrets.items():
                metadata = self._metadata.get(name)
                if metadata and "environment" not in metadata.tags:
                    # Don't save environment variables to file
                    secrets_data[name] = {
                        "value": value,
                        "description": metadata.description,
                        "created_at": metadata.created_at,
                        "updated_at": metadata.updated_at,
                        "tags": metadata.tags
                    }
            
            fernet = Fernet(self._encryption_key)
            json_data = json.dumps(secrets_data, indent=2).encode()
            encrypted_data = fernet.encrypt(json_data)
            
            secrets_file = Path.home() / ".ftl_mcp_secrets.enc"
            secrets_file.write_bytes(encrypted_data)
            return True
        except Exception:
            return False
    
    def get_encryption_key_b64(self) -> str:
        """Get the encryption key as base64 string for environment variable.
        
        Returns:
            Base64 encoded encryption key
        """
        return base64.urlsafe_b64encode(self._encryption_key).decode()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored secrets (safe to expose).
        
        Returns:
            Dictionary with secret statistics
        """
        tag_counts = {}
        source_counts = {"environment": 0, "encrypted-file": 0, "runtime": 0}
        
        for metadata in self._metadata.values():
            for tag in metadata.tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
                if tag in source_counts:
                    source_counts[tag] += 1
        
        return {
            "total_secrets": len(self._secrets),
            "sources": source_counts,
            "tags": tag_counts,
            "has_encryption_key": self._encryption_key is not None
        }
    
    def reload_secrets(self) -> Dict[str, Any]:
        """Reload secrets from environment variables and encrypted files.
        
        This method clears all existing secrets and reloads them fresh from
        environment variables and encrypted files.
        
        Returns:
            Dict with reload results including counts of loaded secrets
        """
        # Track initial state
        initial_count = len(self._secrets)
        
        # Clear all secrets
        self._secrets.clear()
        self._metadata.clear()
        
        # Reload from sources
        self._load_secrets()
        
        # Calculate results
        final_count = len(self._secrets)
        
        return {
            "status": "success",
            "initial_count": initial_count,
            "final_count": final_count,
            "reloaded_environment": len([name for name in self._secrets.keys() 
                                       if self._metadata.get(name) and "environment" in self._metadata[name].tags]),
            "reloaded_encrypted_file": len([name for name in self._secrets.keys() 
                                          if self._metadata.get(name) and "encrypted-file" in self._metadata[name].tags])
        }


# Global secrets manager instance
secrets_manager = SecretsManager()


def get_secret(name: str) -> Optional[str]:
    """Convenience function to get a secret.
    
    Args:
        name: Secret name
        
    Returns:
        Secret value or None if not found
    """
    return secrets_manager.get_secret(name)


def has_secret(name: str) -> bool:
    """Convenience function to check if secret exists.
    
    Args:
        name: Secret name
        
    Returns:
        True if secret exists
    """
    return secrets_manager.has_secret(name)