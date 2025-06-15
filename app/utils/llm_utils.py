# app/utils/llm_utils.py - FIXED Debug Version
import os
import json
import requests
from groq import Groq
import google.generativeai as genai
from markdown2 import Markdown
from dotenv import load_dotenv
from datetime import datetime
import hashlib
import re
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

markdowner = Markdown()

# Configure Gemini API (keeping for backward compatibility)
GENMI_API_KEY = os.getenv("GENMI_API_KEY")
if GENMI_API_KEY:
    genai.configure(api_key=GENMI_API_KEY)

# Groq configuration - Your exact model
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# Perplexity configuration
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")
PERPLEXITY_URL = "https://api.perplexity.ai/chat/completions"

class CommonMetadataManager:
    """Manage common metadata across all databases"""
    
    @staticmethod
    def generate_metadata(user_id: str, career_goal: str, enhancements: dict) -> dict:
        """Generate common metadata for all databases"""
        return {
            "user_id": user_id,
            "career_goal": career_goal,
            "generated_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "version": "1.0",
            "enhanced_with": enhancements,
            "source": "multi_level_perplexity",
            "profile_hash": hashlib.md5(f"{user_id}_{career_goal}".encode()).hexdigest()
        }
    
    @staticmethod
    def update_metadata(existing_meta: dict) -> dict:
        """Update existing metadata"""
        existing_meta["updated_at"] = datetime.now().isoformat()
        current_version = existing_meta.get("version", "1.0")
        version_parts = current_version.split(".")
        version_parts[1] = str(int(version_parts[1]) + 1)
        existing_meta["version"] = ".".join(version_parts)
        return existing_meta

def clean_json_response(response_text: str) -> str:
    """Clean JSON response from Llama - ROBUST cleaning"""
    try:
        # Print raw response for debugging
        print(f"🔍 Raw response preview: {response_text[:200]}...")
        
        # Remove common prefixes
        prefixes_to_remove = [
            "Here is a", "Here's a", "Based on", "I'll create",
            "Creating a", "Let me create", "The following is"
        ]
        
        for prefix in prefixes_to_remove:
            if response_text.startswith(prefix):
                # Find the first '{' after the prefix
                json_start = response_text.find('{')
                if json_start != -1:
                    response_text = response_text[json_start:]
                break
        
        # Remove markdown code blocks - ENHANCED cleaning
        patterns = [
            r'```json\s*\n?',  # Opening ```json
            r'```\s*$',        # Closing ```
            r'^```.*?\n',      # Any line starting with ```
            r'\n```.*?$',      # Any line ending with ```
        ]
        
        for pattern in patterns:
            response_text = re.sub(pattern, '', response_text, flags=re.MULTILINE)
        
        # Remove any remaining markdown artifacts
        response_text = response_text.strip()
        
        # Find JSON boundaries more robustly
        first_brace = response_text.find('{')
        last_brace = response_text.rfind('}')
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            json_content = response_text[first_brace:last_brace + 1]
            print(f"🔍 Extracted JSON: {json_content[:100]}...")
            return json_content
        
        print(f"⚠️ No valid JSON boundaries found")
        return response_text
        
    except Exception as e:
        print(f"❌ JSON cleaning error: {e}")
        return response_text

def query_perplexity_sonar(query: str, system_prompt: str = None, focus: str = "technical") -> str:
    """Universal Perplexity Sonar query function - OBSERVE, DON'T REASON"""
    try:
        if not PERPLEXITY_API_KEY:
            print("⚠️ No Perplexity API key found")
            return None
            
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt or "You are an industry data observer. Provide current, factual information from real-time sources. Focus on observing trends and data, not reasoning or analysis."
                },
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "temperature": 0.1,  # Low temperature for factual observation
            "top_p": 0.8,
            "return_images": False,
            "return_related_questions": False,
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1,
            "web_search_options": {
                "search_context_size": "medium",
                "focus": focus
            },
            "max_tokens": 2500
        }
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print(f"🔍 Querying Perplexity Sonar: {query[:50]}...")
        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                print(f"✅ Perplexity response: {len(content)} characters")
                return content
        else:
            print(f"❌ Perplexity error: {response.status_code} - {response.text}")
            
        return None
        
    except Exception as e:
        print(f"❌ Perplexity query error: {e}")
        return None

def llama_reason_and_structure(prompt: str, max_tokens: int = 3000) -> str:
    """Use Llama to REASON and STRUCTURE - ENHANCED with better JSON handling"""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # Enhanced prompt for better JSON output
        enhanced_prompt = f"""{prompt}

CRITICAL FORMATTING REQUIREMENTS:
- Return ONLY valid JSON
- Do NOT include any explanatory text before or after the JSON
- Do NOT use markdown code blocks (no ```)
- Start directly with {{ and end with }}
- Ensure all quotes are properly escaped
- Validate JSON structure before responding"""
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON response generator. Return ONLY valid JSON without any markdown formatting, explanations, or code blocks. Your response must start with { and end with }."
                },
                {
                    "role": "user",
                    "content": enhanced_prompt
                }
            ],
            model=MODEL,
            temperature=0.1,  # Lower temperature for more consistent JSON
            max_tokens=max_tokens
        )
        
        raw_response = response.choices[0].message.content.strip()
        print(f"🔍 Llama output length: {len(raw_response)} chars")
        print(f"🔍 Llama output preview: {raw_response[:200]}...")
        
        return raw_response
        
    except Exception as e:
        print(f"❌ Llama reasoning error: {e}")
        return None

