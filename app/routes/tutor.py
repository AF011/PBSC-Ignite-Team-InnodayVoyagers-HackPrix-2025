# app/routes/tutor.py - FIXED: Handle resources parameter properly
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
import json
import os
from datetime import datetime
from app.utils.db_utils import get_db, get_user_by_id
from app.utils.resource_utils import (
    fetch_youtube_videos,
    fetch_google_scholar_papers,
    fetch_google_search_results
)
from app.utils.llm_utils import ai_mentor_response
import time

# UPDATED: Import simple profile manager instead of vector database
from app.utils.simple_profile_manager import get_profile_summary_for_llm

# Create a Blueprint for the tutor routes
tutor_bp = Blueprint('tutor_bp', __name__)

# 🚀 SIMPLE: Cache only user data for tutor (not roadmap generation)
tutor_user_cache = {}
tutor_cache_timestamps = {}
TUTOR_CACHE_DURATION = 300  # 5 minutes

def get_cached_tutor_data(user_id):
    """Cache only the user data needed for tutor"""
    current_time = time.time()
    
    # Check cache
    if (user_id in tutor_user_cache and 
        user_id in tutor_cache_timestamps and 
        current_time - tutor_cache_timestamps[user_id] < TUTOR_CACHE_DURATION):
        
        print(f"🚀 Tutor cache HIT for: {user_id}")
        return tutor_user_cache[user_id]
    
    print(f"🔄 Tutor cache MISS for: {user_id}")
    
    try:
        # Get user and roadmap data (this is what you already do)
        user = get_user_by_id(user_id)
        if not user:
            return None
        
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Get profile summary (this is what takes time)
        try:
            profile_summary = get_profile_summary_for_llm(user_id, max_tokens=300)
        except Exception as e:
            print(f"⚠️ Profile error: {e}")
            profile_summary = f"Student: {user.get('name', 'Unknown')}"
        
        # Cache the data
        cached_data = {
            'user': user,
            'roadmap_data': roadmap_data,
            'profile_summary': profile_summary
        }
        
        tutor_user_cache[user_id] = cached_data
        tutor_cache_timestamps[user_id] = current_time
        
        print(f"✅ Tutor data cached for: {user_id}")
        return cached_data
        
    except Exception as e:
        print(f"❌ Tutor cache error: {e}")
        return None

@tutor_bp.route('/tutor/<string:phase_id>/<string:module_id>', methods=['GET'])
def tutor_page(phase_id, module_id):
    """
    Render the AI Tutor page for a specific phase and module
    
    Args:
        phase_id (str): The ID of the phase
        module_id (str): The ID of the module
    """
    if "user_id" not in session:
        return redirect(url_for("auth_bp.sign_in"))
    
    # Get user data
    user = get_user_by_id(session["user_id"])
    if not user:
        return redirect(url_for("auth_bp.sign_in"))
    
    # Get roadmap data
    roadmap_data = json.loads(user.get('road_map', '{}'))
    
    # Get specific phase data
    phase = None
    try:
        phase = roadmap_data['phases'][int(phase_id)]
    except (IndexError, KeyError, ValueError):
        return redirect(url_for("roadmap_bp.roadmap"))
    
    # Get learning plan data if available
    learning_plan = phase.get('learning_plan', {})
    
    # Get the specific module (weekly schedule)
    module = None
    try:
        module = learning_plan['weekly_schedule'][int(module_id) - 1]
    except (IndexError, KeyError, ValueError):
        # If module doesn't exist, redirect to roadmap
        return redirect(url_for("roadmap_bp.roadmap"))
    
    # Prepare initial resources for tutor page
    initial_resources = {
        "videos": [],
        "papers": [],
        "web_results": []
    }
    
    return render_template('tutor.html', 
                         phase=phase, 
                         module=module, 
                         user=user, 
                         phase_id=phase_id,
                         module_id=module_id,
                         resources=initial_resources)

