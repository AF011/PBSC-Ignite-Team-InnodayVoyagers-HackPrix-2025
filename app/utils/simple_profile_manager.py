# app/utils/simple_profile_manager.py - Enhanced with Redis Caching
from typing import Dict, Any, Optional
from datetime import datetime
import json
import os
from groq import Groq

# Import Redis cache manager
try:
    from app.utils.redis_cache_manager import ProfileCache, cache
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ Redis cache not available - profile operations will be slower")

class SimpleProfileManager:
    """
    Simple profile context manager - replaces complex vector database
    Gets profile data directly from MongoDB and creates intelligent summaries
    """
    
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        print("✅ Simple Profile Manager initialized")
    
    def get_complete_profile_context(self, user_id: str) -> Dict[str, Any]:
        """Get complete profile context from MongoDB with Redis caching"""
        try:
            # Try Redis cache first (if available)
            if REDIS_AVAILABLE:
                cached_context = cache.get("profile_complete", user_id)
                if cached_context:
                    print(f"✅ Profile context cache HIT for: {user_id}")
                    return cached_context
                print(f"🔄 Profile context cache MISS for: {user_id}")
            
            from app.utils.db_utils import get_db
            db = get_db()
            
            # Get user profile
            user_profile = db.users.find_one({"user_id": user_id}) or {}
            
            # Get LinkedIn data if available
            linkedin_data = db.linkedin_data.find_one({"user_id": user_id}) or {}
            
            # Combine all profile data
            complete_context = {
                "user_profile": user_profile,
                "linkedin_data": linkedin_data,
                "retrieved_at": datetime.now().isoformat()
            }
            
            # Cache in Redis for 30 minutes (if available)
            if REDIS_AVAILABLE:
                cache.set("profile_complete", user_id, complete_context, 1800)  # 30 minutes
                print(f"✅ Profile context cached for: {user_id}")
            
            print(f"✅ Complete profile context retrieved for: {user_id}")
            return complete_context
            
        except Exception as e:
            print(f"❌ Profile context retrieval error: {e}")
            return {}
    
    def create_profile_summary_template(self, user_id: str) -> str:
        """Create a structured profile summary using templates (fast)"""
        try:
            context = self.get_complete_profile_context(user_id)
            
            if not context:
                return ""
            
            user_profile = context.get("user_profile", {})
            linkedin_data = context.get("linkedin_data", {})
            
            # Build summary using templates (no AI needed - super fast!)
            summary_parts = []
            
            # Basic information
            if user_profile.get("name"):
                summary_parts.append(f"Student: {user_profile['name']}")
            
            # Career goal
            if user_profile.get("career_goal"):
                summary_parts.append(f"Career Goal: {user_profile['career_goal']}")
            
            # Dream company
            if user_profile.get("dream_company"):
                summary_parts.append(f"Target Company: {user_profile['dream_company']}")
            
            # Personal statement
            if user_profile.get("personal_statement"):
                summary_parts.append(f"Motivation: {user_profile['personal_statement']}")
            
            # Experience level
            if user_profile.get("experience_level"):
                summary_parts.append(f"Experience: {user_profile['experience_level']}")
            
            # Skills from LinkedIn
            if linkedin_data.get("skills"):
                skills_list = []
                for skill in linkedin_data["skills"][:10]:  # Top 10 skills
                    if isinstance(skill, dict):
                        skills_list.append(skill.get("name", str(skill)))
                    else:
                        skills_list.append(str(skill))
                
                if skills_list:
                    summary_parts.append(f"Key Skills: {', '.join(skills_list)}")
            
            # Experience from LinkedIn
            if linkedin_data.get("experience"):
                exp_titles = []
                for exp in linkedin_data["experience"][:3]:  # Top 3 experiences
                    if isinstance(exp, dict) and exp.get("title"):
                        exp_titles.append(exp["title"])
                
                if exp_titles:
                    summary_parts.append(f"Experience: {', '.join(exp_titles)}")
            
            # Education
            if linkedin_data.get("education"):
                education_list = []
                for edu in linkedin_data["education"][:2]:  # Top 2 education
                    if isinstance(edu, dict):
                        school = edu.get("school", "")
                        degree = edu.get("degree", "")
                        if school or degree:
                            education_list.append(f"{degree} at {school}".strip())
                
                if education_list:
                    summary_parts.append(f"Education: {', '.join(education_list)}")
            
            # Roadmap progress (if available)
            if user_profile.get("road_map"):
                try:
                    roadmap_data = json.loads(user_profile["road_map"])
                    if roadmap_data.get("phases"):
                        phase_count = len(roadmap_data["phases"])
                        summary_parts.append(f"Learning Journey: {phase_count} phases planned")
                except:
                    pass
            
            result = "\n".join(summary_parts)
            print(f"✅ Template-based profile summary created: {len(result)} chars")
            return result
            
        except Exception as e:
            print(f"❌ Template summary error: {e}")
            return ""
    
    def get_profile_summary_for_llm(self, user_id: str, max_tokens: int = 1000) -> str:
        """
        Get profile summary optimized for LLM consumption with Redis caching
        """
        try:
            # Try Redis cache first (if available)
            cache_key_params = {"max_tokens": max_tokens}
            if REDIS_AVAILABLE:
                cached_summary = cache.get("profile_summary", user_id, **cache_key_params)
                if cached_summary:
                    print(f"✅ Profile summary cache HIT for: {user_id}")
                    return cached_summary
                print(f"🔄 Profile summary cache MISS for: {user_id}")
            
            # First try template-based approach (fastest)
            template_summary = self.create_profile_summary_template(user_id)
            
            if not template_summary:
                print("⚠️ No profile data available")
                return ""
            
            # Check length (rough: 1 token ≈ 4 characters)
            estimated_tokens = len(template_summary) // 4
            
            if estimated_tokens <= max_tokens:
                summary = template_summary
                print(f"✅ Profile summary within limits: {len(summary)} chars")
            else:
                # If too long, use AI to summarize
                print(f"⚠️ Summary too long ({estimated_tokens} tokens), using AI to condense...")
                summary = self._create_condensed_summary_with_ai(template_summary, max_tokens)
            
            # Cache in Redis for 30 minutes (if available)
            if REDIS_AVAILABLE and summary:
                cache.set("profile_summary", user_id, summary, 1800, **cache_key_params)
                print(f"✅ Profile summary cached for: {user_id}")
            
            return summary
            
        except Exception as e:
            print(f"❌ Profile summary error: {e}")
            return ""
    
    def _create_condensed_summary_with_ai(self, profile_text: str, max_tokens: int) -> str:
        """Use AI to create a condensed summary when profile is too long"""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": f"Create a concise student profile summary in under {max_tokens//4} words. Focus on: career goals, key skills, experience level, and learning interests. Keep it factual and structured."
                    },
                    {
                        "role": "user", 
                        "content": profile_text[:4000]  # Limit input to avoid errors
                    }
                ],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                temperature=0.1,
                max_tokens=max_tokens//4
            )
            
            summary = response.choices[0].message.content.strip()
            print(f"✅ AI-condensed profile summary: {len(summary)} chars")
            return summary
            
        except Exception as e:
            print(f"❌ AI condensation error: {e}")
            # Fallback: truncate original text
            truncated = profile_text[:max_tokens*4]
            print(f"⚠️ Using truncated fallback: {len(truncated)} chars")
            return truncated
    
    def get_profile_context_simple(self, user_id: str, query: str = None) -> str:
        """
        Simple profile context retrieval - replaces RAG functionality
        Returns relevant profile information based on query
        """
        try:
            # Get complete profile
            complete_context = self.get_complete_profile_context(user_id)
            
            if not complete_context:
                return ""
            
            user_profile = complete_context.get("user_profile", {})
            linkedin_data = complete_context.get("linkedin_data", {})
            
            # If no specific query, return general summary
            if not query:
                return self.create_profile_summary_template(user_id)
            
            # Simple keyword matching for relevant context
            query_lower = query.lower()
            relevant_parts = []
            
            # Check what the query is asking for
            if any(word in query_lower for word in ["goal", "career", "job", "role"]):
                if user_profile.get("career_goal"):
                    relevant_parts.append(f"Career Goal: {user_profile['career_goal']}")
                if user_profile.get("dream_company"):
                    relevant_parts.append(f"Target Company: {user_profile['dream_company']}")
            
            if any(word in query_lower for word in ["skill", "technology", "programming"]):
                if linkedin_data.get("skills"):
                    skills = [str(skill.get("name", skill)) if isinstance(skill, dict) else str(skill) 
                             for skill in linkedin_data["skills"][:15]]
                    relevant_parts.append(f"Skills: {', '.join(skills)}")
            
            if any(word in query_lower for word in ["experience", "work", "background"]):
                if linkedin_data.get("experience"):
                    exp_list = []
                    for exp in linkedin_data["experience"][:5]:
                        if isinstance(exp, dict):
                            title = exp.get("title", "")
                            company = exp.get("company", "")
                            if title:
                                exp_list.append(f"{title} at {company}".strip())
                    if exp_list:
                        relevant_parts.append(f"Experience: {'; '.join(exp_list)}")
            
            if any(word in query_lower for word in ["education", "study", "learn"]):
                if linkedin_data.get("education"):
                    edu_list = []
                    for edu in linkedin_data["education"][:3]:
                        if isinstance(edu, dict):
                            school = edu.get("school", "")
                            degree = edu.get("degree", "")
                            if school or degree:
                                edu_list.append(f"{degree} at {school}".strip())
                    if edu_list:
                        relevant_parts.append(f"Education: {'; '.join(edu_list)}")
            
            # If no specific matches, return general summary
            if not relevant_parts:
                return self.create_profile_summary_template(user_id)
            
            result = "\n".join(relevant_parts)
            print(f"✅ Query-specific context retrieved: {len(result)} chars")
            return result
            
        except Exception as e:
            print(f"❌ Simple context retrieval error: {e}")
            return ""
    
    def store_profile_simple(self, user_data: Dict[str, Any]) -> bool:
        """
        Simple profile storage with Redis cache invalidation
        """
        try:
            user_id = user_data.get('user_id')
            
            if not user_id:
                print("❌ No user_id provided for profile storage")
                return False
            
            # Profile is already stored in MongoDB by main.py
            # Invalidate Redis cache for this user (if available)
            if REDIS_AVAILABLE:
                # Clear all cached profile data for this user
                patterns_cleared = 0
                patterns = [
                    f"profile_complete:{user_id}",
                    f"profile_summary:{user_id}:*",
                    f"profile_context:{user_id}:*"
                ]
                
                for pattern in patterns:
                    try:
                        if cache.delete_pattern(pattern.replace(":", "*")):
                            patterns_cleared += 1
                    except:
                        pass
                
                if patterns_cleared > 0:
                    print(f"✅ Cleared {patterns_cleared} cached entries for: {user_id}")
            
            print(f"✅ Profile storage confirmed for: {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Simple profile storage error: {e}")
            return False

# Convenience functions to replace vector database imports
def get_profile_summary_for_llm(user_id: str, max_tokens: int = 1000) -> str:
    """Get profile summary for LLM - replaces vector database function"""
    try:
        manager = SimpleProfileManager()
        return manager.get_profile_summary_for_llm(user_id, max_tokens)
    except Exception as e:
        print(f"⚠️ Profile summary failed: {e}")
        return ""

def get_profile_context_simple(user_id: str, query: str = None) -> str:
    """Get simple profile context - replaces RAG functionality"""
    try:
        manager = SimpleProfileManager()
        return manager.get_profile_context_simple(user_id, query)
    except Exception as e:
        print(f"⚠️ Profile context failed: {e}")
        return ""

def store_profile_simple(user_data: Dict[str, Any]) -> bool:
    """Simple profile storage - replaces vector database storage"""
    try:
        manager = SimpleProfileManager()
        return manager.store_profile_simple(user_data)
    except Exception as e:
        print(f"⚠️ Profile storage failed: {e}")
        return False