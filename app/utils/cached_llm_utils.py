# app/utils/cached_llm_utils.py - Enhanced LLM Functions with Redis Caching
import hashlib
import json
from typing import Dict, Any, Optional

# Import Redis cache manager
try:
    from app.utils.redis_cache_manager import APICache, cached_response, TIMEOUT_API, TIMEOUT_LONG
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis cache not available - API calls will be slower")

# Import your existing LLM functions
from app.utils.llm_utils import (
    query_perplexity_sonar,
    llama_reason_and_structure,
    get_groq_response,
    leo_ai_response as original_leo_ai_response,
    ai_mentor_response as original_ai_mentor_response
)

def cached_query_perplexity_sonar(query: str, system_message: str = None) -> Optional[str]:
    """
    Cached version of Perplexity Sonar queries
    Cache API responses for 12 hours to reduce costs
    """
    if not REDIS_AVAILABLE:
        return query_perplexity_sonar(query, system_message)
    
    try:
        # Create cache key from query and system message
        cache_content = f"{query}_{system_message or ''}"
        query_hash = hashlib.md5(cache_content.encode()).hexdigest()
        
        # Try cache first
        cached_response = APICache.get_perplexity_response(cache_content)
        if cached_response:
            print(f"✅ Perplexity cache HIT: {query[:50]}...")
            return cached_response
        
        print(f"🔄 Perplexity cache MISS: {query[:50]}...")
        
        # Make API call
        response = query_perplexity_sonar(query, system_message)
        
        # Cache response for 12 hours
        if response:
            APICache.set_perplexity_response(cache_content, response)
            print(f"✅ Perplexity response cached")
        
        return response
        
    except Exception as e:
        print(f"❌ Cached Perplexity error: {e}")
        return query_perplexity_sonar(query, system_message)

def cached_llama_reason_and_structure(prompt: str, max_tokens: int = 4000) -> Optional[str]:
    """
    Cached version of Llama reasoning
    Cache responses for 6 hours since reasoning might be reused
    """
    if not REDIS_AVAILABLE:
        return llama_reason_and_structure(prompt, max_tokens)
    
    try:
        # Create cache key from prompt
        prompt_hash = hashlib.md5(f"{prompt}_{max_tokens}".encode()).hexdigest()
        
        # Try cache first
        cached_response = APICache.get_groq_response(prompt, f"llama_{max_tokens}")
        if cached_response:
            print(f"✅ Llama reasoning cache HIT: {prompt[:50]}...")
            return cached_response
        
        print(f"🔄 Llama reasoning cache MISS: {prompt[:50]}...")
        
        # Make API call
        response = llama_reason_and_structure(prompt, max_tokens)
        
        # Cache response for 6 hours
        if response:
            APICache.set_groq_response(prompt, response, f"llama_{max_tokens}")
            print(f"✅ Llama reasoning response cached")
        
        return response
        
    except Exception as e:
        print(f"❌ Cached Llama reasoning error: {e}")
        return llama_reason_and_structure(prompt, max_tokens)

def cached_groq_response(message: str, topic: str, **kwargs) -> Optional[str]:
    """
    Cached version of Groq responses
    Cache for 6 hours for general responses
    """
    if not REDIS_AVAILABLE:
        return get_groq_response(message, topic, **kwargs)
    
    try:
        # Create cache key from message, topic, and kwargs
        cache_key_content = f"{message}_{topic}_{json.dumps(kwargs, sort_keys=True)}"
        
        # Try cache first
        cached_response = APICache.get_groq_response(cache_key_content, "groq_general")
        if cached_response:
            print(f"✅ Groq cache HIT: {message[:50]}...")
            return cached_response
        
        print(f"🔄 Groq cache MISS: {message[:50]}...")
        
        # Make API call
        response = get_groq_response(message, topic, **kwargs)
        
        # Cache response for 6 hours
        if response:
            APICache.set_groq_response(cache_key_content, response, "groq_general")
            print(f"✅ Groq response cached")
        
        return response
        
    except Exception as e:
        print(f"❌ Cached Groq error: {e}")
        return get_groq_response(message, topic, **kwargs)

def cached_leo_ai_response(prompt: str, max_tokens: int = 1500, user_profile: str = "") -> str:
    """
    Cached version of Leo AI responses
    Cache for 2 hours since career advice can be reused for similar queries
    """
    if not REDIS_AVAILABLE:
        return original_leo_ai_response(prompt, max_tokens, user_profile)
    
    try:
        # Create cache key from prompt and user profile
        cache_key_content = f"{prompt}_{user_profile[:200]}_{max_tokens}"  # Limit profile for key
        leo_hash = hashlib.md5(cache_key_content.encode()).hexdigest()
        
        # Try cache first
        cached_response = APICache.get_groq_response(cache_key_content, "leo_ai")
        if cached_response:
            print(f"✅ Leo AI cache HIT: {prompt[:50]}...")
            return cached_response
        
        print(f"🔄 Leo AI cache MISS: {prompt[:50]}...")
        
        # Make API call
        response = original_leo_ai_response(prompt, max_tokens, user_profile)
        
        # Cache response for 2 hours (career advice changes less frequently)
        if response:
            APICache.set_groq_response(cache_key_content, response, "leo_ai")
            print(f"✅ Leo AI response cached")
        
        return response
        
    except Exception as e:
        print(f"❌ Cached Leo AI error: {e}")
        return original_leo_ai_response(prompt, max_tokens, user_profile)

