# Add these routes to your Flask application
# Create a new file: app/routes/linkedin_routes.py

from flask import Blueprint, request, jsonify, session
from app.utils.db_utils import get_db, get_user_by_id
from app.utils.linkedin_integration import (
    LinkedInAchievementPublisher,
    publish_task_completion_achievement,
    publish_assessment_achievement,
    publish_phase_completion_achievement
)
import json
from datetime import datetime

# Create blueprint for LinkedIn routes
linkedin_bp = Blueprint('linkedin_bp', __name__)

@linkedin_bp.route('/api/user/linkedin-status', methods=['GET'])
def get_linkedin_status():
    """Check if user has LinkedIn connected"""
    if "user_id" not in session:
        return jsonify({"connected": False, "message": "Not authenticated"}), 401
    
    try:
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"connected": False, "message": "User not found"}), 404
        
        # Check if user has LinkedIn account ID
        linkedin_account_id = user.get('linkedin_account_id')
        linkedin_profile_url = user.get('linkedin_profile_url')
        auto_sharing_enabled = user.get('auto_sharing_enabled', False)
        
        return jsonify({
            "connected": bool(linkedin_account_id),
            "profile_url": linkedin_profile_url,
            "auto_sharing_enabled": auto_sharing_enabled,
            "account_id_masked": f"***{linkedin_account_id[-4:]}" if linkedin_account_id else None
        })
        
    except Exception as e:
        print(f"❌ LinkedIn status check error: {e}")
        return jsonify({"connected": False, "error": str(e)}), 500

@linkedin_bp.route('/api/user/connect-linkedin', methods=['POST'])
def connect_linkedin():
    """Save user's LinkedIn connection details"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        linkedin_account_id = data.get('linkedin_account_id', '').strip()
        linkedin_profile_url = data.get('linkedin_profile_url', '').strip()
        auto_sharing_enabled = data.get('auto_sharing_enabled', False)
        
        if not linkedin_account_id or not linkedin_profile_url:
            return jsonify({"status": "error", "message": "Missing required fields"}), 400
        
        # Basic validation
        if not linkedin_profile_url.startswith('https://www.linkedin.com/in/'):
            return jsonify({"status": "error", "message": "Invalid LinkedIn profile URL"}), 400
        
        # Update user record
        db = get_db()
        result = db.users.update_one(
            {"user_id": session["user_id"]},
            {
                "$set": {
                    "linkedin_account_id": linkedin_account_id,
                    "linkedin_profile_url": linkedin_profile_url,
                    "auto_sharing_enabled": auto_sharing_enabled,
                    "linkedin_connected_at": datetime.now().isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ LinkedIn connected for user {session['user_id']}")
            return jsonify({
                "status": "success",
                "message": "LinkedIn connected successfully!"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to save LinkedIn connection"}), 500
            
    except Exception as e:
        print(f"❌ LinkedIn connection error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@linkedin_bp.route('/api/user/linkedin-preferences', methods=['GET'])
def get_linkedin_preferences():
    """Get user's LinkedIn sharing preferences"""
    if "user_id" not in session:
        return jsonify({"auto_sharing_enabled": False}), 401
    
    try:
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"auto_sharing_enabled": False}), 404
        
        return jsonify({
            "auto_sharing_enabled": user.get('auto_sharing_enabled', False),
            "linkedin_connected": bool(user.get('linkedin_account_id'))
        })
        
    except Exception as e:
        print(f"❌ LinkedIn preferences error: {e}")
        return jsonify({"auto_sharing_enabled": False}), 500

# REPLACE your publish_achievement route with this Llama-powered version:

@linkedin_bp.route('/api/linkedin/publish-achievement', methods=['POST'])
def publish_achievement():
    """Publish achievement to LinkedIn with Llama-generated content"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        achievement_type = data.get('type', 'task_completion')
        
        # Extract achievement details
        phase_name = data.get('phase_name', 'Learning Phase')
        day = data.get('day', 1)
        score = data.get('score', 85)
        user_name = data.get('user_name', 'Demo User')
        
        print(f"🤖 Generating LinkedIn post with Llama for {achievement_type}...")
        
        # Generate LinkedIn post using Llama
        post_content = generate_linkedin_post_with_llama(
            achievement_type=achievement_type,
            phase_name=phase_name,
            day=day,
            score=score,
            user_name=user_name
        )
        
        if not post_content:
            print("❌ Failed to generate post content, using fallback")
            post_content = f"🎉 Just completed Day {day} assessment in {phase_name} with {score}%! #Learning #Achievement"
        
        print(f"✅ Llama-generated post ({len(post_content)} chars): {post_content[:100]}...")
        
        # Use hardcoded LinkedIn ID for demo
        linkedin_account_id = '9KDztbl5QFedLtfzuc4doQ'
        
        # Initialize publisher and create/publish achievement
        publisher = LinkedInAchievementPublisher()
        result = publisher.create_and_publish_achievement_with_content(
            post_content=post_content,
            user_linkedin_account_id=linkedin_account_id,
            include_image=False
        )
        
        print(f"📤 LinkedIn publish result: {result}")
        
        if result['success']:
            print(f"🎉 Achievement published to LinkedIn successfully")
            return jsonify({
                "status": "success",
                "message": result['message'],
                "post_content": post_content,
                "image_generated": False
            })
        else:
            print(f"❌ LinkedIn publishing failed: {result['message']}")
            return jsonify({
                "status": "error",
                "message": result['message']
            }), 400
            
    except Exception as e:
        print(f"❌ LinkedIn achievement publishing error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def generate_linkedin_post_with_llama(achievement_type, phase_name, day, score, user_name):
    """Generate LinkedIn post using Llama"""
    try:
        from groq import Groq
        import os
        
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        if achievement_type == 'assessment_passed':
            prompt = f"""Create a professional LinkedIn post for someone who just passed an assessment.