def check_token_limit(text: str, max_tokens: int = 4000) -> tuple:
    """Check if text exceeds token limit (rough: 1 token ≈ 4 characters)"""
    estimated_tokens = len(text) // 4
    exceeds_limit = estimated_tokens > max_tokens
    return exceeds_limit, estimated_tokens

def get_enhanced_roadmap_with_multi_level_perplexity(user_id: str, topic: str, profile_summary: str = "") -> dict:
    """
    Level 1: Enhanced roadmap generation - FIXED VERSION
    Perplexity OBSERVES → Llama REASONS & STRUCTURES
    """
    try:
        print(f"🚀 Level 1: Multi-level roadmap generation for {topic}")
        
        # Step 1: Perplexity OBSERVES current industry trends (no reasoning)
        perplexity_query = f"""What are the current industry trends, job market demands, essential skills, and learning requirements for {topic} in 2025?

Observe and report factual data about:
- Most in-demand skills and technologies
- Current job market requirements
- Industry growth areas and opportunities
- Popular tools and platforms being used
- Recent developments and emerging trends
- Salary ranges and career progression paths
- Common career paths and specializations

Student background for context: {profile_summary[:300]}

Provide factual, current information from reliable sources."""

        system_prompt = "You are an industry data observer with access to real-time information. Report current facts, trends, and data without analysis or reasoning. Focus on observing what IS happening in the industry right now."
        
        perplexity_response = query_perplexity_sonar(perplexity_query, system_prompt)
        
        if not perplexity_response:
            print("⚠️ Perplexity failed, using fallback")
            return get_roadmap_from_groq(topic)
        
        print("✅ Perplexity industry observation complete")
        
        # Step 2: Check token limits for Llama input
        combined_input = f"Profile: {profile_summary}\n\nIndustry Data: {perplexity_response}"
        exceeds_limit, token_count = check_token_limit(combined_input, max_tokens=6000)
        
        if exceeds_limit:
            print(f"⚠️ Input too long ({token_count} tokens), summarizing profile")
            # Summarize profile to fit
            profile_summary = profile_summary[:500] + "..." if len(profile_summary) > 500 else profile_summary
        
        # Step 3: Llama REASONS and STRUCTURES the roadmap - ENHANCED PROMPT
        llama_prompt = f"""Create a structured learning roadmap for {topic} based on current industry trends.

STUDENT BACKGROUND:
{profile_summary}

CURRENT INDUSTRY DATA:
{perplexity_response[:2000]}

Create exactly 4 phases with this structure:
{{
    "phases": [
        {{
            "name": "Phase Name",
            "duration": "X-Y months",
            "description": "Description incorporating current trends",
            "skills": ["skill1", "skill2", "skill3"],
            "resources": {{
                "Online Courses": ["Course 1", "Course 2"],
                "Books": ["Book 1", "Book 2"],
                "Tools": ["Tool 1", "Tool 2"]
            }}
        }}
    ]
}}"""

        print(f"🔍 Llama input length: {len(llama_prompt)} chars")
        print(f"🔍 Llama input preview: {llama_prompt[:200]}...")
        
        llama_response = llama_reason_and_structure(llama_prompt, max_tokens=4000)
        
        if not llama_response:
            print("⚠️ Llama structuring failed, using fallback")
            return get_roadmap_from_groq(topic)
        
        # ENHANCED JSON cleaning and parsing
        cleaned_response = clean_json_response(llama_response)
        
        try:
            roadmap_data = json.loads(cleaned_response)
            print("✅ JSON parsed successfully")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"❌ Raw response: {llama_response[:500]}...")
            
            # Try alternative cleaning
            try:
                # Last resort: extract JSON using regex
                json_match = re.search(r'\{.*\}', llama_response, re.DOTALL)
                if json_match:
                    potential_json = json_match.group(0)
                    roadmap_data = json.loads(potential_json)
                    print("✅ JSON extracted with regex")
                else:
                    raise ValueError("No JSON found")
            except:
                print("❌ All JSON parsing attempts failed, using fallback")
                return get_roadmap_from_groq(topic)
        
        # Add metadata
        enhancements = {
            "level_1_perplexity_observe": True,
            "level_1_llama_reason": True,
            "level_2_detailed_tasks": False,
            "level_3_enhanced_resources": False,
            "industry_trends_integrated": True
        }
        
        roadmap_data["metadata"] = CommonMetadataManager.generate_metadata(
            user_id=user_id,
            career_goal=topic,
            enhancements=enhancements
        )
        
        print("✅ Level 1 complete: Enhanced roadmap with industry trends")
        return roadmap_data
        
    except Exception as e:
        print(f"❌ Level 1 error: {e}")
        return get_roadmap_from_groq(topic)

