import hashlib
import json
from typing import Any, Optional
from django.core.cache import cache
from django.db import models


class IdempotencyKey:
    """
    Idempotency key manager for preventing duplicate operations
    """
    
    def __init__(self, prefix: str = 'idempotent'):
        self.prefix = prefix
    
    def generate_key(self, *args, **kwargs) -> str:
        """
        Generate an idempotency key from arguments
        
        Args:
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            Idempotency key string
        """
        # Combine all arguments
        data = {
            'args': args,
            'kwargs': kwargs
        }
        
        # Convert to stable JSON string
        json_str = json.dumps(data, sort_keys=True)
        
        # Generate hash
        hash_value = hashlib.sha256(json_str.encode()).hexdigest()
        
        return f"{self.prefix}:{hash_value}"
    
    def check_and_set(
        self, 
        key: str, 
        value: Any = True, 
        ttl: int = 3600
    ) -> bool:
        """
        Check if key exists and set if not (atomic operation)
        
        Args:
            key: Idempotency key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if key was set (operation should proceed)
            False if key existed (operation already performed)
        """
        # Try to add key (will fail if exists)
        return cache.add(key, value, ttl)
    
    def get(self, key: str) -> Optional[Any]:
        """Get value for idempotency key"""
        return cache.get(key)
    
    def delete(self, key: str) -> None:
        """Delete idempotency key"""
        cache.delete(key)


class IdempotentOperation(models.Model):
    """
    Database-backed idempotent operations for critical operations
    """
    key = models.CharField(max_length=255, unique=True, db_index=True)
    operation = models.CharField(max_length=100)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['key', 'operation']),
            models.Index(fields=['created_at']),
        ]