Details:
- User: {user_name}
- Course: {phase_name}
- Day: {day}
- Score: {score}%

Requirements:
- Professional but enthusiastic tone
- Include relevant emojis
- Add 3-5 relevant hashtags
- Keep it under 300 characters
- Sound authentic and personal
- Include learning insights

Write the complete LinkedIn post:"""

        else:
            prompt = f"""Create a professional LinkedIn post for someone who completed a learning task.

Details:
- User: {user_name}
- Course: {phase_name}
- Day: {day}

Requirements:
- Professional but enthusiastic tone
- Include relevant emojis
- Add 3-5 relevant hashtags
- Keep it under 300 characters
- Sound authentic and personal

Write the complete LinkedIn post:"""
        
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a professional LinkedIn content creator. Write engaging, authentic posts that celebrate learning achievements."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            max_tokens=200
        )
        
        post_content = response.choices[0].message.content.strip()
        
        # Clean up any quotes or formatting
        post_content = post_content.replace('"', '').replace("Here's the LinkedIn post:", "").strip()
        
        return post_content
        
    except Exception as e:
        print(f"❌ Llama post generation error: {e}")
        return None

@linkedin_bp.route('/api/linkedin/test-connection', methods=['POST'])
def test_linkedin_connection():
    """Test LinkedIn connection by posting a test message"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        linkedin_account_id = user.get('linkedin_account_id')
        if not linkedin_account_id:
            return jsonify({"status": "error", "message": "LinkedIn not connected"}), 400
        
        # Create test achievement data
        test_data = {
            'type': 'test_connection',
            'user_name': user.get('name', 'Student'),
            'phase_name': 'LinkedIn Integration Test',
            'task_name': 'Connection Test',
            'day': 1,
            'skills': ['Social Media Integration', 'Professional Networking'],
            'total_progress': 100
        }
        
        publisher = LinkedInAchievementPublisher()
        result = publisher.create_and_publish_achievement(
            achievement_data=test_data,
            user_linkedin_account_id=linkedin_account_id,
            include_image=False  # No image for test
        )
        
        return jsonify({
            "status": "success" if result['success'] else "error",
            "message": result['message'],
            "test_content": result.get('post_content', '')
        })
        
    except Exception as e:
        print(f"❌ LinkedIn test connection error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@linkedin_bp.route('/api/user/update-linkedin-preferences', methods=['POST'])
def update_linkedin_preferences():
    """Update user's LinkedIn sharing preferences"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        auto_sharing_enabled = data.get('auto_sharing_enabled', False)
        
        # Update user record
        db = get_db()
        result = db.users.update_one(
            {"user_id": session["user_id"]},
            {
                "$set": {
                    "auto_sharing_enabled": auto_sharing_enabled,
                    "preferences_updated_at": datetime.now().isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ LinkedIn preferences updated for user {session['user_id']}: auto_sharing={auto_sharing_enabled}")
            return jsonify({
                "status": "success",
                "message": "Preferences updated successfully!",
                "auto_sharing_enabled": auto_sharing_enabled
            })
        else:
            return jsonify({"status": "error", "message": "Failed to update preferences"}), 500
            
    except Exception as e:
        print(f"❌ LinkedIn preferences update error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@linkedin_bp.route('/api/user/disconnect-linkedin', methods=['POST'])
def disconnect_linkedin():
    """Disconnect user's LinkedIn account"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        # Remove LinkedIn connection data from user record
        db = get_db()
        result = db.users.update_one(
            {"user_id": session["user_id"]},
            {
                "$unset": {
                    "linkedin_account_id": "",
                    "linkedin_profile_url": "",
                    "linkedin_connected_at": ""
                },
                "$set": {
                    "auto_sharing_enabled": False,
                    "linkedin_disconnected_at": datetime.now().isoformat()
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"✅ LinkedIn disconnected for user {session['user_id']}")
            return jsonify({
                "status": "success",
                "message": "LinkedIn account disconnected successfully!"
            })
        else:
            return jsonify({"status": "error", "message": "Failed to disconnect LinkedIn"}), 500
            
    except Exception as e:
        print(f"❌ LinkedIn disconnect error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@linkedin_bp.route('/api/linkedin/posts-history', methods=['GET'])
def get_linkedin_posts_history():
    """Get user's LinkedIn posts history"""
    if "user_id" not in session:
        return jsonify({"posts": [], "message": "Not authenticated"}), 401
    
    try:
        db = get_db()
        posts = list(db.linkedin_posts.find(
            {"user_id": session["user_id"]},
            {"_id": 0}  # Exclude MongoDB ID
        ).sort("published_at", -1).limit(50))  # Latest 50 posts
        
        return jsonify({
            "posts": posts,
            "total_count": len(posts)
        })
        
    except Exception as e:
        print(f"❌ LinkedIn posts history error: {e}")
        return jsonify({"posts": [], "error": str(e)}), 500

# Helper function to validate LinkedIn URL format
def is_valid_linkedin_url(url):
    """Validate LinkedIn profile URL format"""
    if not url:
        return False
    
    valid_patterns = [
        'https://www.linkedin.com/in/',
        'https://linkedin.com/in/',
        'http://www.linkedin.com/in/',
        'http://linkedin.com/in/'
    ]
    
    return any(url.startswith(pattern) for pattern in valid_patterns)

# Add this to your main app.py registration
"""
# In your main app.py file, add this import and registration:


"""