def generate_detailed_learning_plan_with_perplexity(phase_name: str, skills: list, phase_description: str = "", user_profile: str = "") -> dict:
    """
    Level 2: Detailed learning plan generation - FIXED VERSION
    Perplexity OBSERVES detailed learning paths → Llama STRUCTURES into weekly format
    """
    try:
        print(f"🚀 Level 2: Detailed learning plan for {phase_name}")
        
        skills_str = ', '.join(skills)
        
        # Step 1: Perplexity OBSERVES detailed learning approaches
        perplexity_query = f"""What are the current best practices, learning methods, daily activities, and study approaches for mastering these skills: {skills_str}

Phase focus: {phase_name}
Phase description: {phase_description}

Observe and report factual information about:
- Most effective learning sequences and methods
- Daily practice activities and exercises
- Current online resources and platforms
- Hands-on projects and practical applications
- Time estimates for different learning activities
- Assessment methods and milestones
- Common learning challenges and solutions
- Industry-recommended study schedules

Student context: {user_profile[:200]}

Focus on current, practical learning approaches that work in 2025."""

        system_prompt = "You are a learning methodology observer. Report current best practices, effective learning methods, and practical approaches without analysis. Focus on what learning approaches are proven to work."
        
        perplexity_response = query_perplexity_sonar(perplexity_query, system_prompt, focus="educational")
        
        if not perplexity_response:
            print("⚠️ Perplexity failed for detailed plan, using fallback")
            return generate_learning_plan(phase_name, skills)
        
        print("✅ Perplexity learning methodology observation complete")
        
        # Step 2: Check token limits
        combined_input = f"Profile: {user_profile}\n\nPhase: {phase_name}\n\nSkills: {skills_str}\n\nLearning Methods: {perplexity_response}"
        exceeds_limit, token_count = check_token_limit(combined_input, max_tokens=6000)
        
        if exceeds_limit:
            print(f"⚠️ Input too long ({token_count} tokens), summarizing")
            perplexity_response = perplexity_response[:2000] + "..." if len(perplexity_response) > 2000 else perplexity_response
        
        # Step 3: Llama STRUCTURES into weekly schedule
        llama_prompt = f"""Create a weekly learning schedule for {phase_name} with skills: {skills_str}

LEARNING METHODS DATA:
{perplexity_response[:1500]}

Create 4-6 weeks with daily tasks:
{{
    "weekly_schedule": [
        {{
            "week": 1,
            "learning_objectives": ["Objective 1", "Objective 2"],
            "daily_tasks": [
                {{
                    "day": 1,
                    "tasks": ["Task 1", "Task 2"],
                    "resources": ["Resource 1"],
                    "duration_hours": 2
                }}
            ],
            "assessment": "Weekly project"
        }}
    ]
}}"""

        llama_response = llama_reason_and_structure(llama_prompt, max_tokens=5000)
        
        if not llama_response:
            print("⚠️ Llama structuring failed, using fallback")
            return generate_learning_plan(phase_name, skills)
        
        # Clean and parse JSON
        cleaned_response = clean_json_response(llama_response)
        
        try:
            learning_plan = json.loads(cleaned_response)
            print("✅ Level 2 complete: Detailed learning plan generated")
            return learning_plan
        except json.JSONDecodeError as e:
            print(f"❌ Learning plan JSON error: {e}")
            return generate_learning_plan(phase_name, skills)
        
    except Exception as e:
        print(f"❌ Level 2 error: {e}")
        return generate_learning_plan(phase_name, skills)

def enhance_roadmap_resources_with_perplexity(roadmap_data: dict) -> dict:
    """
    Level 3: Resource enhancement - FIXED VERSION
    Perplexity OBSERVES current resources → Llama ORGANIZES and INTEGRATES
    """
    try:
        print("🚀 Level 3: Enhancing resources with current recommendations")
        
        # Extract information from roadmap
        all_skills = []
        all_topics = []
        
        for phase in roadmap_data.get('phases', []):
            all_skills.extend(phase.get('skills', []))
            all_topics.append(phase.get('name', ''))
        
        skills_str = ', '.join(set(all_skills))
        topics_str = ', '.join(all_topics)
        
        # Step 1: Perplexity OBSERVES current resource landscape
        perplexity_query = f"""What are the current best learning resources, tools, and materials available for these topics and skills in 2025?

LEARNING TOPICS: {topics_str}
KEY SKILLS: {skills_str}

Observe and report current information about:
- Top-rated online courses and platforms (with specific names)
- Recently published books and learning materials
- Current industry-standard tools and software
- Active practice platforms and coding challenges
- Valuable certifications and credentials
- Helpful communities and forums
- Free and paid learning options
- Mobile apps and learning tools

Focus on resources that are:
- Currently available and accessible
- Highly rated and recommended
- Updated for 2025 standards
- Suitable for different learning levels"""

        system_prompt = "You are a learning resource observer. Report current, specific learning resources without analysis. Focus on what resources are actually available and recommended right now."
        
        perplexity_response = query_perplexity_sonar(perplexity_query, system_prompt, focus="educational")
        
        if not perplexity_response:
            print("⚠️ Resource enhancement failed, keeping original")
            return roadmap_data
        
        print("✅ Perplexity resource observation complete")
        
        # Step 2: Llama ORGANIZES and INTEGRATES resources
        llama_prompt = f"""Enhance this roadmap with specific resources from the research data.

RESOURCE DATA:
{perplexity_response[:2000]}

ROADMAP TO ENHANCE:
{json.dumps(roadmap_data, indent=2)[:2000]}

Return the complete enhanced roadmap with improved resources."""

        llama_response = llama_reason_and_structure(llama_prompt, max_tokens=6000)
        
        if not llama_response:
            print("⚠️ Resource structuring failed, keeping original")
            return roadmap_data
        
        # Clean and parse
        cleaned_response = clean_json_response(llama_response)
        
        try:
            enhanced_roadmap = json.loads(cleaned_response)
            
            # Update metadata
            if "metadata" in enhanced_roadmap:
                enhanced_roadmap["metadata"]["enhanced_with"]["level_3_enhanced_resources"] = True
                enhanced_roadmap["metadata"] = CommonMetadataManager.update_metadata(enhanced_roadmap["metadata"])
            
            print("✅ Level 3 complete: Resources enhanced with current recommendations")
            return enhanced_roadmap
            
        except json.JSONDecodeError as e:
            print(f"❌ Resource enhancement JSON error: {e}")
            return roadmap_data
        
    except Exception as e:
        print(f"❌ Level 3 error: {e}")
        return roadmap_data

