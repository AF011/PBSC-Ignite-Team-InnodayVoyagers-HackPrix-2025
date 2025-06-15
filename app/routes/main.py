# app/routes/main.py - Clean Version with Redis Caching
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import requests
from datetime import datetime
import json
import os
from app.utils.db_utils import get_user_by_id

# ENHANCED: Import the multi-level system
from app.utils.llm_utils import (
    get_roadmap_from_groq,  # Fallback
    fetch_linkedin_profile  # LinkedIn with caching
)

# Import enhanced profile manager with Redis caching
from app.utils.simple_profile_manager import (
    store_profile_simple,          # Simple storage with cache invalidation
    get_profile_summary_for_llm    # Now includes Redis caching
)

# Import cached LLM functions for better performance
try:
    from app.utils.cached_llm_utils import (
        get_enhanced_roadmap_cached,
        cached_query_perplexity_sonar
    )
    CACHING_AVAILABLE = True
    print("✅ Redis caching enabled for LLM operations")
except ImportError:
    from app.utils.llm_utils import (
        get_enhanced_roadmap_with_multi_level_perplexity as get_enhanced_roadmap_cached,
        query_perplexity_sonar as cached_query_perplexity_sonar
    )
    CACHING_AVAILABLE = False
    print("⚠️ Redis caching not available - using direct API calls")

# Main blueprint
main_bp = Blueprint('main_bp', __name__)

@main_bp.route("/")
@main_bp.route("/home")
def home():
    if "user_id" in session:
        # Categories for the top section
        categories = [
            "Blockchain", "JavaScript", "Education", "Coding", "Books", "Web Development",
            "Marketing", "Deep Learning", "Social Media", "Software Development",
            "Artificial Intelligence", "Culture", "React", "UX", "Software Engineering",
            "Design", "Science", "Health", "Python", "Productivity", "Machine Learning",
            "Writing", "Self Improvement", "Technology", "Data Science", "Programming"
        ]

        # Fetch companies from database
        from app.utils.db_utils import get_db
        db = get_db()
        companies_collection = db.companies
        companies = companies_collection.find().sort("visit_date", 1).limit(5)
        selected_companies = list(companies)

        # Fetch articles from Medium API
        query = "technology"
        page = 0
        url = "https://medium16.p.rapidapi.com/search/stories"
        headers = {
            "x-rapidapi-key": os.getenv('MEDIUM_API_KEY'),
            "x-rapidapi-host": "medium16.p.rapidapi.com",
        }
        querystring = {"q": query, "limit": "5", "page": str(page)}
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            articles = response.json().get("data", []) if response.status_code == 200 else []
        except Exception as e:
            print(f"Error fetching articles: {e}")
            articles = []

        return render_template("home.html", 
                             categories=categories, 
                             selected_companies=selected_companies, 
                             stories=articles)  # Changed from articles to stories
    else:
        # FIX: Always pass stories variable, even when user is not authenticated
        # Option 1: Pass empty list (simplest fix)
        return render_template("home.html", stories=[])
        
        # Option 2: Fetch some default stories for non-authenticated users (better UX)
        # Uncomment the code below if you want to show articles to non-authenticated users
        """
        try:
            url = "https://medium16.p.rapidapi.com/search/stories"
            headers = {
                "x-rapidapi-key": os.getenv('MEDIUM_API_KEY'),
                "x-rapidapi-host": "medium16.p.rapidapi.com",
            }
            querystring = {"q": "technology", "limit": "6", "page": "0"}
            response = requests.get(url, headers=headers, params=querystring)
            stories = response.json().get("data", []) if response.status_code == 200 else []
        except Exception as e:
            print(f"Error fetching default stories: {e}")
            stories = []
        
        return render_template("home.html", stories=stories)
        """

@main_bp.route("/news-articles")
def news_article():
    if "user_id" in session:
        # Categories for the top section
        categories = [
            "Blockchain", "JavaScript", "Education", "Coding", "Books", "Web Development",
            "Marketing", "Deep Learning", "Social Media", "Software Development",
            "Artificial Intelligence", "Culture", "React", "UX", "Software Engineering",
            "Design", "Science", "Health", "Python", "Productivity", "Machine Learning",
            "Writing", "Self Improvement", "Technology", "Data Science", "Programming"
        ]

        # Get query parameters for topic and pagination
        query = request.args.get("q", "technology")
        page = int(request.args.get("page", 0))

        # API Request
        url = "https://medium16.p.rapidapi.com/search/stories"
        headers = {
            "x-rapidapi-key": os.getenv('MEDIUM_API_KEY'),
            "x-rapidapi-host": "medium16.p.rapidapi.com",
        }
        querystring = {"q": query, "limit": "10", "page": str(page)}
        
        try:
            response = requests.get(url, headers=headers, params=querystring)
            stories = response.json().get("data", []) if response.status_code == 200 else []
        except Exception as e:
            print(f"Error fetching stories: {e}")
            stories = []

        return render_template(
            "news_articles.html", stories=stories, query=query, page=page, categories=categories
        )
    else:
        return redirect(url_for("auth_bp.sign_in"))