def cached_ai_mentor_response(message: str, topic: str, objectives: list = None, 
                            skills: list = None, conversation_context: list = None, 
                            student_profile: str = "") -> str:
    """
    Cached version of AI Mentor responses
    Cache for 1 hour since tutoring responses can be reused
    """
    if not REDIS_AVAILABLE:
        return original_ai_mentor_response(message, topic, objectives, skills, conversation_context, student_profile)
    
    try:
        # Create cache key (limit context for reasonable key size)
        cache_data = {
            "message": message,
            "topic": topic,
            "objectives": objectives[:3] if objectives else [],  # Limit to first 3
            "skills": skills[:5] if skills else [],  # Limit to first 5
            "student_profile": student_profile[:200]  # Limit profile length
        }
        cache_key_content = json.dumps(cache_data, sort_keys=True)
        
        # Try cache first
        cached_response = APICache.get_groq_response(cache_key_content, "ai_mentor")
        if cached_response:
            print(f"✅ AI Mentor cache HIT: {message[:50]}...")
            return cached_response
        
        print(f"🔄 AI Mentor cache MISS: {message[:50]}...")
        
        # Make API call
        response = original_ai_mentor_response(
            message, topic, objectives, skills, conversation_context, student_profile
        )
        
        # Cache response for 1 hour
        if response:
            APICache.set_groq_response(cache_key_content, response, "ai_mentor")
            print(f"✅ AI Mentor response cached")
        
        return response
        
    except Exception as e:
        print(f"❌ Cached AI Mentor error: {e}")
        return original_ai_mentor_response(message, topic, objectives, skills, conversation_context, student_profile)

# Enhanced roadmap generation with caching
def cached_enhanced_roadmap_generation(user_id: str, topic: str, profile_summary: str = "") -> dict:
    """
    Cached version of enhanced roadmap generation
    Cache roadmaps for 24 hours since they don't change frequently
    """
    if not REDIS_AVAILABLE:
        # Import here to avoid circular imports
        from app.utils.llm_utils import get_enhanced_roadmap_with_multi_level_perplexity
        return get_enhanced_roadmap_with_multi_level_perplexity(user_id, topic, profile_summary)
    
    try:
        # Import here to avoid circular imports
        from app.utils.redis_cache_manager import RoadmapCache
        
        # Check for cached roadmap first
        cached_roadmap = RoadmapCache.get_roadmap(user_id)
        if cached_roadmap:
            print(f"✅ Roadmap cache HIT for: {user_id}")
            return cached_roadmap
        
        print(f"🔄 Roadmap cache MISS for: {user_id}")
        
        # Generate new roadmap using cached API calls
        from app.utils.llm_utils import get_enhanced_roadmap_with_multi_level_perplexity
        
        # Replace API calls in the roadmap generation with cached versions
        # This requires modifying the original function to use our cached versions
        roadmap = get_enhanced_roadmap_with_multi_level_perplexity(user_id, topic, profile_summary)
        
        # Cache the generated roadmap for 24 hours
        if roadmap:
            RoadmapCache.set_roadmap(user_id, roadmap)
            print(f"✅ Roadmap cached for: {user_id}")
        
        return roadmap
        
    except Exception as e:
        print(f"❌ Cached roadmap generation error: {e}")
        from app.utils.llm_utils import get_enhanced_roadmap_with_multi_level_perplexity
        return get_enhanced_roadmap_with_multi_level_perplexity(user_id, topic, profile_summary)

# Cache statistics and management
def get_api_cache_stats() -> Dict[str, Any]:
    """Get API cache statistics"""
    if not REDIS_AVAILABLE:
        return {"status": "Redis not available"}
    
    try:
        from app.utils.redis_cache_manager import cache
        
        # Count different types of cached API responses
        perplexity_keys = len(cache.redis_client.keys("pbsc:perplexity:*")) if cache.redis_available else 0
        groq_keys = len(cache.redis_client.keys("pbsc:groq:*")) if cache.redis_available else 0
        
        return {
            "status": "available",
            "perplexity_cached_responses": perplexity_keys,
            "groq_cached_responses": groq_keys,
            "total_api_cache_entries": perplexity_keys + groq_keys,
            "estimated_api_calls_saved": perplexity_keys + groq_keys
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

def clear_api_cache() -> int:
    """Clear all API response caches"""
    if not REDIS_AVAILABLE:
        return 0
    
    try:
        from app.utils.redis_cache_manager import cache
        
        patterns = ["perplexity:*", "groq:*"]
        total_cleared = 0
        
        for pattern in patterns:
            total_cleared += cache.delete_pattern(pattern)
        
        print(f"✅ Cleared {total_cleared} API cache entries")
        return total_cleared
        
    except Exception as e:
        print(f"❌ Error clearing API cache: {e}")
        return 0

# Export cached versions as the main functions
# This allows easy switching between cached and non-cached versions
query_perplexity_sonar_cached = cached_query_perplexity_sonar
llama_reason_and_structure_cached = cached_llama_reason_and_structure
get_groq_response_cached = cached_groq_response
leo_ai_response_cached = cached_leo_ai_response
ai_mentor_response_cached = cached_ai_mentor_response
get_enhanced_roadmap_cached = cached_enhanced_roadmap_generation