# LinkedIn fetching with 15-day caching
def fetch_linkedin_profile(linkedin_url, user_id):
    """LinkedIn data fetching with 15-day caching to save API limits"""
    from app.utils.db_utils import get_db
    db = get_db()
    students_collection = db["linkedin_data"]
    users_collection = db["users"]
    
    # Check 15-day cache
    try:
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data and user_data.get('linkedin_last_fetched'):
            last_fetched = datetime.fromisoformat(user_data['linkedin_last_fetched'])
            days_since_fetch = (datetime.now() - last_fetched).days
            
            if days_since_fetch < 15:
                print(f"✅ LinkedIn cached ({days_since_fetch} days old)")
                existing_profile = students_collection.find_one({"user_id": user_id})
                if existing_profile:
                    return {"status": "success", "message": f"Using cached LinkedIn data for {user_id}"}
            else:
                print(f"⏰ LinkedIn data expired ({days_since_fetch} days), fetching fresh")
    except Exception as e:
        print(f"⚠️ LinkedIn cache check error: {e}")
    
    # Fresh fetch
    print(f"🔄 Fetching fresh LinkedIn data for: {user_id}")
    
    url = "https://linkedin-data-api.p.rapidapi.com/get-profile-data-by-url"
    querystring = {"url": linkedin_url}
    headers = {
        'x-rapidapi-key': os.getenv("LINKEDIN_API_KEY"),
        "x-rapidapi-host": "linkedin-data-api.p.rapidapi.com"
    }    

    try:
        response = requests.get(url, headers=headers, params=querystring)

        if response.status_code == 200:
            profile_data = response.json()
            profile_data["user_id"] = user_id

            existing_profile = students_collection.find_one({"user_id": user_id})

            if existing_profile:
                students_collection.update_one(
                    {"user_id": user_id},
                    {"$set": profile_data}
                )
                message = f"LinkedIn data updated for {user_id}"
            else:                
                students_collection.insert_one(profile_data)
                message = f"LinkedIn data saved for {user_id}"
            
            # Update timestamp
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"linkedin_last_fetched": datetime.now().isoformat()}}
            )
            
            print(f"✅ Fresh LinkedIn data cached for: {user_id}")
            return {"status": "success", "message": message}
        else:
            return {"status": "error", "message": f"LinkedIn API error: {response.status_code}"}
    except Exception as e:
        return {"status": "error", "message": f"LinkedIn fetch error: {str(e)}"}

# Your existing functions (maintained for backward compatibility)
def get_roadmap_from_groq(topic):
    """Original function maintained as fallback"""
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = f"""Create a structured learning roadmap for {topic} in this exact JSON format:
    {{
        "phases": [
            {{
                "name": "Phase Name",
                "duration": "X-Y months",
                "description": "Brief description",
                "skills": ["skill1", "skill2", "skill3"],
                "resources": {{
                    "Category1": ["Resource1", "Resource2"],
                    "Category2": ["Resource3", "Resource4"],
                    "Category3": ["Resource5", "Resource6"]
                }}
            }}
        ]
    }}
    Include exactly 4 phases. Return ONLY the JSON without any markdown formatting or code blocks."""

    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "You are a technical expert. Respond with valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        model=MODEL,
        temperature=0.1,
        max_tokens=2000
    )
    
    content = response.choices[0].message.content.strip()
    
    # Use the enhanced cleaning function
    cleaned_content = clean_json_response(content)
    
    try:
        return json.loads(cleaned_content)
    except json.JSONDecodeError as e:
        print(f"Fallback roadmap generation error: {e}")
        return {
            "phases": [{
                "name": f"Getting Started with {topic}",
                "duration": "1-3 months", 
                "description": f"Learn the fundamentals of {topic}",
                "skills": ["Basic skills"],
                "resources": {"Online Courses": ["Recommended courses"]}
            }]
        }

def generate_learning_plan(phase_name, skills):
    """Original function maintained as fallback"""
    client = Groq(api_key=GROQ_API_KEY)
    
    skills_str = ', '.join(skills)
    prompt = f"""Generate learning plan for {phase_name} phase with skills: {skills_str}. Return pure JSON:
            {{
                "weekly_schedule": [
                    {{
                        "week": 1,
                        "learning_objectives": ["Objective 1", "Objective 2"],
                        "daily_tasks": [
                            {{
                                "day": 1,
                                "tasks": ["Task 1", "Task 2"],
                                "resources": ["Resource 1"],
                                "duration_hours": 2
                            }}
                        ],
                        "assessment": "Project description"
                    }}
                ]
            }}"""

    response = client.chat.completions.create(
        messages=[{"role": "system", "content": "Return valid JSON only"},
                 {"role": "user", "content": prompt}],
        model=MODEL,
        temperature=0
    )
    
    raw_response = response.choices[0].message.content.strip()
    cleaned_response = clean_json_response(raw_response)
    
    try:
        return json.loads(cleaned_response)
    except json.JSONDecodeError:
        # Ultra-fallback
        return {
            "weekly_schedule": [{
                "week": 1,
                "learning_objectives": [f"Learn {phase_name} basics"],
                "daily_tasks": [{
                    "day": 1,
                    "tasks": ["Study fundamentals"],
                    "resources": ["Online resources"],
                    "duration_hours": 2
                }],
                "assessment": "Practice exercises"
            }]
        }