@main_bp.route('/mentorship')
def mentorship():
    if "user_id" in session:
        return render_template('mentorship.html')
    else:
        return redirect(url_for("auth_bp.sign_in"))

@main_bp.route('/get_notifications')
def get_notifications():
    if "user_id" not in session:
        return jsonify([])
    
    from app.utils.db_utils import get_db
    db = get_db()
    notifications = list(db.notifications.find(
        {"user_id": session["user_id"]},
        {"_id": 0}
    ).sort("timestamp", -1).limit(10))
    
    return jsonify(notifications)

@main_bp.route("/student_profile", methods=["GET", "POST"])
def student_profile():
    if "user_id" not in session:
        return redirect(url_for("auth_bp.sign_in"))
    
    if request.method == "POST":
        try:
            from app.utils.db_utils import get_db
            db = get_db()
            user_collection = db.users
            
            # Get existing profile
            user_id = session["user_id"]
            existing_profile = user_collection.find_one({"user_id": user_id}) or {}
            
            # Collect form data
            form_data = request.form.to_dict()
            
            # Get checkbox values (multi-select)
            selected_companies = request.form.getlist('interested_companies')
            selected_industries = request.form.getlist('interested_industries')
            
            # Basic profile data
            basic_profile = {
                "name": form_data.get("name", "").strip(),
                "email": form_data.get("email", "").strip(),
                "phone": form_data.get("phone", "").strip(),
                "linkedin_url": form_data.get("linkedin_url", "").strip(),
                "github_url": form_data.get("github_url", "").strip(),
                "personal_statement": form_data.get("personal_statement", "").strip(),
                "career_goal": form_data.get("career_goal", "").strip(),
                "dream_company": form_data.get("dream_company", "").strip(),
                "experience_level": form_data.get("experience_level", "").strip(),
                "interested_companies": selected_companies,
                "interested_industries": selected_industries,
                "updated_at": datetime.now().isoformat()
            }
            
            # Check if key fields changed (trigger roadmap regeneration)
            key_fields = ["career_goal", "dream_company", "experience_level"]
            key_fields_updated = any(
                basic_profile.get(field) != existing_profile.get(field)
                for field in key_fields
            )
            
            # LinkedIn data fetching with caching
            linkedin_data = {}
            if basic_profile.get("linkedin_url"):
                try:
                    print("🔍 Fetching LinkedIn data...")
                    linkedin_response = fetch_linkedin_profile(basic_profile["linkedin_url"], user_id)
                    if linkedin_response.get("status") == "success":
                        linkedin_data = linkedin_response.get("data", {})
                        print(f"✅ LinkedIn data fetched: {len(linkedin_data)} fields")
                    else:
                        print(f"⚠️ LinkedIn fetch issue: {linkedin_response.get('message', 'Unknown error')}")
                except Exception as linkedin_error:
                    print(f"⚠️ LinkedIn error (non-critical): {linkedin_error}")
            
            # Combine all profile data
            updated_profile = {**basic_profile}
            
            # Generate roadmap if key fields updated or no roadmap exists
            desired_role = updated_profile.get("career_goal", "")
            
            if (key_fields_updated or not existing_profile.get("road_map")) and desired_role:
                print(f"🚀 Generating roadmap for: {desired_role}")
                
                # UPDATED: Get profile summary using simple manager (no vector DB)
                try:
                    profile_summary = get_profile_summary_for_llm(user_id, max_tokens=800)
                    if profile_summary:
                        print(f"✅ Got profile context: {len(profile_summary)} chars")
                    else:
                        print("⚠️ No profile context available, using basic info")
                except Exception as context_error:
                    print(f"⚠️ Profile context error: {context_error}")
                    profile_summary = f"Career Goal: {desired_role}"
                
                # Step 2: Generate Enhanced Roadmap (Level 1: Perplexity + Llama) with caching
                try:
                    print("🔍 Attempting Level 1 enhancement with Redis caching...")
                    roadmap_data = get_enhanced_roadmap_cached(
                        user_id=user_id,
                        topic=desired_role,
                        profile_summary=profile_summary
                    )
                    if CACHING_AVAILABLE:
                        print("✅ Multi-level enhanced roadmap generated with caching")
                    else:
                        print("✅ Multi-level enhanced roadmap generated (no cache)")
                    
                except Exception as enhancement_error:
                    print(f"⚠️ Level 1 enhancement failed: {enhancement_error}")
                    print("🔄 Falling back to basic roadmap generation...")
                    roadmap_data = get_roadmap_from_groq(desired_role)
                    print("✅ Basic roadmap generated as fallback")
                
                # Store roadmap in profile
                updated_profile['road_map'] = json.dumps(roadmap_data)

            # Database update operations
            update_operation = {"$set": updated_profile}
            if key_fields_updated:
                update_operation["$unset"] = {"active_modules": ""}

            # Update MongoDB
            result = user_collection.update_one(
                {"user_id": user_id}, 
                update_operation
            )
            
            print(f"✅ Profile updated in MongoDB: {result.modified_count} documents modified")
            
            # UPDATED: Simple profile storage (replaces vector database)
            try:
                complete_profile = {**existing_profile, **updated_profile}
                simple_storage_success = store_profile_simple(complete_profile)
                if simple_storage_success:
                    print(f"✅ Profile storage confirmed: {user_id}")
                else:
                    print(f"⚠️ Profile storage confirmation failed: {user_id}")
            except Exception as storage_error:
                print(f"⚠️ Profile storage error (non-critical): {storage_error}")
                # Don't break the main flow if storage confirmation fails
            
            flash("Profile updated successfully!", "success")
            return redirect(url_for('main_bp.student_profile'))

        except Exception as profile_error:
            print(f"❌ Profile update error: {str(profile_error)}")
            flash("Error updating profile. Please try again.", "error")
            return redirect(url_for('main_bp.student_profile'))

    # GET request - display profile
    from app.utils.db_utils import get_db
    db = get_db()
    user_collection = db.users
    profile = user_collection.find_one({"user_id": session['user_id']}) or {}
    return render_template('student_profile.html', profile=profile, user=profile)

