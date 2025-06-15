# app/routes/roadmap.py - Complete: Vector Database Removed & Missing Routes Added
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import json
from datetime import datetime
from app.utils.db_utils import get_db, get_user_by_id

# Enhanced: Import both original and enhanced functions
from app.utils.llm_utils import (
    generate_learning_plan,  # Original fallback
    generate_detailed_learning_plan_with_perplexity  # Level 2: Enhanced
)

# UPDATED: Import simple profile manager instead of vector database
from app.utils.simple_profile_manager import get_profile_summary_for_llm

# Create a blueprint for roadmap routes
roadmap_bp = Blueprint('roadmap_bp', __name__)


# ✅ ADAPTIVE ROADMAP SYSTEM
# Smart curriculum adjustment based on daily progress and delays

from datetime import datetime, timedelta
import json
from flask import Blueprint, jsonify, request, session
from app.utils.db_utils import get_db, get_user_by_id

class AdaptiveRoadmapManager:
    """
    🧠 Smart Roadmap Manager that adapts to student progress
    - Tracks daily completion vs expected schedule
    - Detects delays and missed days
    - Automatically adjusts curriculum difficulty and timeline
    - Provides personalized catch-up plans
    """
    
    def __init__(self):
        self.db = get_db()
        
    def analyze_progress_and_adapt(self, user_id, roadmap_data):
        """
        📊 Core function: Analyze progress and adapt roadmap
        """
        try:
            print(f"🔍 Analyzing progress for user {user_id}...")
            
            # 1. Calculate progress metrics
            progress_analysis = self._calculate_detailed_progress(roadmap_data)
            
            # 2. Detect delays and missed days
            delay_analysis = self._detect_delays(roadmap_data)
            
            # 3. Generate adaptation recommendations
            adaptations = self._generate_adaptations(progress_analysis, delay_analysis)
            
            # 4. Apply automatic adjustments
            adapted_roadmap = self._apply_adaptations(roadmap_data, adaptations)
            
            # 5. Update user roadmap in database
            self._save_adapted_roadmap(user_id, adapted_roadmap, adaptations)
            
            return {
                "status": "success",
                "progress_analysis": progress_analysis,
                "delay_analysis": delay_analysis,
                "adaptations_applied": adaptations,
                "updated_roadmap": adapted_roadmap
            }
            
        except Exception as e:
            print(f"❌ Adaptive analysis error: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "error": str(e)}
    
    def _calculate_detailed_progress(self, roadmap_data):
        """📈 Calculate comprehensive progress metrics"""
        
        current_date = datetime.now()
        total_phases = len(roadmap_data.get('phases', []))
        
        analysis = {
            "overall_stats": {
                "total_phases": total_phases,
                "completed_phases": 0,
                "in_progress_phases": 0,
                "pending_phases": 0
            },
            "phase_details": {},
            "daily_completion_rate": 0,
            "expected_vs_actual": {},
            "learning_velocity": "normal"  # slow, normal, fast
        }
        
        total_tasks_all = 0
        completed_tasks_all = 0
        total_days_expected = 0
        total_days_completed = 0
        
        for phase_idx, phase in enumerate(roadmap_data.get('phases', [])):
            if not phase.get('learning_plan', {}).get('weekly_schedule'):
                continue
                
            phase_analysis = self._analyze_phase_progress(phase, phase_idx, current_date)
            analysis["phase_details"][phase_idx] = phase_analysis
            
            # Aggregate statistics
            total_tasks_all += phase_analysis["total_tasks"]
            completed_tasks_all += phase_analysis["completed_tasks"]
            total_days_expected += phase_analysis["expected_days_by_now"]
            total_days_completed += phase_analysis["actual_completed_days"]
            
            # Count phase status
            if phase_analysis["completion_percentage"] == 100:
                analysis["overall_stats"]["completed_phases"] += 1
            elif phase_analysis["completion_percentage"] > 0:
                analysis["overall_stats"]["in_progress_phases"] += 1
            else:
                analysis["overall_stats"]["pending_phases"] += 1
        
        # Calculate learning velocity
        if total_days_expected > 0:
            completion_ratio = total_days_completed / total_days_expected
            if completion_ratio >= 1.2:
                analysis["learning_velocity"] = "fast"
            elif completion_ratio <= 0.7:
                analysis["learning_velocity"] = "slow"
            else:
                analysis["learning_velocity"] = "normal"
        
        analysis["daily_completion_rate"] = (completed_tasks_all / total_tasks_all * 100) if total_tasks_all > 0 else 0
        analysis["expected_vs_actual"] = {
            "expected_days": total_days_expected,
            "actual_days": total_days_completed,
            "ahead_behind": total_days_completed - total_days_expected
        }
        
        return analysis
    
    def _analyze_phase_progress(self, phase, phase_idx, current_date):
        """📊 Detailed analysis for a single phase"""
        
        # Get phase start date (when learning plan was generated)
        phase_start = phase.get('learning_plan', {}).get('metadata', {}).get('generated_at')
        if phase_start:
            try:
                # Handle different datetime formats
                if 'T' in phase_start:
                    phase_start_date = datetime.fromisoformat(phase_start.replace('Z', '+00:00'))
                else:
                    phase_start_date = datetime.fromisoformat(phase_start)
            except:
                phase_start_date = current_date
        else:
            phase_start_date = current_date  # Fallback to now
        
        weekly_schedule = phase['learning_plan']['weekly_schedule']
        
        phase_analysis = {
            "phase_id": phase_idx,
            "phase_name": phase.get('name', f'Phase {phase_idx + 1}'),
            "start_date": phase_start,
            "total_weeks": len(weekly_schedule),
            "total_tasks": 0,
            "completed_tasks": 0,
            "expected_days_by_now": 0,
            "actual_completed_days": 0,
            "completion_percentage": 0,
            "days_behind_schedule": 0,
            "missed_days": [],
            "status": "pending"  # pending, on_track, behind, ahead, completed
        }
        
        days_since_start = (current_date - phase_start_date).days
        
        all_tasks = []
        for week_idx, week in enumerate(weekly_schedule):
            for day_idx, task in enumerate(week.get('daily_tasks', [])):
                phase_analysis["total_tasks"] += 1
                
                task_info = {
                    "week": week_idx,
                    "day": day_idx,
                    "task_id": task.get('task_id', f'w{week_idx}_d{day_idx}'),
                    "completed": task.get('completed', False),
                    "completed_date": task.get('completed_date'),
                    "expected_date": phase_start_date + timedelta(days=len(all_tasks))
                }
                
                all_tasks.append(task_info)
                
                if task.get('completed', False):
                    phase_analysis["completed_tasks"] += 1
                    phase_analysis["actual_completed_days"] += 1
        
        # Calculate expected progress (max days since start, but not more than total tasks)
        expected_tasks_by_now = min(days_since_start, len(all_tasks))
        phase_analysis["expected_days_by_now"] = max(0, expected_tasks_by_now)
        
        # Determine if behind schedule
        phase_analysis["days_behind_schedule"] = max(0, expected_tasks_by_now - phase_analysis["actual_completed_days"])
        
        # Find missed days
        for i, task in enumerate(all_tasks[:expected_tasks_by_now]):
            if not task["completed"] and task["expected_date"] < current_date:
                phase_analysis["missed_days"].append({
                    "day": i + 1,
                    "expected_date": task["expected_date"].isoformat(),
                    "days_overdue": (current_date - task["expected_date"]).days
                })
        
        # Calculate completion percentage
        if phase_analysis["total_tasks"] > 0:
            phase_analysis["completion_percentage"] = round(
                (phase_analysis["completed_tasks"] / phase_analysis["total_tasks"]) * 100, 1
            )
        
        # Determine status
        if phase_analysis["completion_percentage"] == 100:
            phase_analysis["status"] = "completed"
        elif phase_analysis["days_behind_schedule"] > 3:
            phase_analysis["status"] = "behind"
        elif phase_analysis["actual_completed_days"] > expected_tasks_by_now:
            phase_analysis["status"] = "ahead"
        elif phase_analysis["actual_completed_days"] > 0:
            phase_analysis["status"] = "on_track"
        else:
            phase_analysis["status"] = "pending"
        
        return phase_analysis
    
    def _detect_delays(self, roadmap_data):
        """🚨 Detect learning delays and patterns"""
        
        current_date = datetime.now()
        delay_analysis = {
            "total_days_behind": 0,
            "phases_behind_schedule": [],
            "longest_streak_missed": 0,
            "delay_patterns": [],
            "risk_level": "low",  # low, medium, high, critical
            "recommendations": []
        }
        
        total_delays = 0
        
        for phase_idx, phase in enumerate(roadmap_data.get('phases', [])):
            if not phase.get('learning_plan', {}).get('weekly_schedule'):
                continue
            
            phase_delays = self._analyze_phase_delays(phase, phase_idx, current_date)
            
            if phase_delays["days_behind"] > 0:
                delay_analysis["phases_behind_schedule"].append(phase_delays)
                total_delays += phase_delays["days_behind"]
        
        delay_analysis["total_days_behind"] = total_delays
        
        # Determine risk level
        if total_delays == 0:
            delay_analysis["risk_level"] = "low"
        elif total_delays <= 3:
            delay_analysis["risk_level"] = "medium"
        elif total_delays <= 7:
            delay_analysis["risk_level"] = "high"
        else:
            delay_analysis["risk_level"] = "critical"
        
        # Generate recommendations based on delays
        delay_analysis["recommendations"] = self._generate_delay_recommendations(delay_analysis)
        
        return delay_analysis
    
    def _analyze_phase_delays(self, phase, phase_idx, current_date):
        """🔍 Analyze delays for a specific phase"""
        
        phase_start = phase.get('learning_plan', {}).get('metadata', {}).get('generated_at')
        if phase_start:
            try:
                if 'T' in phase_start:
                    phase_start_date = datetime.fromisoformat(phase_start.replace('Z', '+00:00'))
                else:
                    phase_start_date = datetime.fromisoformat(phase_start)
            except:
                phase_start_date = current_date
        else:
            phase_start_date = current_date
        
        days_since_start = (current_date - phase_start_date).days
        weekly_schedule = phase['learning_plan']['weekly_schedule']
        
        total_expected_by_now = 0
        total_completed = 0
        missed_days_streak = 0
        current_streak = 0
        
        day_count = 0
        for week in weekly_schedule:
            for task in week.get('daily_tasks', []):
                day_count += 1
                
                if day_count <= days_since_start:
                    total_expected_by_now += 1
                    
                    if task.get('completed', False):
                        total_completed += 1
                        current_streak = 0
                    else:
                        current_streak += 1
                        missed_days_streak = max(missed_days_streak, current_streak)
        
        return {
            "phase_id": phase_idx,
            "phase_name": phase.get('name', f'Phase {phase_idx + 1}'),
            "days_behind": max(0, total_expected_by_now - total_completed),
            "expected_by_now": total_expected_by_now,
            "actually_completed": total_completed,
            "longest_missed_streak": missed_days_streak,
            "start_date": phase_start_date.isoformat()
        }
    
    def _generate_delay_recommendations(self, delay_analysis):
        """💡 Generate personalized recommendations for catching up"""
        
        recommendations = []
        risk_level = delay_analysis["risk_level"]
        total_behind = delay_analysis["total_days_behind"]
        
        if risk_level == "low":
            recommendations.append({
                "type": "motivation",
                "title": "Keep Up the Great Work! 🎉",
                "description": "You're on track with your learning goals. Maintain this momentum!",
                "action": "Continue daily practice"
            })
        
        elif risk_level == "medium":
            recommendations.append({
                "type": "gentle_reminder",
                "title": "Small Catch-Up Needed 📚",
                "description": f"You're {total_behind} days behind schedule. A focused weekend can get you back on track!",
                "action": "Dedicate 2-3 hours this weekend to catch up"
            })
        
        elif risk_level == "high":
            recommendations.append({
                "type": "intensive_catchup",
                "title": "Time for Intensive Catch-Up 🚀",
                "description": f"You're {total_behind} days behind. Let's create a focused catch-up plan.",
                "action": "Switch to accelerated learning mode for 1 week"
            })
            
        elif risk_level == "critical":
            recommendations.append({
                "type": "curriculum_adjustment",
                "title": "Curriculum Adjustment Needed 🔄",
                "description": f"You're {total_behind} days behind. Let's modify your learning path to focus on core concepts.",
                "action": "Activate emergency catch-up mode with simplified curriculum"
            })
        
        return recommendations
    
    def _generate_adaptations(self, progress_analysis, delay_analysis):
        """🔧 Generate specific curriculum adaptations"""
        
        adaptations = {
            "schedule_adjustments": [],
            "content_modifications": [],
            "difficulty_changes": [],
            "timeline_extensions": [],
            "catch_up_plans": []
        }
        
        risk_level = delay_analysis["risk_level"]
        learning_velocity = progress_analysis["learning_velocity"]
        
        # Schedule adjustments based on learning velocity
        if learning_velocity == "slow" or risk_level in ["high", "critical"]:
            adaptations["schedule_adjustments"].append({
                "type": "extend_timeline",
                "description": "Extend daily learning time by 30 minutes",
                "adjustment": "timeline_extension"
            })
            
            adaptations["content_modifications"].append({
                "type": "simplify_content",
                "description": "Focus on core concepts, reduce advanced topics",
                "adjustment": "content_simplification"
            })
        
        elif learning_velocity == "fast":
            adaptations["difficulty_changes"].append({
                "type": "increase_challenge",
                "description": "Add bonus challenges and advanced projects",
                "adjustment": "difficulty_increase"
            })
        
        # Specific catch-up plans
        if delay_analysis["total_days_behind"] > 0:
            adaptations["catch_up_plans"].append({
                "type": "weekend_intensive",
                "days_to_recover": delay_analysis["total_days_behind"],
                "estimated_hours": delay_analysis["total_days_behind"] * 2,
                "description": f"Intensive {delay_analysis['total_days_behind']}-day catch-up program"
            })
        
        return adaptations
    
    def _apply_adaptations(self, roadmap_data, adaptations):
        """🔄 Apply adaptations to the roadmap"""
        
        adapted_roadmap = json.loads(json.dumps(roadmap_data))  # Deep copy
        
        # Add adaptation metadata
        if 'adaptive_settings' not in adapted_roadmap:
            adapted_roadmap['adaptive_settings'] = {}
        
        adapted_roadmap['adaptive_settings'].update({
            'last_adaptation': datetime.now().isoformat(),
            'applied_adaptations': adaptations,
            'adaptation_count': adapted_roadmap.get('adaptive_settings', {}).get('adaptation_count', 0) + 1
        })
        
        # Apply specific adaptations to phases
        for phase in adapted_roadmap.get('phases', []):
            if phase.get('learning_plan'):
                # Add adaptation flags to learning plan
                if 'adaptation_flags' not in phase['learning_plan']:
                    phase['learning_plan']['adaptation_flags'] = {}
                
                # Apply content modifications
                for modification in adaptations.get('content_modifications', []):
                    if modification['type'] == 'simplify_content':
                        phase['learning_plan']['adaptation_flags']['content_simplified'] = True
                        phase['learning_plan']['adaptation_flags']['focus_mode'] = 'core_concepts'
                
                # Apply difficulty changes
                for change in adaptations.get('difficulty_changes', []):
                    if change['type'] == 'increase_challenge':
                        phase['learning_plan']['adaptation_flags']['difficulty_increased'] = True
                        phase['learning_plan']['adaptation_flags']['bonus_content'] = True
        
        return adapted_roadmap
    
    def _save_adapted_roadmap(self, user_id, adapted_roadmap, adaptations):
        """💾 Save the adapted roadmap to database"""
        
        try:
            result = self.db.users.update_one(
                {"user_id": user_id},
                {"$set": {"road_map": json.dumps(adapted_roadmap)}}
            )
            
            # Also save adaptation history (optional - create collection if needed)
            try:
                adaptation_record = {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "adaptations": adaptations,
                    "adaptation_type": "automatic"
                }
                
                self.db.adaptation_history.insert_one(adaptation_record)
            except Exception as history_error:
                print(f"⚠️ Could not save adaptation history (non-critical): {history_error}")
            
            print(f"✅ Adapted roadmap saved for user {user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error saving adapted roadmap: {e}")
            return False
        

@roadmap_bp.route('/road-map')
def roadmap():
    """Render the roadmap page for the user"""
    if "user_id" not in session:
        return redirect(url_for("auth_bp.sign_in"))
    
    # Get user data
    user = get_user_by_id(session["user_id"])
    if not user:
        return redirect(url_for("auth_bp.sign_in"))
    
    # Get roadmap data
    roadmap_data = json.loads(user.get('road_map', '{}'))
    
    # Check if roadmap exists
    if not roadmap_data or 'phases' not in roadmap_data:
        return redirect(url_for("main_bp.student_profile"))
    
    # Add the user object to the template context
    return render_template('road_map.html', roadmap_data=roadmap_data, user=user)

@roadmap_bp.route('/generate-plan/<string:phase_id>', methods=['POST'])
def generate_plan(phase_id):
    """🚀 UPDATED: Generate learning plan with simple profile manager (Vector DB removed)"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    # Get user data
    user = get_user_by_id(session["user_id"])
    if not user:
        return jsonify({"status": "error", "message": "User not found"}), 404
    
    # Get roadmap data
    roadmap_data = json.loads(user.get('road_map', '{}'))
    
    # Check if phase exists
    try:
        phase_id_int = int(phase_id)
        if phase_id_int < 0 or phase_id_int >= len(roadmap_data.get('phases', [])):
            return jsonify({"status": "error", "message": "Invalid phase ID"}), 400
        
        phase = roadmap_data['phases'][phase_id_int]
    except (ValueError, IndexError, KeyError):
        return jsonify({"status": "error", "message": "Invalid phase ID"}), 400
    
    # Check if the learning plan already exists
    if phase.get('learning_plan'):
        return jsonify({"status": "exists", "message": "Learning plan already exists"})
    
    # Get phase name and skills - Handle both 'name' and 'title' fields
    phase_name = phase.get('name', phase.get('title', ''))
    phase_description = phase.get('description', '')
    skills = phase.get('skills', [])
    duration_weeks = phase.get('duration_weeks', 4)
    
    if not phase_name:
        return jsonify({"status": "error", "message": "Missing phase name"}), 400
    
    try:
        print(f"🚀 Level 2: Generating enhanced learning plan for {phase_name}")
        
        # UPDATED: Get user profile context using simple manager (no vector DB)
        user_profile_context = ""
        try:
            user_profile_context = get_profile_summary_for_llm(session["user_id"], max_tokens=500)
            if user_profile_context:
                print(f"✅ Got user profile context: {len(user_profile_context)} chars")
        except Exception as context_error:
            print(f"⚠️ Profile context error (non-critical): {context_error}")
        
        # 🚀 ENHANCED: Try Level 2 enhancement first (Perplexity + Llama)
        learning_plan = None
        enhancement_used = False
        
        try:
            print("🔍 Attempting Level 2 enhancement (Perplexity learning methods + Llama structuring)...")
            learning_plan = generate_detailed_learning_plan_with_perplexity(
                phase_name=phase_name,
                skills=skills,
                phase_description=phase_description,
                user_profile=user_profile_context
            )
            enhancement_used = True
            print("✅ Level 2 enhanced learning plan generated")
            
        except Exception as enhancement_error:
            print(f"⚠️ Level 2 enhancement failed: {enhancement_error}")
            print("🔄 Falling back to basic learning plan generation...")
            
            # Fallback to original method
            try:
                learning_plan = generate_learning_plan(
                    phase_name=phase_name,
                    phase_description=phase_description,
                    duration_weeks=duration_weeks
                )
                print("✅ Basic learning plan generated as fallback")
            except Exception as fallback_error:
                print(f"❌ Even fallback failed: {fallback_error}")
                return jsonify({"status": "error", "message": "Failed to generate learning plan"}), 500
        
        if not learning_plan or 'weekly_schedule' not in learning_plan:
            return jsonify({"status": "error", "message": "Invalid learning plan generated"}), 500
        
        # Add the learning plan to the phase
        phase['learning_plan'] = learning_plan
        
        # Initialize task completion tracking
        for week_idx, week in enumerate(learning_plan.get('weekly_schedule', [])):
            for day_idx, task in enumerate(week.get('daily_tasks', [])):
                task['completed'] = False
                task['completed_date'] = None
                task['completion_history'] = []
                # Add task ID for better tracking
                task['task_id'] = f"w{week.get('week', week_idx + 1)}_d{task.get('day', day_idx + 1)}"
        
        # Add metadata to learning plan
        learning_plan['metadata'] = {
            "generated_at": datetime.now().isoformat(),
            "user_id": session["user_id"],
            "phase_id": phase_id,
            "enhancement_level": "level_2_perplexity" if enhancement_used else "basic_fallback",
            "total_weeks": len(learning_plan.get('weekly_schedule', [])),
            "total_tasks": sum(len(week.get('daily_tasks', [])) for week in learning_plan.get('weekly_schedule', [])),
            "progress_percentage": 0,
            "completed_tasks": 0
        }
        
        # Update the roadmap in the database
        db = get_db()
        user_collection = db.users
        
        result = user_collection.update_one(
            {"user_id": session["user_id"]},
            {"$set": {"road_map": json.dumps(roadmap_data)}}
        )
        
        if result.modified_count > 0:
            print(f"✅ Learning plan stored for phase: {phase_name}")
            return jsonify({
                "status": "success", 
                "message": "Learning plan generated successfully",
                "learning_plan": learning_plan,
                "redirect_url": url_for("roadmap_bp.learning_plan", phase_id=phase_id)
            })
        else:
            return jsonify({"status": "error", "message": "Failed to save learning plan"}), 500
            
    except Exception as e:
        print(f"❌ Generate plan error: {e}")
        return jsonify({"status": "error", "message": f"Error generating plan: {str(e)}"}), 500

@roadmap_bp.route('/learning-plan/<string:phase_id>')
def learning_plan(phase_id):
    """🚀 FIXED: Render the learning plan page for a specific phase"""
    print(f"🔍 DEBUG: Accessing learning-plan route for phase_id: {phase_id}")
    
    if "user_id" not in session:
        print("❌ DEBUG: No user_id in session")
        return redirect(url_for("auth_bp.sign_in"))
    
    # Get user data
    user = get_user_by_id(session["user_id"])
    if not user:
        print("❌ DEBUG: User not found")
        return redirect(url_for("auth_bp.sign_in"))
    
    print(f"✅ DEBUG: User found: {user.get('name', 'Unknown')}")
    
    # Get roadmap data
    try:
        roadmap_data = json.loads(user.get('road_map', '{}'))
        print(f"✅ DEBUG: Roadmap data loaded, phases count: {len(roadmap_data.get('phases', []))}")
    except Exception as e:
        print(f"❌ DEBUG: Error parsing roadmap data: {e}")
        return redirect(url_for("roadmap_bp.roadmap"))
    
    # Check if phase exists
    try:
        phase_id_int = int(phase_id)
        print(f"✅ DEBUG: Phase ID converted to int: {phase_id_int}")
        
        if phase_id_int < 0 or phase_id_int >= len(roadmap_data.get('phases', [])):
            print(f"❌ DEBUG: Phase ID out of range. Available phases: 0-{len(roadmap_data.get('phases', [])) - 1}")
            return redirect(url_for("roadmap_bp.roadmap"))
        
        phase = roadmap_data['phases'][phase_id_int]
        phase_name = phase.get('name', phase.get('title', 'Unknown'))
        print(f"✅ DEBUG: Phase found: {phase_name}")
        
    except (ValueError, IndexError, KeyError) as e:
        print(f"❌ DEBUG: Error accessing phase: {e}")
        return redirect(url_for("roadmap_bp.roadmap"))
    
    # Check if learning plan exists
    if not phase.get('learning_plan'):
        print("⚠️ DEBUG: No learning plan found, showing generation page")
        # Return a simple HTML page that will trigger the generation
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Generate Learning Plan</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .btn {{ background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }}
                .btn:hover {{ background: #0056b3; }}
                .loading {{ display: none; color: #666; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚀 Generate Learning Plan</h1>
                <h2>Phase: {phase_name}</h2>
                <p>No learning plan exists for this phase yet. Click the button below to generate an enhanced learning plan.</p>
                
                <button class="btn" onclick="generatePlan()">Generate Learning Plan</button>
                <div class="loading" id="loading">
                    <p>🔄 Generating your personalized learning plan... This may take a moment.</p>
                </div>
                
                <script>
                function generatePlan() {{
                    document.getElementById('loading').style.display = 'block';
                    document.querySelector('.btn').disabled = true;
                    
                    fetch('/generate-plan/{phase_id}', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                        }}
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            window.location.reload();
                        }} else {{
                            alert('Error: ' + data.message);
                            document.getElementById('loading').style.display = 'none';
                            document.querySelector('.btn').disabled = false;
                        }}
                    }})
                    .catch(error => {{
                        alert('Error generating plan: ' + error);
                        document.getElementById('loading').style.display = 'none';
                        document.querySelector('.btn').disabled = false;
                    }});
                }}
                </script>
                
                <p><a href="/road-map">← Back to Roadmap</a></p>
            </div>
        </body>
        </html>
        """
    
    print("✅ DEBUG: Learning plan found, rendering template")
    
    # Try to render the template, with fallback
    try:
        return render_template('learning_plan.html', 
                             phase=phase, 
                             user=user, 
                             phase_id=phase_id)
    except Exception as template_error:
        print(f"❌ DEBUG: Template error: {template_error}")
        # Fallback: return simple HTML with learning plan data
        learning_plan = phase['learning_plan']
        weekly_schedule = learning_plan.get('weekly_schedule', [])
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Learning Plan - {phase_name}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; }}
                .week {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .task {{ margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 3px; }}
                .completed {{ background: #d4edda !important; }}
                .btn {{ background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 3px; cursor: pointer; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📚 Learning Plan: {phase_name}</h1>
                <p><strong>User:</strong> {user.get('name', 'Unknown')}</p>
                <p><a href="/road-map">← Back to Roadmap</a></p>
                
                <div id="learning-plan">
        """
        
        for week_idx, week in enumerate(weekly_schedule):
            html_content += f"""
                    <div class="week">
                        <h3>Week {week.get('week', week_idx + 1)}: {week.get('title', 'Learning Week')}</h3>
                        <p>{week.get('description', '')}</p>
            """
            
            for day_idx, task in enumerate(week.get('daily_tasks', [])):
                completed_class = "completed" if task.get('completed', False) else ""
                html_content += f"""
                        <div class="task {completed_class}">
                            <strong>Day {task.get('day', day_idx + 1)}:</strong> {task.get('task', 'Learning Task')}
                            <br><small>{task.get('description', '')}</small>
                            <br>
                            <button class="btn" onclick="toggleTask({phase_id}, {week_idx}, {day_idx}, {str(not task.get('completed', False)).lower()})">
                                {'✅ Mark Incomplete' if task.get('completed', False) else '☐ Mark Complete'}
                            </button>
                        </div>
                """
            
            html_content += "</div>"
        
        html_content += f"""
                </div>
                
                <script>
                function toggleTask(phaseId, weekIdx, dayIdx, completed) {{
                    fetch('/complete-task', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{
                            phase_id: phaseId,
                            week_index: weekIdx,
                            day_index: dayIdx,
                            completed: completed
                        }})
                    }})
                    .then(response => response.json())
                    .then(data => {{
                        if (data.status === 'success') {{
                            window.location.reload();
                        }} else {{
                            alert('Error: ' + data.message);
                        }}
                    }});
                }}
                </script>
            </div>
        </body>
        </html>
        """
        
        return html_content

@roadmap_bp.route('/complete-task', methods=['POST'])
def complete_task():
    """🚀 ENHANCED: Mark a task as completed with better tracking"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    data = request.json
    phase_id = data.get('phase_id')
    week_index = data.get('week_index')
    day_index = data.get('day_index')
    completed = data.get('completed', False)
    
    if not all([phase_id is not None, week_index is not None, day_index is not None]):
        return jsonify({"status": "error", "message": "Missing required parameters"}), 400
    
    try:
        # Get user data
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        # Get roadmap data
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Update the task completion status
        phase = roadmap_data['phases'][int(phase_id)]
        weekly_schedule = phase['learning_plan']['weekly_schedule']
        task = weekly_schedule[int(week_index)]['daily_tasks'][int(day_index)]
        
        # Update task status
        task['completed'] = completed
        task['completed_date'] = datetime.now().isoformat() if completed else None
        
        # Add completion tracking metadata
        if 'completion_history' not in task:
            task['completion_history'] = []
        
        task['completion_history'].append({
            "timestamp": datetime.now().isoformat(),
            "action": "completed" if completed else "uncompleted",
            "user_id": session["user_id"]
        })
        
        # Calculate phase progress
        total_tasks = 0
        completed_tasks = 0
        for week in weekly_schedule:
            for daily_task in week.get('daily_tasks', []):
                total_tasks += 1
                if daily_task.get('completed', False):
                    completed_tasks += 1
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Update phase metadata
        if 'learning_plan' in phase and 'metadata' in phase['learning_plan']:
            phase['learning_plan']['metadata']['last_updated'] = datetime.now().isoformat()
            phase['learning_plan']['metadata']['progress_percentage'] = round(progress_percentage, 1)
            phase['learning_plan']['metadata']['completed_tasks'] = completed_tasks
            phase['learning_plan']['metadata']['total_tasks'] = total_tasks
        
        # Update the database
        db = get_db()
        result = db.users.update_one(
            {"user_id": session["user_id"]},
            {"$set": {"road_map": json.dumps(roadmap_data)}}
        )
        
        if result.modified_count > 0:
            return jsonify({
                "status": "success", 
                "message": "Task updated successfully",
                "progress": {
                    "completed_tasks": completed_tasks,
                    "total_tasks": total_tasks,
                    "percentage": round(progress_percentage, 1)
                }
            })
        else:
            return jsonify({"status": "error", "message": "Failed to update task"}), 500
    
    except Exception as e:
        print(f"❌ Task completion error: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@roadmap_bp.route('/api/roadmap/progress', methods=['POST'])
def update_progress():
    """Update learning progress for a specific module"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        phase_id = data.get('phase_id')
        week_id = data.get('week_id') 
        day_id = data.get('day_id')
        task_id = data.get('task_id')
        completed = data.get('completed', False)
        
        # Get user data
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        # Get roadmap data
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Update the specific task completion status
        try:
            task = roadmap_data['phases'][phase_id]['learning_plan']['weekly_schedule'][week_id]['daily_tasks'][day_id]['tasks'][task_id]
            task['completed'] = completed
            task['completed_at'] = datetime.now().isoformat() if completed else None
            
            # Update in database
            db = get_db()
            user_collection = db.users
            
            result = user_collection.update_one(
                {"user_id": session["user_id"]},
                {"$set": {"road_map": json.dumps(roadmap_data)}}
            )
            
            if result.modified_count > 0:
                return jsonify({"status": "success", "message": "Progress updated"})
            else:
                return jsonify({"status": "error", "message": "Failed to update progress"}), 500
                
        except (IndexError, KeyError) as e:
            return jsonify({"status": "error", "message": "Invalid task reference"}), 400
            
    except Exception as e:
        print(f"❌ Progress update error: {e}")
        return jsonify({"status": "error", "message": f"Error updating progress: {str(e)}"}), 500

@roadmap_bp.route('/api/roadmap/stats/<user_id>')
def get_roadmap_stats(user_id):
    """Get roadmap completion statistics"""
    if "user_id" not in session or session["user_id"] != user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        if not roadmap_data or 'phases' not in roadmap_data:
            return jsonify({"error": "No roadmap found"}), 404
        
        total_tasks = 0
        completed_tasks = 0
        
        # Count tasks and completion
        for phase in roadmap_data['phases']:
            learning_plan = phase.get('learning_plan', {})
            weekly_schedule = learning_plan.get('weekly_schedule', [])
            
            for week in weekly_schedule:
                daily_tasks = week.get('daily_tasks', [])
                for task in daily_tasks:
                    total_tasks += 1
                    if task.get('completed', False):
                        completed_tasks += 1
        
        completion_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        return jsonify({
            "status": "success",
            "stats": {
                "total_phases": len(roadmap_data['phases']),
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "completion_percentage": round(completion_percentage, 2),
                "phases_with_plans": len([p for p in roadmap_data['phases'] if p.get('learning_plan')])
            }
        })
        
    except Exception as e:
        print(f"❌ Roadmap stats error: {e}")
        return jsonify({"error": f"Failed to get stats: {str(e)}"}), 500
    
# Add these missing methods and routes to your roadmap.py file

# Complete the AdaptiveRoadmapManager class (add the missing methods)

def _generate_delay_recommendations(self, delay_analysis):
    """💡 Generate personalized recommendations for catching up"""
    
    recommendations = []
    risk_level = delay_analysis["risk_level"]
    total_behind = delay_analysis["total_days_behind"]
    
    if risk_level == "low":
        recommendations.append({
            "type": "motivation",
            "title": "Keep Up the Great Work! 🎉",
            "description": "You're on track with your learning goals. Maintain this momentum!",
            "action": "Continue daily practice"
        })
    
    elif risk_level == "medium":
        recommendations.append({
            "type": "gentle_reminder",
            "title": "Small Catch-Up Needed 📚",
            "description": f"You're {total_behind} days behind schedule. A focused weekend can get you back on track!",
            "action": "Dedicate 2-3 hours this weekend to catch up"
        })
    
    elif risk_level == "high":
        recommendations.append({
            "type": "intensive_catchup",
            "title": "Time for Intensive Catch-Up 🚀",
            "description": f"You're {total_behind} days behind. Let's create a focused catch-up plan.",
            "action": "Switch to accelerated learning mode for 1 week"
        })
        
    elif risk_level == "critical":
        recommendations.append({
            "type": "curriculum_adjustment",
            "title": "Curriculum Adjustment Needed 🔄",
            "description": f"You're {total_behind} days behind. Let's modify your learning path to focus on core concepts.",
            "action": "Activate emergency catch-up mode with simplified curriculum"
        })
    
    return recommendations

def _generate_adaptations(self, progress_analysis, delay_analysis):
    """🔧 Generate specific curriculum adaptations"""
    
    adaptations = {
        "schedule_adjustments": [],
        "content_modifications": [],
        "difficulty_changes": [],
        "timeline_extensions": [],
        "catch_up_plans": []
    }
    
    risk_level = delay_analysis["risk_level"]
    learning_velocity = progress_analysis["learning_velocity"]
    
    # Schedule adjustments based on learning velocity
    if learning_velocity == "slow" or risk_level in ["high", "critical"]:
        adaptations["schedule_adjustments"].append({
            "type": "extend_timeline",
            "description": "Extend daily learning time by 30 minutes",
            "adjustment": "timeline_extension"
        })
        
        adaptations["content_modifications"].append({
            "type": "simplify_content",
            "description": "Focus on core concepts, reduce advanced topics",
            "adjustment": "content_simplification"
        })
    
    elif learning_velocity == "fast":
        adaptations["difficulty_changes"].append({
            "type": "increase_challenge",
            "description": "Add bonus challenges and advanced projects",
            "adjustment": "difficulty_increase"
        })
    
    # Specific catch-up plans
    if delay_analysis["total_days_behind"] > 0:
        adaptations["catch_up_plans"].append({
            "type": "weekend_intensive",
            "days_to_recover": delay_analysis["total_days_behind"],
            "estimated_hours": delay_analysis["total_days_behind"] * 2,
            "description": f"Intensive {delay_analysis['total_days_behind']}-day catch-up program"
        })
    
    return adaptations

def _apply_adaptations(self, roadmap_data, adaptations):
    """🔄 Apply adaptations to the roadmap"""
    
    adapted_roadmap = json.loads(json.dumps(roadmap_data))  # Deep copy
    
    # Add adaptation metadata
    if 'adaptive_settings' not in adapted_roadmap:
        adapted_roadmap['adaptive_settings'] = {}
    
    adapted_roadmap['adaptive_settings'].update({
        'last_adaptation': datetime.now().isoformat(),
        'applied_adaptations': adaptations,
        'adaptation_count': adapted_roadmap.get('adaptive_settings', {}).get('adaptation_count', 0) + 1
    })
    
    # Apply specific adaptations to phases
    for phase in adapted_roadmap.get('phases', []):
        if phase.get('learning_plan'):
            # Add adaptation flags to learning plan
            if 'adaptation_flags' not in phase['learning_plan']:
                phase['learning_plan']['adaptation_flags'] = {}
            
            # Apply content modifications
            for modification in adaptations.get('content_modifications', []):
                if modification['type'] == 'simplify_content':
                    phase['learning_plan']['adaptation_flags']['content_simplified'] = True
                    phase['learning_plan']['adaptation_flags']['focus_mode'] = 'core_concepts'
            
            # Apply difficulty changes
            for change in adaptations.get('difficulty_changes', []):
                if change['type'] == 'increase_challenge':
                    phase['learning_plan']['adaptation_flags']['difficulty_increased'] = True
                    phase['learning_plan']['adaptation_flags']['bonus_content'] = True
    
    return adapted_roadmap

def _save_adapted_roadmap(self, user_id, adapted_roadmap, adaptations):
    """💾 Save the adapted roadmap to database"""
    
    try:
        result = self.db.users.update_one(
            {"user_id": user_id},
            {"$set": {"road_map": json.dumps(adapted_roadmap)}}
        )
        
        # Also save adaptation history
        adaptation_record = {
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
            "adaptations": adaptations,
            "adaptation_type": "automatic"
        }
        
        self.db.adaptation_history.insert_one(adaptation_record)
        
        print(f"✅ Adapted roadmap saved for user {user_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving adapted roadmap: {e}")
        return False

def _analyze_phase_delays(self, phase, phase_idx, current_date):
    """🔍 Analyze delays for a specific phase"""
    
    phase_start = phase.get('learning_plan', {}).get('metadata', {}).get('generated_at')
    if phase_start:
        phase_start_date = datetime.fromisoformat(phase_start.replace('Z', '+00:00'))
    else:
        phase_start_date = current_date
    
    days_since_start = (current_date - phase_start_date).days
    weekly_schedule = phase['learning_plan']['weekly_schedule']
    
    total_expected_by_now = 0
    total_completed = 0
    missed_days_streak = 0
    current_streak = 0
    
    day_count = 0
    for week in weekly_schedule:
        for task in week.get('daily_tasks', []):
            day_count += 1
            
            if day_count <= days_since_start:
                total_expected_by_now += 1
                
                if task.get('completed', False):
                    total_completed += 1
                    current_streak = 0
                else:
                    current_streak += 1
                    missed_days_streak = max(missed_days_streak, current_streak)
    
    return {
        "phase_id": phase_idx,
        "phase_name": phase.get('name', f'Phase {phase_idx + 1}'),
        "days_behind": max(0, total_expected_by_now - total_completed),
        "expected_by_now": total_expected_by_now,
        "actually_completed": total_completed,
        "longest_missed_streak": missed_days_streak,
        "start_date": phase_start_date.isoformat()
    }

# Add these new routes to your roadmap.py file

@roadmap_bp.route('/api/roadmap/analyze-and-adapt', methods=['POST'])
def analyze_and_adapt_roadmap():
    """🧠 Manual trigger for roadmap adaptation analysis"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        user_id = session["user_id"]
        
        # Get current roadmap
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
            
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        if not roadmap_data or 'phases' not in roadmap_data:
            return jsonify({"status": "error", "message": "No roadmap found"}), 404
        
        # Run adaptive analysis
        adaptive_manager = AdaptiveRoadmapManager()
        result = adaptive_manager.analyze_progress_and_adapt(user_id, roadmap_data)
        
        print(f"🧠 Adaptive analysis completed for user {user_id}")
        print(f"   📊 Status: {result.get('status')}")
        
        if result['status'] == 'success':
            print(f"   🎯 Learning velocity: {result['progress_analysis']['learning_velocity']}")
            print(f"   🚨 Risk level: {result['delay_analysis']['risk_level']}")
            print(f"   🔧 Adaptations applied: {len(result['adaptations_applied'])}")
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Manual adaptation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

@roadmap_bp.route('/api/roadmap/refresh-progress', methods=['POST'])
def refresh_roadmap_progress():
    """✅ NEW: Endpoint to refresh roadmap progress in real-time"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401
    
    try:
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Create adaptive manager instance and calculate progress
        adaptive_manager = AdaptiveRoadmapManager()
        progress_metrics = adaptive_manager._calculate_detailed_progress(roadmap_data)
        
        # Update global stats in database
        if 'global_stats' not in roadmap_data:
            roadmap_data['global_stats'] = {}
            
        roadmap_data['global_stats'].update({
            'last_updated': datetime.now().isoformat(),
            'overall_progress': progress_metrics['overall_stats'],
            'daily_completion_rate': progress_metrics['daily_completion_rate'],
            'learning_velocity': progress_metrics['learning_velocity'],
            'expected_vs_actual': progress_metrics['expected_vs_actual']
        })
        
        # Save updated roadmap
        db = get_db()
        db.users.update_one(
            {"user_id": session["user_id"]},
            {"$set": {"road_map": json.dumps(roadmap_data)}}
        )
        
        print(f"✅ Roadmap progress refreshed for user {session['user_id']}")
        
        return jsonify({
            "status": "success",
            "message": "Roadmap progress refreshed",
            "progress_metrics": progress_metrics
        })
        
    except Exception as e:
        print(f"❌ Roadmap refresh error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Enhanced complete-task route with adaptive analysis
@roadmap_bp.route('/complete-task', methods=['POST'])
def complete_task_with_adaptation():
    """✅ ENHANCED: Complete task and trigger adaptive analysis"""
    if "user_id" not in session:
        return jsonify({"status": "error", "message": "Not authenticated"}), 401

    try:
        data = request.get_json()
        phase_id = int(data.get('phase_id', 0))
        week_index = int(data.get('week_index', 0))
        day_index = int(data.get('day_index', 0))
        completed = bool(data.get('completed', False))
        auto_completed = bool(data.get('auto_completed_by_assessment', False))
        
        print(f"📝 Task completion request:")
        print(f"   📌 Phase: {phase_id}, Week: {week_index}, Day: {day_index}")
        print(f"   📌 Completed: {completed}")
        print(f"   📌 Auto-completed by assessment: {auto_completed}")

        # Get user data
        user = get_user_by_id(session["user_id"])
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        # Get roadmap data
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Update the task completion status
        phase = roadmap_data['phases'][phase_id]
        weekly_schedule = phase['learning_plan']['weekly_schedule']
        task = weekly_schedule[week_index]['daily_tasks'][day_index]
        
        # ✅ ENHANCED: Store completion details
        task['completed'] = completed
        task['completed_date'] = datetime.now().isoformat() if completed else None
        
        # ✅ NEW: Add auto-completion metadata
        if auto_completed:
            task['auto_completed_by_assessment'] = True
            task['assessment_completion_date'] = datetime.now().isoformat()
            print(f"✅ Task auto-completed by successful assessment!")
        
        # Add completion tracking metadata
        if 'completion_history' not in task:
            task['completion_history'] = []
        
        task['completion_history'].append({
            "timestamp": datetime.now().isoformat(),
            "action": "completed" if completed else "uncompleted",
            "user_id": session["user_id"],
            "auto_completed": auto_completed,
            "completion_source": "assessment" if auto_completed else "manual"
        })
        
        # Calculate basic progress for immediate response
        total_tasks = 0
        completed_tasks = 0
        for week in weekly_schedule:
            for daily_task in week.get('daily_tasks', []):
                total_tasks += 1
                if daily_task.get('completed', False):
                    completed_tasks += 1
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Update phase metadata
        if 'learning_plan' in phase:
            if 'metadata' not in phase['learning_plan']:
                phase['learning_plan']['metadata'] = {}
                
            phase['learning_plan']['metadata'].update({
                'last_updated': datetime.now().isoformat(),
                'progress_percentage': round(progress_percentage, 1),
                'completed_tasks': completed_tasks,
                'total_tasks': total_tasks
            })
        
        # Update the database
        db = get_db()
        result = db.users.update_one(
            {"user_id": session["user_id"]},
            {"$set": {"road_map": json.dumps(roadmap_data)}}
        )
        
        # Prepare response
        response_data = {
            "status": "success", 
            "message": "Task automatically completed by successful assessment!" if auto_completed else "Task updated successfully",
            "auto_completed": auto_completed,
            "progress": {
                "completed_tasks": completed_tasks,
                "total_tasks": total_tasks,
                "percentage": round(progress_percentage, 1)
            },
            "task_details": {
                "day": day_index + 1,
                "week": week_index + 1,
                "phase": phase_id,
                "completion_source": "assessment" if auto_completed else "manual"
            }
        }
        
        # ✅ TRIGGER ADAPTIVE ANALYSIS (async-style)
        if result.modified_count > 0 and completed:
            try:
                print(f"🧠 Triggering adaptive analysis...")
                adaptive_manager = AdaptiveRoadmapManager()
                adaptation_result = adaptive_manager.analyze_progress_and_adapt(session["user_id"], roadmap_data)
                
                if adaptation_result['status'] == 'success':
                    response_data['adaptive_analysis'] = {
                        "progress_analysis": adaptation_result['progress_analysis'],
                        "delay_analysis": adaptation_result['delay_analysis'],
                        "adaptations_applied": adaptation_result['adaptations_applied']
                    }
                    
                    print(f"🧠 Adaptive analysis completed:")
                    print(f"   📊 Learning velocity: {adaptation_result['progress_analysis']['learning_velocity']}")
                    print(f"   🚨 Risk level: {adaptation_result['delay_analysis']['risk_level']}")
                
            except Exception as adaptive_error:
                print(f"⚠️ Adaptive analysis failed (non-critical): {adaptive_error}")
                # Don't fail the main task completion if adaptive analysis fails
        
        if result.modified_count > 0:
            print(f"✅ Task completion successful")
            return jsonify(response_data)
        else:
            return jsonify({"status": "error", "message": "Failed to update task"}), 500
    
    except Exception as e:
        print(f"❌ Task completion error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500