def fetch_github_projects(github_username):
    """Your existing GitHub function"""
    github_api_url = f"https://api.github.com/users/{github_username}/repos"
    try:
        response = requests.get(github_api_url)
        response.raise_for_status()
        repos = response.json()
        projects = [{"title": repo["name"], "description": repo["description"] or "No description available"} 
                    for repo in repos]
        return projects
    except requests.RequestException as e:
        return f"Error fetching GitHub data: {e}"

# ONLY THESE TWO FUNCTIONS NEED TO BE REPLACED in your llm_utils.py

# REPLACE THESE TWO FUNCTIONS in your llm_utils.py

# 🚀 UPDATED: Leo AI - Wholesome Career Companion with Citations and Profile Context
# Replace your leo_ai_response function in llm_utils.py with this FIXED version

# COMPLETELY REPLACE your leo_ai_response function with this version
# This version forces text output and handles JSON responses

def leo_ai_response(prompt, max_tokens=1500, user_profile=""):
    """
    Leo Career Coach AI response - GUARANTEED to return text format with citations
    """
    try:
        print("🦁 Leo AI starting with FORCED TEXT OUTPUT...")
        
        # Use Perplexity directly with text-focused prompting
        career_query = f"""
        You are Leo 🦁, a friendly career coach having a conversation. Respond in natural, 
        conversational text format to this career question:

        {prompt}
        
        Student Context: {user_profile[:400]}
        
        Write a warm, encouraging response that includes:
        - Current industry insights and job market trends
        - Specific, actionable career advice
        - Practical next steps
        - Use emojis naturally in conversation
        - Structure with bullet points and numbered lists in markdown
        
        Write as if you're talking directly to the student - friendly, supportive, and practical.
        Keep it conversational and under 350 words.
        """
        
        # Direct Perplexity call with conversation focus
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "You are Leo, a friendly career coach. Respond in natural conversational text format. Do NOT return JSON. Write as if you're having a friendly conversation."
                },
                {
                    "role": "user",
                    "content": career_query
                }
            ],
            "temperature": 0.6,
            "top_p": 0.9,
            "return_images": False,
            "return_related_questions": False,
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1,
            "web_search_options": {"search_context_size": "medium"},
            "max_tokens": max_tokens
        }
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print("🔍 Querying Perplexity directly for Leo...")
        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # Check if response is JSON format and convert to text
                if content.strip().startswith('{') and content.strip().endswith('}'):
                    print("⚠️ Got JSON response, converting to text format...")
                    try:
                        json_data = json.loads(content)
                        content = convert_json_to_text(json_data)
                    except:
                        print("❌ Failed to parse JSON, using Groq fallback")
                        return get_groq_leo_response(prompt, max_tokens)
                
                # Add citations if available
                if 'citations' in result and result['citations']:
                    content += "\n\n**Sources:** "
                    for i, citation_url in enumerate(result['citations'][:5], 1):
                        content += f"[{i}] {citation_url} "
                
                print(f"✅ Leo response (text format): {len(content)} chars")
                print(f"🔍 Preview: {content[:200]}...")
                
                return content
            else:
                print("❌ No choices in Perplexity response")
                return get_groq_leo_response(prompt, max_tokens)
        else:
            print(f"❌ Perplexity API error: {response.status_code}")
            return get_groq_leo_response(prompt, max_tokens)
            
    except Exception as e:
        print(f"❌ Leo AI error: {e}")
        return get_groq_leo_response(prompt, max_tokens)

def convert_json_to_text(json_data):
    """
    Convert JSON response to natural text format for Leo
    """
    try:
        text_response = ""
        
        # Start with greeting/message
        if 'message' in json_data:
            text_response += json_data['message'] + "\n\n"
        
        # Add main content
        if 'content' in json_data:
            text_response += json_data['content'] + "\n\n"
        
        # Add industry trends
        if 'currentIndustryTrends' in json_data:
            text_response += "**🔥 Current Industry Trends:**\n"
            for trend in json_data['currentIndustryTrends']:
                text_response += f"- {trend}\n"
            text_response += "\n"
        
        # Add key skills
        if 'keySkills' in json_data:
            text_response += "**💻 Key Skills to Focus On:**\n"
            for skill in json_data['keySkills']:
                text_response += f"- {skill}\n"
            text_response += "\n"
        
        # Add career advancement strategies
        if 'careerAdvancementStrategies' in json_data:
            text_response += "**🚀 Career Advancement Strategies:**\n"
            for strategy in json_data['careerAdvancementStrategies']:
                text_response += f"- {strategy}\n"
            text_response += "\n"
        
        # Add interview tips
        if 'interviewPreparationTips' in json_data:
            text_response += "**📝 Interview Preparation Tips:**\n"
            for tip in json_data['interviewPreparationTips']:
                text_response += f"- {tip}\n"
            text_response += "\n"
        
        # Add next steps
        if 'nextSteps' in json_data:
            text_response += "**⏭️ Next Steps:**\n"
            for step in json_data['nextSteps']:
                text_response += f"- {step}\n"
            text_response += "\n"
        
        # Add encouragement
        if 'encouragement' in json_data:
            text_response += json_data['encouragement'] + "\n\n"
        
        # Add sources
        if 'sources' in json_data:
            text_response += "**Sources:** "
            for i, source in enumerate(json_data['sources'][:5], 1):
                text_response += f"[{i}] {source} "
        
        return text_response.strip()
        
    except Exception as e:
        print(f"❌ JSON to text conversion error: {e}")
        return "Hey there! 🦁 I'm having some trouble formatting my response right now, but I'm still here to help with your career journey!"

