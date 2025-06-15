# app/utils/redis_cache_manager.py - Lightning Fast Caching System
import redis
import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List
from functools import wraps
import pickle

class RedisCache:
    """
    Redis Cache Manager for PBSC-Ignite
    Provides intelligent caching for all system components
    """
    
    def __init__(self):
        """Initialize Redis connection with error handling"""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=os.getenv('REDIS_PASSWORD', None) or None,
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
            
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            print("✅ Redis Cache Manager initialized successfully")
            
        except Exception as e:
            print(f"⚠️ Redis not available: {e}")
            print("🔄 Cache operations will be bypassed")
            self.redis_available = False
            self.redis_client = None
    
    def _create_cache_key(self, prefix: str, identifier: str, **kwargs) -> str:
        """Create a consistent cache key"""
        # Create a hash from kwargs for consistent keys
        if kwargs:
            params_str = json.dumps(kwargs, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            return f"pbsc:{prefix}:{identifier}:{params_hash}"
        return f"pbsc:{prefix}:{identifier}"
    
    def get(self, prefix: str, identifier: str, **kwargs) -> Optional[Any]:
        """Get cached data"""
        if not self.redis_available:
            return None
        
        try:
            cache_key = self._create_cache_key(prefix, identifier, **kwargs)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                # Try JSON first (most common)
                try:
                    return json.loads(cached_data)
                except json.JSONDecodeError:
                    # Return as string if not JSON
                    return cached_data
            
            return None
            
        except Exception as e:
            print(f"⚠️ Redis get error: {e}")
            return None
    
    def set(self, prefix: str, identifier: str, data: Any, timeout: int = 3600, **kwargs) -> bool:
        """Set cached data with timeout"""
        if not self.redis_available:
            return False
        
        try:
            cache_key = self._create_cache_key(prefix, identifier, **kwargs)
            
            # Serialize data
            if isinstance(data, (dict, list)):
                serialized_data = json.dumps(data)
            else:
                serialized_data = str(data)
            
            # Set with expiration
            return self.redis_client.setex(cache_key, timeout, serialized_data)
            
        except Exception as e:
            print(f"⚠️ Redis set error: {e}")
            return False
    
    def delete(self, prefix: str, identifier: str, **kwargs) -> bool:
        """Delete cached data"""
        if not self.redis_available:
            return False
        
        try:
            cache_key = self._create_cache_key(prefix, identifier, **kwargs)
            return bool(self.redis_client.delete(cache_key))
            
        except Exception as e:
            print(f"⚠️ Redis delete error: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self.redis_available:
            return 0
        
        try:
            keys = self.redis_client.keys(f"pbsc:{pattern}")
            if keys:
                return self.redis_client.delete(*keys)
            return 0
            
        except Exception as e:
            print(f"⚠️ Redis delete pattern error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.redis_available:
            return {"status": "unavailable"}
        
        try:
            info = self.redis_client.info('memory')
            keyspace = self.redis_client.info('keyspace')
            
            # Count PBSC keys
            pbsc_keys = len(self.redis_client.keys("pbsc:*"))
            
            return {
                "status": "available",
                "memory_used": info.get('used_memory_human', 'N/A'),
                "total_keys": pbsc_keys,
                "databases": keyspace,
                "connected_clients": self.redis_client.info().get('connected_clients', 0)
            }
            
        except Exception as e:
            return {"status": "error", "error": str(e)}

# Global cache instance
cache = RedisCache()

# Cache timeout constants (from environment or defaults)
TIMEOUT_SHORT = int(os.getenv('CACHE_TIMEOUT_SHORT', 300))      # 5 minutes
TIMEOUT_MEDIUM = int(os.getenv('CACHE_TIMEOUT_MEDIUM', 1800))   # 30 minutes
TIMEOUT_LONG = int(os.getenv('CACHE_TIMEOUT_LONG', 21600))      # 6 hours
TIMEOUT_API = int(os.getenv('CACHE_TIMEOUT_API', 43200))        # 12 hours

class ProfileCache:
    """Specialized caching for user profiles"""
    
    @staticmethod
    def get_profile_summary(user_id: str) -> Optional[str]:
        """Get cached profile summary"""
        return cache.get("profile_summary", user_id)
    
    @staticmethod
    def set_profile_summary(user_id: str, summary: str) -> bool:
        """Cache profile summary"""
        return cache.set("profile_summary", user_id, summary, TIMEOUT_MEDIUM)
    
    @staticmethod
    def get_profile_context(user_id: str, query: str = None) -> Optional[str]:
        """Get cached profile context"""
        return cache.get("profile_context", user_id, query=query)
    
    @staticmethod
    def set_profile_context(user_id: str, context: str, query: str = None) -> bool:
        """Cache profile context"""
        return cache.set("profile_context", user_id, context, TIMEOUT_SHORT, query=query)
    
    @staticmethod
    def invalidate_profile(user_id: str) -> int:
        """Clear all cached data for a user"""
        return cache.delete_pattern(f"*:{user_id}:*") + cache.delete_pattern(f"*:{user_id}")

class APICache:
    """Specialized caching for API responses"""
    
    @staticmethod
    def get_perplexity_response(query: str) -> Optional[Dict]:
        """Get cached Perplexity response"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return cache.get("perplexity", query_hash)
    
    @staticmethod
    def set_perplexity_response(query: str, response: Dict) -> bool:
        """Cache Perplexity response"""
        query_hash = hashlib.md5(query.encode()).hexdigest()
        return cache.set("perplexity", query_hash, response, TIMEOUT_API)
    
    @staticmethod
    def get_groq_response(prompt: str, model: str = "default") -> Optional[str]:
        """Get cached Groq response"""
        prompt_hash = hashlib.md5(f"{prompt}_{model}".encode()).hexdigest()
        return cache.get("groq", prompt_hash)
    
    @staticmethod
    def set_groq_response(prompt: str, response: str, model: str = "default") -> bool:
        """Cache Groq response"""
        prompt_hash = hashlib.md5(f"{prompt}_{model}".encode()).hexdigest()
        return cache.set("groq", prompt_hash, response, TIMEOUT_LONG)
    
    @staticmethod
    def get_linkedin_data(user_id: str) -> Optional[Dict]:
        """Get cached LinkedIn data"""
        return cache.get("linkedin", user_id)
    
    @staticmethod
    def set_linkedin_data(user_id: str, data: Dict) -> bool:
        """Cache LinkedIn data"""
        return cache.set("linkedin", user_id, data, TIMEOUT_API)

class SessionCache:
    """Specialized caching for user sessions"""
    
    @staticmethod
    def get_session_data(session_id: str) -> Optional[Dict]:
        """Get cached session data"""
        return cache.get("session", session_id)
    
    @staticmethod
    def set_session_data(session_id: str, data: Dict) -> bool:
        """Cache session data"""
        return cache.set("session", session_id, data, TIMEOUT_SHORT)
    
    @staticmethod
    def get_conversation_history(user_id: str, context: str) -> Optional[List]:
        """Get cached conversation history"""
        return cache.get("conversation", user_id, context=context)
    
    @staticmethod
    def set_conversation_history(user_id: str, history: List, context: str) -> bool:
        """Cache conversation history"""
        return cache.set("conversation", user_id, history, TIMEOUT_MEDIUM, context=context)

class RoadmapCache:
    """Specialized caching for roadmaps and learning plans"""
    
    @staticmethod
    def get_roadmap(user_id: str) -> Optional[Dict]:
        """Get cached roadmap"""
        return cache.get("roadmap", user_id)
    
    @staticmethod
    def set_roadmap(user_id: str, roadmap: Dict) -> bool:
        """Cache roadmap"""
        return cache.set("roadmap", user_id, roadmap, TIMEOUT_LONG)
    
    @staticmethod
    def get_learning_plan(user_id: str, phase_id: str) -> Optional[Dict]:
        """Get cached learning plan"""
        return cache.get("learning_plan", user_id, phase=phase_id)
    
    @staticmethod
    def set_learning_plan(user_id: str, phase_id: str, plan: Dict) -> bool:
        """Cache learning plan"""
        return cache.set("learning_plan", user_id, plan, TIMEOUT_LONG, phase=phase_id)

# Decorator for automatic caching
def cached_response(prefix: str, timeout: int = TIMEOUT_MEDIUM, key_func=None):
    """
    Decorator to automatically cache function responses
    
    Usage:
    @cached_response("api_call", timeout=3600)
    def expensive_api_call(param1, param2):
        return api.call(param1, param2)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Use function name and args as key
                args_str = "_".join(str(arg) for arg in args)
                kwargs_str = "_".join(f"{k}={v}" for k, v in kwargs.items())
                cache_key = f"{args_str}_{kwargs_str}" if args_str or kwargs_str else "default"
            
            # Try to get from cache
            cached_result = cache.get(prefix, cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(prefix, cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator

# Utility functions
def clear_user_cache(user_id: str) -> int:
    """Clear all cached data for a specific user"""
    patterns = [
        f"profile_*:{user_id}",
        f"profile_*:{user_id}:*",
        f"session:{user_id}",
        f"conversation:{user_id}:*",
        f"roadmap:{user_id}",
        f"learning_plan:{user_id}:*"
    ]
    
    total_deleted = 0
    for pattern in patterns:
        total_deleted += cache.delete_pattern(pattern)
    
    return total_deleted

def get_cache_health() -> Dict[str, Any]:
    """Get comprehensive cache health status"""
    stats = cache.get_stats()
    
    if stats["status"] == "available":
        # Add more detailed stats
        stats["cache_types"] = {
            "profiles": len(cache.redis_client.keys("pbsc:profile_*")) if cache.redis_available else 0,
            "api_responses": len(cache.redis_client.keys("pbsc:perplexity:*")) + len(cache.redis_client.keys("pbsc:groq:*")) if cache.redis_available else 0,
            "sessions": len(cache.redis_client.keys("pbsc:session:*")) if cache.redis_available else 0,
            "roadmaps": len(cache.redis_client.keys("pbsc:roadmap:*")) if cache.redis_available else 0
        }
    
    return stats