@main_bp.route('/api/profile/insights/<user_id>')
def get_profile_insights(user_id):
    """Get AI-generated profile insights"""
    if "user_id" not in session or session["user_id"] != user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # UPDATED: Get profile context using simple manager
        profile_context = get_profile_summary_for_llm(user_id, max_tokens=1500)
        
        if not profile_context:
            return jsonify({"error": "No profile data available"}), 404
        
        return jsonify({
            "status": "success",
            "profile_context": profile_context,
            "insights": "Profile insights generated using simple context manager"
        })
        
    except Exception as e:
        print(f"❌ Profile insights error: {e}")
        return jsonify({"error": "Failed to generate insights"}), 500

@main_bp.route('/debug/test-enhancement')
def debug_test_enhancement():
    """Debug endpoint to test the enhancement system"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    if not os.getenv('DEBUG', '').lower() == 'true':
        return jsonify({"error": "Debug mode not enabled"}), 403
    
    try:
        user_id = session["user_id"]
        
        # UPDATED: Test profile summary using simple manager
        profile_summary = get_profile_summary_for_llm(user_id, max_tokens=500)
        
        # Test enhanced roadmap generation
        test_role = "Data Scientist"
        roadmap_data = get_enhanced_roadmap_cached(
            user_id=user_id,
            topic=test_role,
            profile_summary=profile_summary[:300]  # Limit for testing
        )
        
        return jsonify({
            "status": "success",
            "profile_summary_length": len(profile_summary),
            "profile_summary_preview": profile_summary[:200] + "..." if len(profile_summary) > 200 else profile_summary,
            "roadmap_phases": len(roadmap_data.get('phases', [])),
            "enhancement_metadata": roadmap_data.get('metadata', {}),
            "test_role": test_role,
            "system": "Simple Profile Manager with Redis Caching",
            "caching_enabled": CACHING_AVAILABLE
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "message": "Enhancement test failed"
        }), 500

@main_bp.route('/api/cache/stats')
def get_cache_stats():
    """Get cache statistics for monitoring"""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        from app.utils.redis_cache_manager import get_cache_health
        from app.utils.cached_llm_utils import get_api_cache_stats
        
        cache_health = get_cache_health()
        api_stats = get_api_cache_stats()
        
        return jsonify({
            "status": "success",
            "cache_health": cache_health,
            "api_cache": api_stats,
            "caching_enabled": CACHING_AVAILABLE
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "caching_enabled": False
        }), 500

@main_bp.route('/api/cache/clear/<cache_type>', methods=['POST'])
def clear_cache(cache_type):
    """Clear specific cache types"""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    
    if not os.getenv('DEBUG', '').lower() == 'true':
        return jsonify({"error": "Debug mode required"}), 403
    
    try:
        from app.utils.redis_cache_manager import clear_user_cache
        from app.utils.cached_llm_utils import clear_api_cache
        
        if cache_type == "user":
            user_id = session["user_id"]
            cleared = clear_user_cache(user_id)
            return jsonify({"status": "success", "cleared": cleared, "type": "user_cache"})
        
        elif cache_type == "api":
            cleared = clear_api_cache()
            return jsonify({"status": "success", "cleared": cleared, "type": "api_cache"})
        
        else:
            return jsonify({"error": "Invalid cache type"}), 400
            
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500