def get_groq_leo_response(prompt, max_tokens):
    """
    Enhanced Groq fallback with better prompting to avoid JSON
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # Very explicit prompt to avoid JSON
        leo_prompt = f"""
        You are Leo 🦁, a friendly career coach. Have a natural conversation with this student.
        
        Student's situation: {prompt}
        
        Instructions:
        - Write in natural conversation format (like texting a friend)
        - Do NOT use JSON format
        - Do NOT structure as an object
        - Use emojis naturally
        - Give practical career advice
        - Keep it friendly and encouraging
        - Write in paragraphs and bullet points
        - End with encouragement
        
        Just write a normal, friendly response like you're chatting with the student.
        """
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are Leo, a friendly career coach. Write in natural text format like a conversation. Never use JSON format. Write like you're texting a friend."
                },
                {
                    "role": "user",
                    "content": leo_prompt
                }
            ],
            model=MODEL,
            temperature=0.8,  # Higher for more natural conversation
            max_tokens=max_tokens//2
        )
        
        result = response.choices[0].message.content.strip()
        
        # Double-check it's not JSON
        if result.startswith('{') and result.endswith('}'):
            print("⚠️ Groq also returned JSON, forcing text conversion...")
            return "Hey there! 👋🦁 I'm Leo, and I'm excited to help you with your career journey! Based on what you've shared, you're on a great track. Let me give you some practical advice to help you reach your ML engineering goals. What specific area would you like to focus on first? I'm here to support you every step of the way! 🚀"
        
        print(f"✅ Groq fallback response: {len(result)} chars")
        return result
        
    except Exception as e:
        print(f"❌ Groq Leo fallback error: {e}")
        return "Hey there! 👋🦁 I'm Leo, your career coach! I'm having some technical difficulties right now, but I'm still here to help you succeed. Could you try asking your question again? I'm committed to supporting your career journey! 🚀💪"
    

def get_groq_leo_response(prompt, max_tokens):
    """Fallback Leo response using only Groq"""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        leo_prompt = f"""
        You are Leo 🦁, an enthusiastic career coach. Respond to this conversation in a friendly, 
        supportive manner with practical career advice.
        
        {prompt}
        
        Be encouraging, use emojis naturally, and provide actionable advice. Write in natural 
        conversational text format - NOT JSON. Keep under 300 words.
        """
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are Leo, a friendly career coach. Be enthusiastic, supportive, and practical. Write in natural text format."
                },
                {
                    "role": "user",
                    "content": leo_prompt
                }
            ],
            model=MODEL,
            temperature=0.7,
            max_tokens=max_tokens//2
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Groq Leo fallback error: {e}")
        return "Hey there! 👋 I'm having some technical difficulties right now, but I'm still here to help with your career journey! Could you try asking your question again? 🚀"

def format_leo_citations(leo_response, perplexity_data):
    """
    Format Leo's response to include proper citations
    
    Args:
        leo_response (str): Leo's response from Groq
        perplexity_data (str): Original Perplexity response with sources
        
    Returns:
        str: Formatted response with proper citations
    """
    try:
        import re
        
        # Extract URLs from Perplexity response
        url_pattern = r'https?://[^\s\]]+(?:[^\s\]\)])*'
        urls = re.findall(url_pattern, perplexity_data)
        
        # Remove duplicates and clean URLs
        unique_urls = []
        seen_domains = set()
        
        for url in urls:
            # Clean URL (remove trailing punctuation)
            clean_url = re.sub(r'[.,;:\])\}]+$', '', url)
            
            # Extract domain to avoid duplicates from same site
            try:
                domain = urlparse(clean_url).netloc.lower()
                
                if domain not in seen_domains and len(clean_url) > 10:
                    unique_urls.append(clean_url)
                    seen_domains.add(domain)
                    
                    if len(unique_urls) >= 5:  # Limit to 5 sources
                        break
            except:
                continue
        
        # If Leo's response already has **Sources:** section, replace it
        if "**Sources:**" in leo_response:
            # Remove existing sources section
            leo_response = re.sub(r'\*\*Sources:\*\*.*?(?=\n\n|\n$|$)', '', leo_response, flags=re.DOTALL).strip()
        
        # Add formatted sources if we have URLs
        if unique_urls:
            sources_section = "\n\n**Sources:** "
            for i, url in enumerate(unique_urls, 1):
                sources_section += f"[{i}] {url} "
            
            leo_response += sources_section
        
        return leo_response
        
    except Exception as e:
        print(f"⚠️ Citation formatting error: {e}")
        return leo_response  # Return original response if formatting fails
    

# 🚀 UPDATED: AI Mentor - Educational Tutor with Citations, Links, and Profile Context
def ai_mentor_response(message, topic, objectives, skills, resources, conversation_context=[], user_profile=None):
    """
    🎓 AI Mentor - Educational tutor with current information, citations, source links, and user profile context
    """
    try:
        if not PERPLEXITY_API_KEY:
            print("❌ No Perplexity API key - AI Mentor falling back to Groq")
            # Groq fallback
            client = Groq(api_key=GROQ_API_KEY)
            
            resources_str = ""
            for category, items in resources.items():
                resources_str += f"{category}: {', '.join(items)}\n"
            
            system_prompt = f"""You are an AI tutor specializing in {topic}. 
            
            Current context:
            - Topic: {topic}
            - Learning Objectives: {', '.join(objectives)}
            - Key Skills: {', '.join(skills)}
            
            Available Resources:
            {resources_str}
            
            Provide educational, supportive responses that help students learn effectively."""
            
            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_context:
                for msg in conversation_context[-5:]:  # Last 5 messages
                    messages.append(msg)
            
            messages.append({"role": "user", "content": message})
            
            response = client.chat.completions.create(
                messages=messages,
                model=MODEL,
                temperature=0.5,
                max_tokens=1200  # Increased token limit
            )
            
            return response.choices[0].message.content.strip()
        
        # Format resources
        resources_str = ""
        for category, items in resources.items():
            resources_str += f"{category}: {', '.join(items)}\n"
        
        # Format recent conversation context
        recent_context = ""
        if conversation_context:
            recent_messages = conversation_context[-4:]  # Last 4 messages
            for msg in recent_messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')[:120]  # Increased context
                recent_context += f"{role.title()}: {content}\n"
        
        # Add user profile context for personalized tutoring
        profile_context = ""
        if user_profile:
            profile_context = f"""