@tutor_bp.route('/api/tutor/chat', methods=['POST'])
def tutor_chat():
    """🚀 CACHED: Only cache the user data retrieval part"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        message = data.get('message', '')
        phase_id = data.get('phase_id')
        module_id = data.get('module_id')
        
        if not all([message, phase_id is not None, module_id is not None]):
            return jsonify({"status": "error", "message": "Missing required parameters"}), 400
        
        start_time = time.time()
        
        # 🚀 CACHED: Get user data from cache instead of multiple DB calls
        cached_data = get_cached_tutor_data(session["user_id"])
        if not cached_data:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        user = cached_data['user']
        roadmap_data = cached_data['roadmap_data']
        profile_summary = cached_data['profile_summary']  # Already generated!
        
        print(f"⏱️ User data retrieved: {time.time() - start_time:.2f}s")
        
        # Get phase and module data (from cached roadmap)
        phase = roadmap_data['phases'][int(phase_id)]
        learning_plan = phase.get('learning_plan', {})
        module = learning_plan['weekly_schedule'][int(module_id) - 1]
        
        # Get chat history (still need this from DB)
        db = get_db()
        chat_history_doc = db.user_chat_histories.find_one({"user_id": session["user_id"]})
        
        if not chat_history_doc:
            chat_history_doc = {
                "user_id": session["user_id"],
                "modules": {}
            }
        
        module_key = f"phase_{phase_id}_module_{module_id}"
        if module_key not in chat_history_doc.get('modules', {}):
            chat_history_doc['modules'][module_key] = []
        
        # Add user message to history
        user_message = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now()
        }
        chat_history_doc['modules'][module_key].append(user_message)
        
        # Get conversation context (last 10 messages)
        conversation_context = chat_history_doc['modules'][module_key][-10:]
        
        # 🔧 FIXED: Prepare parameters for AI mentor with proper resource handling
        topic = f"{phase.get('name', phase.get('title', 'Learning Topic'))} - Week {module.get('week', 1)}"
        
        # Handle objectives properly
        objectives = module.get('learning_objectives', [])
        if not isinstance(objectives, list):
            objectives = [str(objectives)] if objectives else ["General learning"]
        
        # Handle skills properly
        skills = phase.get('skills', [])
        if not isinstance(skills, list):
            skills = [str(skills)] if skills else ["Fundamental skills"]
        
        # 🔧 FIXED: Handle resources properly - convert to dict format expected by ai_mentor_response
        phase_resources = phase.get('resources', {})
        if isinstance(phase_resources, dict):
            resources = phase_resources
        elif isinstance(phase_resources, list):
            resources = {"Learning Resources": phase_resources}
        else:
            resources = {"Learning Resources": [str(phase_resources)] if phase_resources else []}
        
        # Add module-specific resources if available
        module_resources = module.get('resources', [])
        if module_resources:
            if isinstance(module_resources, list):
                resources["Module Resources"] = module_resources
            else:
                resources["Module Resources"] = [str(module_resources)]
        
        print(f"🎓 AI Mentor processing: {message[:50]}...")
        print(f"📚 Topic: {topic}")
        print(f"🎯 Objectives: {objectives}")
        print(f"🔧 Skills: {skills}")
        
        ai_start_time = time.time()
        
        # Get response from AI Mentor (using cached profile!)
        ai_response = ai_mentor_response(
            message=message,
            topic=topic,
            objectives=objectives,
            skills=skills,
            resources=resources,
            conversation_context=conversation_context,
            user_profile=profile_summary  # 🚀 This is now cached!
        )
        
        print(f"⏱️ AI processing: {time.time() - ai_start_time:.2f}s")
        
        # Handle different response formats
        if isinstance(ai_response, dict):
            response_content = ai_response.get('response', ai_response.get('content', 'No response available'))
            citations = ai_response.get('citations', [])
        else:
            response_content = str(ai_response)
            citations = []
        
        # Create AI response object
        assistant_message = {
            "role": "assistant",
            "content": response_content,
            "citations": citations,
            "timestamp": datetime.now()
        }
        
        # Add assistant message to history
        chat_history_doc['modules'][module_key].append(assistant_message)
        
        # Update the database
        db.user_chat_histories.update_one(
            {"user_id": session["user_id"]},
            {"$set": chat_history_doc},
            upsert=True
        )
        
        total_time = time.time() - start_time
        print(f"✅ Total response time: {total_time:.2f}s")
        print(f"✅ Conversation message stored: {len(chat_history_doc['modules'][module_key])}")
        
        return jsonify({
            "status": "success",
            "response": response_content,
            "citations": citations,
            "processing_time": f"{total_time:.2f}s"
        })
        
    except Exception as e:
        print(f"❌ Tutor chat error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@tutor_bp.route('/api/tutor/resources', methods=['GET'])
def get_resources():
    """API endpoint to get resources for a specific topic"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    topic = request.args.get('topic')
    resource_type = request.args.get('type', 'all')
    
    if not topic:
        return jsonify({"status": "error", "message": "Topic is required"}), 400
    
    try:
        resources = {}
        
        if resource_type in ['all', 'videos']:
            videos = fetch_youtube_videos(topic)
            resources['videos'] = videos
        
        if resource_type in ['all', 'papers']:
            papers = fetch_google_scholar_papers(topic)
            resources['papers'] = papers
        
        if resource_type in ['all', 'web']:
            web_results = fetch_google_search_results(topic)
            resources['web_results'] = web_results
        
        return jsonify({
            "status": "success",
            "resources": resources
        })
        
    except Exception as e:
        print(f"❌ Resource fetch error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@tutor_bp.route('/api/tutor/history/<string:phase_id>/<string:module_id>')
def get_chat_history(phase_id, module_id):
    """Get chat history for a specific phase and module"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        db = get_db()
        chat_history_doc = db.user_chat_histories.find_one({"user_id": session["user_id"]})
        
        if not chat_history_doc:
            return jsonify({"status": "success", "history": []})
        
        module_key = f"phase_{phase_id}_module_{module_id}"
        history = chat_history_doc.get('modules', {}).get(module_key, [])
        
        # Convert datetime objects to strings for JSON serialization
        for message in history:
            if 'timestamp' in message and hasattr(message['timestamp'], 'isoformat'):
                message['timestamp'] = message['timestamp'].isoformat()
        
        return jsonify({
            "status": "success",
            "history": history
        })
        
    except Exception as e:
        print(f"❌ Chat history error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@tutor_bp.route('/api/tutor/clear-history/<string:phase_id>/<string:module_id>', methods=['POST'])
def clear_chat_history(phase_id, module_id):
    """Clear chat history for a specific phase and module"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        db = get_db()
        module_key = f"phase_{phase_id}_module_{module_id}"
        
        result = db.user_chat_histories.update_one(
            {"user_id": session["user_id"]},
            {"$unset": {f"modules.{module_key}": ""}}
        )
        
        return jsonify({
            "status": "success",
            "message": "Chat history cleared successfully"
        })
        
    except Exception as e:
        print(f"❌ Clear history error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500