STUDENT BACKGROUND & PROFILE:
{user_profile[:600]}

Use this context to personalize your teaching approach and examples.
"""                    

        # Enhanced AI Mentor prompt - Educational focus with MORE current references
        mentor_prompt = f"""You are an AI Mentor 🎓 specializing in {topic}. You help students learn effectively with the most current, accurate, and well-sourced information available.

{profile_context}

LEARNING CONTEXT:
- Topic: {topic}
- Learning Objectives: {', '.join(objectives)}
- Key Skills to Develop: {', '.join(skills)}

AVAILABLE RESOURCES:
{resources_str}

RECENT CONVERSATION:
{recent_context}

STUDENT QUESTION: {message}

As an AI Mentor, provide comprehensive guidance with HEAVY emphasis on current information:

📚 **Current Educational Content**: Use the latest learning approaches, methodologies, and industry-standard practices
🔄 **Latest Trends & Standards**: Actively reference current industry developments, new tools, frameworks, and best practices
💡 **Real-World Examples**: Provide current, practical examples from 2024-2025 industry applications
📊 **Current Data & Statistics**: Include recent market data, adoption rates, salary trends, and industry reports when relevant
🎯 **Up-to-Date Technologies**: Reference the latest versions, tools, frameworks, and platforms currently being used
🌟 **Industry Insights**: Share current hiring trends, skill demands, and what companies are actually looking for right now
📈 **Market Context**: Explain how current market conditions affect learning priorities and career paths
🔍 **Evidence-Based Learning**: Cite current research, studies, and proven methodologies for effective learning

CRITICAL: For {topic}, make sure to reference:
- Current industry standards and best practices
- Latest tools, frameworks, and technologies being used in 2025
- Recent developments and updates in the field
- Current job market demands and trends
- What leading companies are doing right now
- Recent case studies and real-world applications

Provide educational guidance that's not just theoretically sound, but also practically relevant to today's industry landscape. Help the student learn {topic} with context about why it matters RIGHT NOW in the current market."""
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {"role": "user", "content": mentor_prompt}
            ],
            "temperature": 0.2,  # Lower for more educational accuracy
            "top_p": 0.9,
            "return_images": False,
            "return_related_questions": False,
            "top_k": 0,
            "stream": False,
            "presence_penalty": 0,
            "frequency_penalty": 1,
            "web_search_options": {"search_context_size": "medium"},
            "max_tokens": 1400  # Increased token limit for detailed explanations
        }
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        print(f"🎓 AI Mentor querying Perplexity: {message[:50]}...")
        response = requests.post(PERPLEXITY_URL, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                
                # 🚀 ADD CITATION LINKS if available
                if 'citations' in result and result['citations']:
                    content += "\n\n**📖 Sources & References:**\n"
                    for i, citation_url in enumerate(result['citations'][:6]):  # Max 6 citations for mentor
                        # Clean URL display
                        domain = citation_url.split('/')[2] if '//' in citation_url else citation_url
                        content += f"[{i+1}] [{domain}]({citation_url})\n"
                
                print(f"✅ AI Mentor response with auto-citations and links")
                return content
            else:
                print("❌ No choices in Perplexity response for AI Mentor")
                return "I'm having trouble accessing current educational information right now. Could you please rephrase your question? I'm here to help you learn! 🎓"
        else:
            print(f"❌ Perplexity API error for AI Mentor: {response.status_code}")
            return "I'm experiencing some technical difficulties with accessing current learning resources. Please try your question again - I want to make sure you get the best educational guidance! 📚"
            
    except Exception as e:
        print(f"❌ AI Mentor Perplexity error: {e}")
        return "I'm having trouble accessing current educational resources right now. Please try asking your learning question again - I'm committed to helping you succeed! 🎓✨"


def get_groq_leo_response(prompt, max_tokens):
    """Fallback Leo response using only Groq"""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        leo_prompt = f"""
        You are Leo 🦁, an enthusiastic career coach. Respond to this conversation in a friendly, 
        supportive manner with practical career advice.
        
        {prompt}
        
        Be encouraging, use emojis naturally, and provide actionable advice. Keep under {max_tokens//4} words.
        """
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are Leo, a friendly career coach. Be enthusiastic, supportive, and practical."
                },
                {
                    "role": "user",
                    "content": leo_prompt
                }
            ],
            model=MODEL,
            temperature=0.7,
            max_tokens=max_tokens//2
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Groq Leo fallback error: {e}")
        return "Hey there! 👋 I'm having some technical difficulties right now, but I'm still here to help with your career journey! Could you try asking your question again? 🚀"

def format_leo_citations(leo_response, perplexity_data):
    """
    Format Leo's response to include proper citations
    
    Args:
        leo_response (str): Leo's response from Groq
        perplexity_data (str): Original Perplexity response with sources
        
    Returns:
        str: Formatted response with proper citations
    """
    try:
        import re
        
        # Extract URLs from Perplexity response
        url_pattern = r'https?://[^\s\]]+(?:[^\s\]\)])*'
        urls = re.findall(url_pattern, perplexity_data)
        
        # Remove duplicates and clean URLs
        unique_urls = []
        seen_domains = set()
        
        for url in urls:
            # Clean URL (remove trailing punctuation)
            clean_url = re.sub(r'[.,;:\])\}]+$', '', url)
            
            # Extract domain to avoid duplicates from same site
            try:
                from urllib.parse import urlparse
                domain = urlparse(clean_url).netloc.lower()
                
                if domain not in seen_domains and len(clean_url) > 10:
                    unique_urls.append(clean_url)
                    seen_domains.add(domain)
                    
                    if len(unique_urls) >= 8:  # Limit to 8 sources max
                        break
            except:
                continue
        
        # If Leo's response already has **Sources:** section, replace it
        if "**Sources:**" in leo_response:
            # Remove existing sources section
            leo_response = re.sub(r'\*\*Sources:\*\*.*?(?=\n\n|\n$|$)', '', leo_response, flags=re.DOTALL).strip()
        
        # Add formatted sources if we have URLs
        if unique_urls:
            sources_section = "\n\n**Sources:** "
            for i, url in enumerate(unique_urls, 1):
                sources_section += f"[{i}] {url} "
            
            leo_response += sources_section
        
        return leo_response
        
    except Exception as e:
        print(f"⚠️ Citation formatting error: {e}")
        return leo_response  # Return original response if formatting fails

# Also add this import at the top of your llm_utils.py if not already present
# from urllib.parse import urlparse


# Replace or add this function in your llm_utils.py

def get_groq_response(message, topic, objectives, skills, resources, conversation_context=[]):
    """
    Get AI tutor response using Groq API - FIXED to return text format
    
    Args:
        message (str): The user's message
        topic (str): The current topic being discussed
        objectives (list): Learning objectives for the current module
        skills (list): Skills for the current phase
        resources (dict): Resources for the current phase
        conversation_context (list): List of previous messages for context
        
    Returns:
        str: AI response in text format
    """
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # Format resources into a readable string
        resources_str = ""
        for category, items in resources.items():
            resources_str += f"{category}: {', '.join(items)}\n"
        
        # Prepare system prompt
        system_prompt = f"""You are an AI tutor specializing in {topic}. 
        
        You are currently helping the student with the following:
        - Topic: {topic}
        - Learning Objectives: {', '.join(objectives)}
        - Key Skills: {', '.join(skills)}
        
        Available Learning Resources:
        {resources_str}
        
        Your role is to:
        1. Answer questions about the topic in an educational manner
        2. Explain concepts clearly and thoroughly
        3. Provide practical examples and applications
        4. Suggest additional resources when appropriate
        5. Encourage critical thinking and problem-solving
        6. If the student seems to be struggling, break down complex topics into simpler components
        7. Maintain a supportive, patient, and encouraging tone
        
        Do not:
        - Provide incorrect information
        - Go off-topic from the learning objectives
        - Write extremely long responses (keep them concise but educational)
        - Return JSON format - respond in natural conversational text
        
        Write in an engaging educational style that's friendly but professional.
        """
        
        # Prepare messages including conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation context (previous messages)
        if conversation_context:
            for msg in conversation_context[-6:]:  # Last 6 messages for context
                messages.append(msg)
        
        # Add the current user message
        messages.append({"role": "user", "content": message})
        
        # Get response from Groq
        response = client.chat.completions.create(
            messages=messages,
            model=MODEL,
            temperature=0.5,
            max_tokens=1000
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        print(f"✅ AI Tutor response generated: {len(ai_response)} characters")
        print(f"🔍 Response preview: {ai_response[:150]}...")
        
        return ai_response
        
    except Exception as e:
        print(f"❌ AI Tutor Groq error: {e}")
        return "I'm having trouble processing your question right now. Could you please try asking again? I'm here to help you learn! 🎓"

# Also make sure you have this function for Gemini fallback
def get_gemini_response(prompt, tokens=8192):
    """Get a response from Gemini API - FIXED to return text format"""
    try:
        if not GENMI_API_KEY:
            print("⚠️ No Gemini API key, using Groq fallback")
            return get_groq_fallback_response(prompt, tokens)
            
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro-latest",
            generation_config={
                "temperature": 0.5,
                "top_p": 0.95,
                "max_output_tokens": tokens,
            },
        )
        convo = model.start_chat(history=[])
        response = convo.send_message(prompt)
        
        result = response.text.strip()
        print(f"✅ Gemini response: {len(result)} characters")
        
        return result
        
    except Exception as e:
        print(f"❌ Gemini error: {e}")
        return get_groq_fallback_response(prompt, tokens)

def get_groq_fallback_response(prompt, tokens):
    """Fallback response using Groq when Gemini fails"""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        response = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Provide clear, informative responses in natural text format."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            model=MODEL,
            temperature=0.5,
            max_tokens=min(tokens, 2000)
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"❌ Groq fallback error: {e}")
        return "I'm experiencing technical difficulties. Please try your question again."