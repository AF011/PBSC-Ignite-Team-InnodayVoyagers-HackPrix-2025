# app/routes/integrated_assessment.py
"""
🧠 INTEGRATED ASSESSMENT SYSTEM
Assessments directly embedded in learning plans with smart unlocking

Flow:
1. Learning plan shows Day 1, Day 2, Day 3... with assessment buttons
2. First assessment unlocks after Leo AI interaction OR toggle activation
3. Sequential unlocking: Complete previous day → next day unlocks
4. Dynamic assessment generation using Claude Sonnet based on day content
"""

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from datetime import datetime, timedelta
import json
import boto3
import os
from groq import Groq
from app.utils.db_utils import get_db, get_user_by_id

import requests
import base64
import re

# Create blueprint
integrated_assessment_bp = Blueprint('integrated_assessment_bp', __name__)


# ADD this new class after your existing classes
class GitHubAnalyzer:
    """GitHub repository analyzer for coding assessments"""
    
    def __init__(self, bedrock_client=None):
        self.bedrock_client = bedrock_client
    
    def parse_github_url(self, url):
        """Extract owner and repo from GitHub URL"""
        pattern = r'github\.com/([^/]+)/([^/]+)'
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2).rstrip('.git')
        return None, None
    
    def get_repo_info(self, owner, repo):
        """Get basic repository information"""
        url = f"https://api.github.com/repos/{owner}/{repo}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    def get_file_content(self, owner, repo, path):
        """Get content of a specific file"""
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                file_data = response.json()
                if file_data.get('encoding') == 'base64':
                    return base64.b64decode(file_data['content']).decode('utf-8')
        except:
            pass
        return None
    
    def analyze_repository(self, github_url):
        """Analyze GitHub repository for assessment"""
        owner, repo = self.parse_github_url(github_url)
        if not owner or not repo:
            return {"error": "Invalid GitHub URL"}
        
        # Get repo info
        repo_info = self.get_repo_info(owner, repo)
        if not repo_info:
            return {"error": "Repository not found or private"}
        
        analysis = {
            "repo_accessible": True,
            "language": repo_info.get('language', 'Unknown'),
            "size_kb": repo_info.get('size', 0),
            "has_description": bool(repo_info.get('description')),
            "code_analysis": {},
            "ai_probability": 0,
            "quality_score": 0
        }
        
        # Try to get main code files
        main_files = ['main.py', 'app.py', 'index.js', 'script.js', 'main.java']
        code_found = False
        
        for filename in main_files:
            content = self.get_file_content(owner, repo, filename)
            if content:
                analysis["code_analysis"][filename] = self.analyze_code_content(content)
                code_found = True
                break
        
        if code_found:
            analysis["quality_score"] = self.calculate_quality_score(analysis)
            analysis["ai_probability"] = self.detect_ai_patterns(analysis)
        
        return analysis
    
    def analyze_code_content(self, content):
        """Analyze code content for quality metrics"""
        lines = content.split('\n')
        code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        
        return {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "has_functions": any('def ' in line for line in lines),
            "has_comments": any(line.strip().startswith('#') for line in lines),
            "has_error_handling": any('try:' in line or 'except' in line for line in lines),
        }
    
    def calculate_quality_score(self, analysis):
        """Calculate overall code quality score"""
        score = 0
        
        # Check if code exists
        if analysis["code_analysis"]:
            score += 40
            
            # Check code structure
            for file_analysis in analysis["code_analysis"].values():
                if file_analysis["has_functions"]:
                    score += 20
                if file_analysis["has_comments"]:
                    score += 15
                if file_analysis["has_error_handling"]:
                    score += 15
                if file_analysis["code_lines"] > 10:  # Substantial code
                    score += 10
        
        return min(score, 100)
    
    def detect_ai_patterns(self, analysis):
        """Simple AI detection based on patterns"""
        ai_score = 0
        
        # Very basic detection - you can enhance this
        for file_analysis in analysis["code_analysis"].values():
            if file_analysis["code_lines"] < 5:  # Too short
                ai_score += 20
            if not file_analysis["has_comments"]:  # No comments at all
                ai_score += 15
        
        return min(ai_score, 100)

# REPLACE your current strict_coding_evaluation function with this:
def strict_coding_evaluation(user_answers: dict, day_content: dict) -> dict:
    """
    ✅ ENHANCED GitHub-powered coding evaluation
    """
    try:
        github_url = user_answers.get('github_url', '').strip()
        description = user_answers.get('description', '').strip()
        
        print(f"🔍 Enhanced coding evaluation starting...")
        print(f"📍 GitHub URL: {github_url}")
        
        score = 0
        feedback_points = []
        
        # 1. Basic validation (30 points)
        if not github_url:
            return {
                "score": 0,
                "feedback": "❌ GitHub repository URL is required for coding assessments.",
                "status": "FAILED - NO SUBMISSION"
            }
        
        if 'github.com' not in github_url:
            return {
                "score": 10,
                "feedback": "❌ Please provide a valid GitHub repository URL.",
                "status": "FAILED - INVALID URL"
            }
        
        score += 30
        feedback_points.append("✅ Valid GitHub URL provided")
        
        # 2. Description quality (20 points)
        if len(description) > 100:
            score += 20
            feedback_points.append("✅ Comprehensive project description")
        elif len(description) > 50:
            score += 15
            feedback_points.append("✅ Good project description")
        elif len(description) > 20:
            score += 10
            feedback_points.append("⚠️ Basic description provided")
        else:
            feedback_points.append("❌ Description too brief")
        
        # 3. GitHub Repository Analysis (50 points)
        try:
            # Initialize GitHub analyzer
            bedrock_client = None
            try:
                bedrock_client = boto3.client(
                    'bedrock-runtime',
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                    region_name='ap-south-1'
                )
            except:
                pass
            
            analyzer = GitHubAnalyzer(bedrock_client)
            repo_analysis = analyzer.analyze_repository(github_url)
            
            if "error" in repo_analysis:
                feedback_points.append(f"❌ Repository analysis failed: {repo_analysis['error']}")
                score += 10  # Partial credit for valid URL
            else:
                print(f"✅ Repository analysis completed")
                
                # Repository accessible (10 points)
                if repo_analysis["repo_accessible"]:
                    score += 10
                    feedback_points.append("✅ Repository is accessible")
                
                # Has description (5 points)
                if repo_analysis["has_description"]:
                    score += 5
                    feedback_points.append("✅ Repository has description")
                
                # Code quality analysis (35 points)
                quality_score = repo_analysis.get("quality_score", 0)
                
                if quality_score >= 80:
                    code_points = 35
                    feedback_points.append("✅ Excellent code quality detected")
                elif quality_score >= 60:
                    code_points = 25
                    feedback_points.append("✅ Good code quality")
                elif quality_score >= 40:
                    code_points = 15
                    feedback_points.append("⚠️ Basic code structure found")
                else:
                    code_points = 5
                    feedback_points.append("❌ Limited code found")
                
                score += code_points
                
                # AI detection warning
                ai_prob = repo_analysis.get("ai_probability", 0)
                if ai_prob > 60:
                    score = max(score - 20, 0)  # Penalty for likely AI code
                    feedback_points.append("⚠️ High AI probability detected - code review needed")
                elif ai_prob > 30:
                    feedback_points.append("⚠️ Some AI patterns detected")
                
                print(f"📊 Quality Score: {quality_score}%, AI Probability: {ai_prob}%")
        
        except Exception as analysis_error:
            print(f"❌ GitHub analysis error: {analysis_error}")
            score += 20  # Partial credit if analysis fails
            feedback_points.append("⚠️ Could not analyze repository content - manual review needed")
        
        # Final evaluation
        final_score = max(0, min(100, score))
        
        if final_score >= 70:
            status = "PASSED"
            feedback = f"🎉 Excellent work! Score: {final_score}%. " + " ".join(feedback_points)
        else:
            status = "FAILED - RETAKE REQUIRED"
            feedback = f"📚 Score: {final_score}% (Need 70% to pass). " + " ".join(feedback_points) + " Please improve and resubmit."
        
        print(f"🏁 Final evaluation: {final_score}% - {status}")
        
        return {
            "score": final_score,
            "feedback": feedback,
            "status": status,
            "next_steps": "Continue to next assessment" if final_score >= 70 else "Improve repository and resubmit"
        }
        
    except Exception as e:
        print(f"❌ Coding evaluation error: {e}")
        return {
            "score": 0,
            "feedback": "Evaluation error occurred. Please check your GitHub URL and try again.",
            "status": "ERROR"
        }

class SonnetAssessmentEngine:
    """
    🤖 Claude Sonnet-powered Assessment Generator
    Creates dynamic assessments based on learning content
    """
    
    def __init__(self):
        self.db = get_db()
        # Initialize AWS Bedrock client for Claude Sonnet
        self.bedrock_client = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name='ap-south-1'
        )
    
    def generate_assessment(self, day_content: dict, assessment_type: str = "theory") -> dict:
        """
        Generate dynamic assessment using Claude Sonnet
        
        Args:
            day_content: The learning content for that day
            assessment_type: "theory" or "coding"
        """
        try:
            if assessment_type == "theory":
                return self._generate_theory_assessment(day_content)
            elif assessment_type == "coding":
                return self._generate_coding_assessment(day_content)
            else:
                return {"error": "Invalid assessment type"}
                
        except Exception as e:
            print(f"❌ Assessment generation error: {e}")
            return {"error": str(e)}
    
    def _generate_theory_assessment(self, day_content: dict) -> dict:
        """Generate Q&A form assessment for theory content"""
        
        task_description = day_content.get('task', '')
        learning_objectives = day_content.get('description', '')
        learning_objectives = day_content.get('description', '')
        print("Task Description - ", task_description)
        print("Learning Objectives - ", learning_objectives)
        
        
        prompt = f"""
You are Leo AI, an expert assessment creator. Generate a comprehensive learning assessment for this day's content:

**Day Content:**
{day_content}

Create a JSON assessment with this EXACT structure:
{{
    "assessment_type": "theory",
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "Clear, specific question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation": "Why this answer is correct",
            "difficulty": "easy|medium|hard"
        }},
        {{
            "id": 2,
            "type": "short_answer",
            "question": "Question requiring 2-3 sentence explanation",
            "expected_keywords": ["keyword1", "keyword2", "keyword3"],
            "difficulty": "medium"
        }},
        {{
            "id": 3,
            "type": "scenario",
            "question": "Real-world scenario question",
            "scenario": "Detailed scenario description",
            "expected_approach": "Step-by-step approach expected",
            "difficulty": "hard"
        }}
    ],
    "total_questions": 3,
    "passing_score": 70,
    "estimated_time": "15-20 minutes"
}}

Requirements:
- Generate 3-5 relevant questions
- Mix difficulty levels (easy/medium/hard)
- Include practical scenarios
- Focus on understanding, not memorization
- Questions should test comprehension of: {task_description}

Return ONLY the JSON, no additional text.
"""
        
        return self._call_sonnet(prompt)
    
    def _generate_coding_assessment(self, day_content: dict) -> dict:
        """Generate coding project assessment with GitHub integration"""
        
        task_description = day_content.get('task', '')
        learning_objectives = day_content.get('description', '')
        
        prompt = f"""
You are Leo AI, an expert coding mentor. Generate a comprehensive coding assessment for this day's content:

**Day Content:**
Task: {task_description}
Learning Focus: {learning_objectives}

Create a JSON assessment with this EXACT structure:
{{
    "assessment_type": "coding",
    "project_title": "Descriptive project title",
    "project_description": "Clear project overview",
    "requirements": [
        "Specific requirement 1",
        "Specific requirement 2", 
        "Specific requirement 3"
    ],
    "github_guidelines": {{
        "repository_structure": "Expected folder structure",
        "file_requirements": ["Required files with descriptions"],
        "commit_guidelines": "How to structure commits",
        "readme_requirements": "What to include in README"
    }},
    "submission_criteria": [
        "Code functionality criteria",
        "Code quality criteria",
        "Documentation criteria"
    ],
    "evaluation_rubric": {{
        "functionality": "40%",
        "code_quality": "30%", 
        "documentation": "20%",
        "creativity": "10%"
    }},
    "estimated_time": "2-4 hours",
    "difficulty": "medium",
    "bonus_challenges": [
        "Optional advanced feature 1",
        "Optional advanced feature 2"
    ]
}}

Requirements:
- Create a practical coding project related to: {task_description}
- Include clear GitHub submission guidelines
- Provide evaluation rubric
- Add optional bonus challenges
- Make it achievable but challenging

Return ONLY the JSON, no additional text.
"""
        
        return self._call_sonnet(prompt)
    
    def _call_sonnet(self, prompt: str) -> dict:
        """Call Claude Sonnet via AWS Bedrock"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId="anthropic.claude-3-sonnet-20240229-v1:0",
                body=json.dumps(body),
                contentType="application/json"
            )
            
            response_body = json.loads(response['body'].read())
            sonnet_response = response_body['content'][0]['text']
            
            # Parse JSON from response
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', sonnet_response, re.DOTALL)
                if json_match:
                    assessment_data = json.loads(json_match.group(0))
                    return assessment_data
                else:
                    return {"error": "No JSON found in Sonnet response"}
            except json.JSONDecodeError as e:
                return {"error": f"JSON parsing error: {e}"}
                
        except Exception as e:
            print(f"❌ Sonnet API error: {e}")
            return {"error": f"Sonnet API error: {e}"}

class SmartAssessmentDetector:
    """
    🤖 IMPROVED: Send complete day content to Llama for better detection
    """
    
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    def detect_assessment_type_and_content(self, day_content: dict) -> dict:
        """
        Send COMPLETE day content to Llama for accurate detection
        """
        try:
            print(f"🦙 Sending COMPLETE day content to Llama for analysis...")
            print(f"📦 Full content: {day_content}")
            
            # Build comprehensive analysis prompt with FULL content
            analysis_prompt = f"""
You are Leo AI, an expert learning analyst. Analyze this COMPLETE learning content and determine the assessment type.

**COMPLETE DAY CONTENT:**
{json.dumps(day_content, indent=2)}

**YOUR TASK:**
Look at the actual learning activities and determine if this needs:
- "coding" = Students need to write/practice code, build projects, implement solutions
- "theory" = Students need to understand concepts, answer questions, explain ideas
- "mixed" = Combination of both coding and theory

**ANALYSIS GUIDELINES:**
- Words like "practice", "implement", "build", "create", "calculator" = CODING
- Words like "learn", "understand", "study", "concept" = THEORY
- Look at the specific tasks/activities, not just titles
- Favor CODING for any hands-on programming work

**REQUIRED JSON RESPONSE:**
{{
    "assessment_type": "coding|theory|mixed",
    "confidence": 0.85,
    "reasoning": "Clear explanation of why this type was chosen",
    "key_indicators": ["practice control flow", "implement calculator"],
    "assessment_category": "coding_practice|conceptual_understanding|practical_application",
    "content_focus": "What the assessment should test",
    "recommended_format": "coding_project|multiple_choice_and_short_answer|github_submission",
    "estimated_duration": "30 minutes|1-2 hours|2-4 hours"
}}

**EXAMPLES:**
- "Practice control flow and functions" → "coding" (hands-on programming)
- "Implement a simple calculator" → "coding" (building something)
- "Learn about variables" → "theory" (conceptual understanding)
- "Understand how loops work" → "theory" (explanation needed)

Analyze the COMPLETE content above and return ONLY valid JSON.
"""
            
            # Call Llama with the complete content
            response = self._call_llama_analyzer(analysis_prompt)
            
            if isinstance(response, dict) and 'assessment_type' in response:
                print(f"🦙 Llama Analysis Results:")
                print(f"   🎯 Type: {response.get('assessment_type')}")
                print(f"   🎯 Confidence: {response.get('confidence', 0)}")
                print(f"   🎯 Reasoning: {response.get('reasoning', 'No reasoning')}")
                print(f"   🎯 Key Indicators: {response.get('key_indicators', [])}")
                
                return response
            else:
                print("❌ Llama response invalid, using fallback")
                return self._smart_fallback_detection(day_content)
                
        except Exception as e:
            print(f"❌ Llama detection error: {e}")
            return self._smart_fallback_detection(day_content)
    
    def _call_llama_analyzer(self, prompt: str) -> dict:
        """Enhanced Llama call with better parsing"""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert learning analyst. Always return valid JSON only. Be very accurate in detecting coding vs theory tasks."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                model="llama-3.1-8b-instant",  # Use the more powerful model
                temperature=0.1,
                max_tokens=1000
            )
            
            llama_response = response.choices[0].message.content.strip()
            print(f"🦙 Llama raw response: {llama_response}")
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{.*\}', llama_response, re.DOTALL)
            if json_match:
                analysis_data = json.loads(json_match.group(0))
                
                # Validate required fields
                required_fields = ['assessment_type', 'reasoning']
                if all(field in analysis_data for field in required_fields):
                    return analysis_data
                else:
                    print(f"❌ Missing required fields in Llama response")
                    return {"error": "Missing required fields"}
            else:
                print("❌ No JSON found in Llama response")
                return {"error": "No JSON found in response"}
                
        except Exception as e:
            print(f"❌ Llama API call error: {e}")
            return {"error": str(e)}
    
    def _smart_fallback_detection(self, day_content: dict) -> dict:
        """
        SMART fallback that properly analyzes the content
        """
        print(f"🔄 Using smart fallback detection...")
        
        # Extract all text content
        task_title = day_content.get('task', '').lower()
        description = day_content.get('description', '').lower()
        tasks_list = day_content.get('tasks', [])
        all_tasks_text = ' '.join(tasks_list).lower()
        
        # Combine all text
        all_content = f"{task_title} {description} {all_tasks_text}"
        
        print(f"🔍 Fallback analyzing: {all_content}")
        
        # Strong coding indicators
        strong_coding_phrases = [
            'practice control flow', 'practice functions', 'implement', 
            'build', 'create', 'calculator', 'program', 'code',
            'develop', 'write', 'coding', 'programming'
        ]
        
        # Theory indicators
        theory_phrases = [
            'learn about', 'understand', 'study', 'read', 
            'concept', 'theory', 'explain', 'describe'
        ]
        
        coding_matches = sum(1 for phrase in strong_coding_phrases if phrase in all_content)
        theory_matches = sum(1 for phrase in theory_phrases if phrase in all_content)
        
        print(f"📊 Fallback scores: coding={coding_matches}, theory={theory_matches}")
        
        # Decision logic
        if coding_matches > theory_matches or any(word in all_content for word in ['practice', 'implement', 'calculator']):
            assessment_type = "coding"
            reasoning = f"Found coding indicators: {[p for p in strong_coding_phrases if p in all_content]}"
        else:
            assessment_type = "theory"
            reasoning = f"Found theory indicators: {[p for p in theory_phrases if p in all_content]}"
        
        return {
            "assessment_type": assessment_type,
            "confidence": 0.7,
            "reasoning": reasoning,
            "detection_method": "smart_fallback",
            "content_focus": f"Focus on {day_content.get('task', 'learning objectives')}",
            "recommended_format": "coding_project" if assessment_type == "coding" else "multiple_choice_and_short_answer",
            "assessment_category": "coding_practice" if assessment_type == "coding" else "conceptual_understanding",
            "estimated_duration": "1-2 hours" if assessment_type == "coding" else "30 minutes"
        }
    
    def _fallback_detection(self, day_content: dict) -> dict:
        """Basic fallback - same as before"""
        return self._smart_fallback_detection(day_content)

class LlamaAssessmentEngine:
    """
    🦙 Llama-powered Assessment Generator
    Creates dynamic assessments using Llama instead of Claude Sonnet
    """
    
    def __init__(self):
        self.db = get_db()
        # Initialize Groq client for Llama
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    def generate_assessment(self, day_content: dict, assessment_type: str = "theory") -> dict:
        """
        Generate dynamic assessment using Llama
        """
        try:
            if assessment_type == "theory":
                return self._generate_theory_assessment(day_content)
            elif assessment_type == "coding":
                return self._generate_coding_assessment(day_content)
            else:
                return {"error": "Invalid assessment type"}
                
        except Exception as e:
            print(f"❌ Assessment generation error: {e}")
            return {"error": str(e)}
    
    def _generate_theory_assessment(self, day_content: dict) -> dict:
        """Generate Q&A form assessment for theory content using Llama"""
        
        task_description = day_content.get('task', '')
        learning_objectives = day_content.get('description', '')
        
        prompt = f"""
You are Leo AI, an expert assessment creator. Generate a comprehensive learning assessment for this day's content:

**Day Content:**
Task: {task_description}
Description: {learning_objectives}
Phase: {day_content.get('phase_name', '')}
Skills: {', '.join(day_content.get('phase_skills', []))}

Create a JSON assessment with this EXACT structure:
{{
    "assessment_type": "theory",
    "questions": [
        {{
            "id": 1,
            "type": "multiple_choice",
            "question": "Clear, specific question text",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": 0,
            "explanation": "Why this answer is correct",
            "difficulty": "easy|medium|hard"
        }},
        {{
            "id": 2,
            "type": "short_answer",
            "question": "Question requiring 2-3 sentence explanation",
            "expected_keywords": ["keyword1", "keyword2", "keyword3"],
            "difficulty": "medium"
        }},
        {{
            "id": 3,
            "type": "scenario",
            "question": "Real-world scenario question",
            "scenario": "Detailed scenario description",
            "expected_approach": "Step-by-step approach expected",
            "difficulty": "hard"
        }}
    ],
    "total_questions": 3,
    "passing_score": 70,
    "estimated_time": "15-20 minutes"
}}

Requirements:
- Generate 3-5 relevant questions
- Mix difficulty levels (easy/medium/hard)
- Include practical scenarios
- Focus on understanding, not memorization
- Questions should test comprehension of: {task_description}

Return ONLY the JSON, no additional text.
"""
        
        return self._call_llama(prompt)
    
    def _generate_coding_assessment(self, day_content: dict) -> dict:
        """Generate coding assessment STRICTLY based on actual day content"""
        
        task_description = day_content.get('task', '')
        learning_objectives = day_content.get('description', '')
        actual_tasks = day_content.get('tasks', [])  # The REAL tasks to focus on
        
        # 🎯 BUILD ASSESSMENT DIRECTLY FROM ACTUAL TASKS
        tasks_text = ', '.join(actual_tasks) if actual_tasks else task_description
        
        prompt = f"""
    You are Leo AI, an expert coding mentor. Create a coding assessment that EXACTLY matches the learning content provided.

    **ACTUAL LEARNING CONTENT:**
    - Main Task: {task_description}
    - Today's Specific Tasks: {actual_tasks}
    - Description: {learning_objectives}

    **CRITICAL INSTRUCTIONS:**
    - Create an assessment that DIRECTLY tests the skills mentioned in "Today's Tasks"
    - Do NOT create unrelated projects
    - Focus ONLY on the topics mentioned in the actual tasks
    - Keep the difficulty appropriate for the learning level

    **EXAMPLE:**
    If tasks are ["Practice control flow and functions", "Implement a simple calculator"]
    → Create a SIMPLE CALCULATOR project, NOT a weather system or complex API project

    Create a JSON assessment with this EXACT structure:
    {{
        "assessment_type": "coding",
        "project_title": "Simple Calculator Project",
        "project_description": "Build a calculator that demonstrates control flow and functions",
        "requirements": [
            "Create functions for basic math operations (add, subtract, multiply, divide)",
            "Use control flow (if/else) for menu and input validation", 
            "Implement a loop to keep the calculator running until user exits"
        ],
        "github_guidelines": {{
            "repository_structure": "Simple folder with main.py and optional helper files",
            "file_requirements": [
                "main.py - Main calculator program",
                "README.md - Project description and how to run"
            ],
            "commit_guidelines": "Clear commit messages for each feature",
            "readme_requirements": "Explain how to run the calculator and what operations it supports"
        }},
        "evaluation_rubric": {{
            "functionality": "40%",
            "code_quality": "30%", 
            "documentation": "30%"
        }},
        "estimated_time": "1-2 hours",
        "difficulty": "beginner",
        "specific_focus": "Practice the exact skills mentioned in today's tasks: {tasks_text}"
    }}

    **REQUIREMENTS:**
    - Project must DIRECTLY relate to: {tasks_text}
    - Keep it simple and focused
    - Test ONLY the skills mentioned in the actual day content
    - Do NOT add unrelated complexity

    Return ONLY the JSON, no additional text.
    """
        
        return self._call_llama(prompt)

    # ALSO fix the theory assessment to be more focused
    def _generate_theory_assessment(self, day_content: dict) -> dict:
        """Generate theory assessment STRICTLY based on actual day content"""
        
        task_description = day_content.get('task', '')
        learning_objectives = day_content.get('description', '')
        actual_tasks = day_content.get('tasks', [])
        
        # Focus on the actual tasks
        tasks_text = ', '.join(actual_tasks) if actual_tasks else task_description
        
        prompt = f"""
    You are Leo AI, an expert assessment creator. Create questions that DIRECTLY test understanding of the specific learning content.

    **ACTUAL LEARNING CONTENT:**
    - Main Task: {task_description}
    - Today's Specific Tasks: {actual_tasks}
    - Description: {learning_objectives}

    **CRITICAL INSTRUCTIONS:**
    - Create questions that DIRECTLY test the concepts mentioned in "Today's Tasks"
    - Focus ONLY on the topics actually covered today
    - Do NOT ask about unrelated topics

    Create a JSON assessment with this EXACT structure:
    {{
        "assessment_type": "theory",
        "questions": [
            {{
                "id": 1,
                "type": "multiple_choice",
                "question": "Question about {tasks_text}",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": 0,
                "explanation": "Why this answer is correct",
                "difficulty": "easy"
            }},
            {{
                "id": 2,
                "type": "short_answer",
                "question": "Explain how to {tasks_text}",
                "expected_keywords": ["keyword1", "keyword2"],
                "difficulty": "medium"
            }}
        ],
        "total_questions": 3,
        "passing_score": 70,
        "estimated_time": "15-20 minutes",
        "focus_areas": "{tasks_text}"
    }}

    **EXAMPLE:**
    If tasks are ["Practice control flow and functions", "Implement a simple calculator"]
    → Ask about control flow (if/else, loops) and functions (def, parameters, return)
    → Do NOT ask about APIs, databases, or other unrelated topics

    **REQUIREMENTS:**
    - Questions must DIRECTLY relate to: {tasks_text}
    - Test understanding of concepts mentioned in actual day content
    - Keep questions focused and relevant

    Return ONLY the JSON, no additional text.
    """
        
        return self._call_llama(prompt)
    
    def _call_llama(self, prompt: str) -> dict:
        """Call Llama via Groq"""
        try:
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert assessment creator. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.1-8b-instant",
                temperature=0.1,
                max_tokens=2000
            )
            
            llama_response = response.choices[0].message.content.strip()
            
            # Parse JSON from response
            try:
                # Extract JSON from response
                import re
                json_match = re.search(r'\{.*\}', llama_response, re.DOTALL)
                if json_match:
                    assessment_data = json.loads(json_match.group(0))
                    return assessment_data
                else:
                    return {"error": "No JSON found in Llama response"}
            except json.JSONDecodeError as e:
                return {"error": f"JSON parsing error: {e}"}
                
        except Exception as e:
            print(f"❌ Llama API error: {e}")
            return {"error": f"Llama API error: {e}"}

# UPDATE: EnhancedSonnetAssessmentEngine to use Llama
class EnhancedLlamaAssessmentEngine(LlamaAssessmentEngine):
    """
    Enhanced assessment engine with AI-powered type detection using Llama
    """
    
    def __init__(self):
        super().__init__()
        self.smart_detector = SmartAssessmentDetector()  # Now uses Llama
    
    def generate_assessment(self, day_content: dict, assessment_type: str = None) -> dict:
        """
        Enhanced assessment generation with smart detection using Llama
        """
        try:
            print(f"🦙 Using Smart Llama Detector for assessment generation...")
            
            # Use Llama to detect assessment type and content if not specified
            if not assessment_type:
                detection_result = self.smart_detector.detect_assessment_type_and_content(day_content)
                assessment_type = detection_result.get('assessment_type', 'theory')
                
                # Add detection results to day_content for better generation
                day_content['ai_analysis'] = detection_result
                
                print(f"✅ Smart detection complete:")
                print(f"   Detected type: {assessment_type}")
                print(f"   Category: {detection_result.get('assessment_category')}")
                print(f"   Focus: {detection_result.get('content_focus')}")
            
            # Generate assessment using detected type
            if assessment_type == "theory":
                return self._generate_theory_assessment(day_content)
            elif assessment_type == "coding":
                return self._generate_coding_assessment(day_content)
            elif assessment_type == "mixed":
                # For mixed assessments, default to theory with coding scenarios
                return self._generate_theory_assessment(day_content)
            else:
                return self._generate_theory_assessment(day_content)
                
        except Exception as e:
            print(f"❌ Enhanced assessment generation error: {e}")
            # Fallback to original method
            return super().generate_assessment(day_content, assessment_type or 'theory')

# UPDATE: Initialize engines with Llama
llama_engine = LlamaAssessmentEngine()
enhanced_llama_engine = EnhancedLlamaAssessmentEngine()

class AssessmentUnlockManager:
    """
    🔓 Manages assessment unlocking logic - FIXED VERSION
    """
    
    def __init__(self):
        self.db = get_db()
    
    def check_unlock_status(self, user_id: str, phase_id: int) -> dict:
        """Check which assessments are unlocked for the user"""
        try:
            # Get user's learning plan progress
            progress_doc = self.db.learning_progress.find_one({
                "user_id": user_id,
                "phase_id": phase_id
            })
            
            if not progress_doc:
                # Initialize progress document
                progress_doc = {
                    "user_id": user_id,
                    "phase_id": phase_id,
                    "unlocked_days": [],
                    "completed_assessments": [],
                    "unlock_trigger": "none",
                    "created_at": datetime.now()
                }
                self.db.learning_progress.insert_one(progress_doc)
            
            # Check unlock conditions
            unlock_status = self._evaluate_unlock_conditions(user_id, phase_id, progress_doc)
            
            return unlock_status
            
        except Exception as e:
            print(f"❌ Unlock status check error: {e}")
            return {"unlocked_days": [1], "current_day": 1, "unlock_trigger": "default"}

    def _evaluate_unlock_conditions(self, user_id: str, phase_id: int, progress_doc: dict) -> dict:
        """✅ SINGLE CORRECT METHOD: Evaluate unlock conditions"""
        
        unlocked_days = progress_doc.get('unlocked_days', [])
        completed_assessments = progress_doc.get('completed_assessments', [])
        
        print(f"🔍 Evaluating unlock for Phase {phase_id}: unlocked={unlocked_days}, completed={completed_assessments}")
        
        # VALIDATION: Check if unlock status makes sense
        if len(unlocked_days) > len(completed_assessments) + 1:
            print(f"⚠️ FIXING inconsistent state...")
            reset_result = self.reset_unlock_status(user_id, phase_id)
            if reset_result.get("status") == "success":
                unlocked_days = reset_result["corrected_unlocked"]
                completed_assessments = reset_result["before_completed"]
        
        # ENSURE Day 1 is always unlocked
        if not unlocked_days or 1 not in unlocked_days:
            unlocked_days = [1]
            self._update_progress(user_id, phase_id, unlocked_days, "first_unlock")
            print(f"✅ Day 1 unlocked for Phase {phase_id}")
        
        # SEQUENTIAL UNLOCKING: Only unlock next day after previous passes
        max_completed = max(completed_assessments) if completed_assessments else 0
        correct_unlocked = [1]  # Always start with Day 1
        
        # Add sequential unlocks based on completed assessments
        for completed_day in sorted(completed_assessments):
            next_day = completed_day + 1
            if next_day not in correct_unlocked and next_day <= 30:  # Reasonable limit
                correct_unlocked.append(next_day)
        
        # Update if unlock status changed
        if set(unlocked_days) != set(correct_unlocked):
            print(f"🔄 Correcting unlock: {unlocked_days} → {correct_unlocked}")
            unlocked_days = sorted(correct_unlocked)
            self._update_progress(user_id, phase_id, unlocked_days, "corrected")
        
        # Find current day
        current_day = None
        for day in sorted(unlocked_days):
            if day not in completed_assessments:
                current_day = day
                break
        current_day = current_day or (max(unlocked_days) if unlocked_days else 1)
        
        print(f"📊 Final Phase {phase_id}: unlocked={unlocked_days}, current={current_day}")
        
        return {
            "unlocked_days": unlocked_days,
            "completed_assessments": completed_assessments,
            "current_day": current_day,
            "unlock_trigger": progress_doc.get('unlock_trigger', 'sequential')
        }

    def reset_unlock_status(self, user_id: str, phase_id: int) -> dict:
        """🔄 RESET: Fix unlock status based on actual completed assessments"""
        try:
            print(f"🔄 Resetting unlock status for Phase {phase_id}")
            
            # Get user's roadmap to check ACTUAL completion status
            user = get_user_by_id(user_id)
            roadmap_data = json.loads(user.get('road_map', '{}'))
            
            actually_completed = []
            
            # Check ONLY this specific phase
            phase_data = roadmap_data.get('phases', {}).get(phase_id, {})
            weekly_schedule = phase_data.get('learning_plan', {}).get('weekly_schedule', [])
            
            for week in weekly_schedule:
                for task in week.get('daily_tasks', []):
                    day = task.get('day', 0)
                    assessment = task.get('assessment', {})
                    
                    # Only count if score >= 70% AND completed=True
                    if (assessment.get('completed') == True and 
                        assessment.get('score', 0) >= 70):
                        actually_completed.append(day)
                        print(f"✅ Phase {phase_id} Day {day}: PASSED with {assessment.get('score')}%")
            
            # Build correct unlock sequence
            corrected_unlocked = [1]  # Always unlock Day 1
            
            # Sequential unlock based on completed assessments
            for day in sorted(actually_completed):
                next_day = day + 1
                if next_day not in corrected_unlocked:
                    corrected_unlocked.append(next_day)
            
            # Update database for this specific phase
            self.db.learning_progress.update_one(
                {"user_id": user_id, "phase_id": phase_id},
                {
                    "$set": {
                        "unlocked_days": corrected_unlocked,
                        "completed_assessments": actually_completed,
                        "unlock_trigger": "reset_corrected",
                        "updated_at": datetime.now()
                    }
                },
                upsert=True
            )
            
            print(f"✅ Phase {phase_id} RESET:")
            print(f"   📊 Completed: {actually_completed}")
            print(f"   🔓 Unlocked: {corrected_unlocked}")
            
            return {
                "status": "success",
                "before_completed": actually_completed,
                "corrected_unlocked": corrected_unlocked,
                "message": f"Phase {phase_id} unlock status corrected"
            }
            
        except Exception as e:
            print(f"❌ Reset error for Phase {phase_id}: {e}")
            return {"error": str(e)}

    def trigger_automatic_unlock(self, user_id: str, phase_id: int, completed_day: int) -> dict:
        """✅ AUTOMATIC UNLOCK: Trigger next assessment unlock after successful completion"""
        try:
            print(f"🔓 Auto-unlock for Phase {phase_id}, Day {completed_day}")
            
            # Get current progress for THIS specific phase
            progress_doc = self.db.learning_progress.find_one({
                "user_id": user_id,
                "phase_id": phase_id  # ✅ CRITICAL: Phase-specific
            })
            
            if not progress_doc:
                print(f"❌ No progress document for Phase {phase_id}")
                return {"error": "No progress document found"}
            
            unlocked_days = progress_doc.get('unlocked_days', [])
            completed_assessments = progress_doc.get('completed_assessments', [])
            
            # Verify the day is actually completed and passed
            if completed_day in completed_assessments:
                next_day = completed_day + 1
                
                if next_day not in unlocked_days:
                    # ✅ UNLOCK NEXT DAY
                    unlocked_days.append(next_day)
                    
                    # Update ONLY this phase's progress
                    self.db.learning_progress.update_one(
                        {"user_id": user_id, "phase_id": phase_id},
                        {
                            "$set": {
                                "unlocked_days": unlocked_days,
                                "unlock_trigger": "auto_sequential",
                                "updated_at": datetime.now()
                            }
                        }
                    )
                    
                    print(f"✅ Phase {phase_id}: Day {next_day} unlocked after Day {completed_day}")
                    
                    return {
                        "status": "success",
                        "unlocked_day": next_day,
                        "message": f"Day {next_day} assessment unlocked!",
                        "new_unlocked_days": unlocked_days
                    }
                else:
                    return {"status": "already_unlocked", "message": f"Day {next_day} already unlocked"}
            else:
                return {"error": "Day not marked as completed"}
            
        except Exception as e:
            print(f"❌ Auto-unlock error: {e}")
            return {"error": str(e)}

    def _check_assessment_passed(self, user_id: str, phase_id: int, day: int) -> bool:
        """Check if specific day assessment was passed"""
        try:
            user = get_user_by_id(user_id)
            roadmap_data = json.loads(user.get('road_map', '{}'))
            
            # Check ONLY the specific phase
            phase_data = roadmap_data.get('phases', {}).get(phase_id, {})
            weekly_schedule = phase_data.get('learning_plan', {}).get('weekly_schedule', [])
            
            for week in weekly_schedule:
                for task in week.get('daily_tasks', []):
                    task_day = task.get('day', 0)
                    
                    if task_day == day:
                        assessment = task.get('assessment', {})
                        
                        if (assessment.get('completed') == True and 
                            assessment.get('score', 0) >= 70):
                            return True
            
            return False
            
        except Exception as e:
            print(f"❌ Check assessment passed error: {e}")
            return False

    def _check_leo_ai_interaction(self, user_id: str) -> bool:
        """Check Leo AI interaction - simplified"""
        return True  # For now, always allow

    def _check_toggle_activation(self, user_id: str, phase_id: int) -> bool:
        """Check toggle activation"""
        return False

    def _update_progress(self, user_id: str, phase_id: int, unlocked_days: list, trigger: str):
        """Update progress for specific phase"""
        try:
            self.db.learning_progress.update_one(
                {"user_id": user_id, "phase_id": phase_id},
                {
                    "$set": {
                        "unlocked_days": unlocked_days,
                        "unlock_trigger": trigger,
                        "updated_at": datetime.now()
                    }
                },
                upsert=True
            )
            print(f"✅ Phase {phase_id} progress updated: {unlocked_days}")
        except Exception as e:
            print(f"❌ Progress update error: {e}")

# Initialize engines
sonnet_engine = SonnetAssessmentEngine()
unlock_manager = AssessmentUnlockManager()

@integrated_assessment_bp.route('/api/assessment/unlock-status/<int:phase_id>')
def get_unlock_status(phase_id):
    """Get assessment unlock status for a phase"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session["user_id"]
    unlock_status = unlock_manager.check_unlock_status(user_id, phase_id)
    
    return jsonify({
        "status": "success",
        "unlock_status": unlock_status,
        "timestamp": datetime.now().isoformat()
    })

@integrated_assessment_bp.route('/api/assessment/check-existing', methods=['POST'])
def check_existing_assessment():
    """
    Check if assessment already exists and return results
    """
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        user_id = session["user_id"]
        
        phase_id = data.get('phase_id')
        week_index = data.get('week_index')
        task_index = data.get('task_index')
        
        # Get user's roadmap
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Check if assessment exists
        try:
            task = roadmap_data['phases'][phase_id]['learning_plan']['weekly_schedule'][week_index]['daily_tasks'][task_index]
            assessment_record = task.get('assessment')
            
            if assessment_record and assessment_record.get('completed'):
                score = assessment_record.get('score', 0)
                
                if score >= 70:  # Passed
                    return jsonify({
                        "status": "completed",
                        "message": "Assessment already completed and passed",
                        "assessment_record": assessment_record
                    })
                else:  # Failed - allow retake
                    return jsonify({
                        "status": "failed", 
                        "message": "Assessment failed - retake allowed",
                        "assessment_record": assessment_record
                    })
            else:
                return jsonify({
                    "status": "not_taken",
                    "message": "Assessment not yet taken"
                })
                
        except (KeyError, IndexError):
            return jsonify({
                "status": "not_found",
                "message": "Assessment not found"
            })
        
    except Exception as e:
        print(f"❌ Check existing assessment error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@integrated_assessment_bp.route('/assessment/take/<int:phase_id>/<int:day>')
def take_assessment(phase_id, day):
    """
    FIXED: Extract the REAL task content, not the tracking wrapper
    """
    if "user_id" not in session:
        return redirect(url_for("auth_bp.sign_in"))
    
    user_id = session["user_id"]
    
    # Check if assessment is unlocked
    unlock_status = unlock_manager.check_unlock_status(user_id, phase_id)
    
    if day not in unlock_status["unlocked_days"]:
        flash("This assessment is not yet unlocked.", "warning")
        return redirect(url_for("roadmap_bp.roadmap"))
    
    # Get user and roadmap data
    user = get_user_by_id(user_id)
    roadmap_data = json.loads(user.get('road_map', '{}'))
    
    try:
        phase = roadmap_data['phases'][phase_id]
        learning_plan = phase.get('learning_plan', {})
        
        # Find the task and extract REAL content
        target_task = None
        week_index = None
        task_index = None
        real_content = None
        
        for w_idx, week in enumerate(learning_plan.get('weekly_schedule', [])):
            for t_idx, task in enumerate(week.get('daily_tasks', [])):
                task_day = task.get('day', t_idx + 1)
                
                if task_day == day:
                    target_task = task
                    week_index = w_idx
                    task_index = t_idx
                    
                    # 🔍 EXTRACT REAL CONTENT from the task
                    print(f"🔍 Raw task data: {task}")
                    print(f"🔍 Task keys: {list(task.keys())}")
                    
                    # Look for the actual learning content
                    real_task_title = None
                    real_description = None
                    real_tasks = []
                    real_resources = []
                    
                    # Try different field names for task title
                    for field in ['task', 'title', 'name', 'activity', 'learning_objective']:
                        if field in task and task[field] and task[field] not in ['Learning Task', '']:
                            real_task_title = task[field]
                            break
                    
                    # Try different field names for description
                    for field in ['description', 'content', 'summary', 'objective']:
                        if field in task and task[field] and task[field] not in ['Daily learning activity', '']:
                            real_description = task[field]
                            break
                    
                    # Extract tasks list
                    if 'tasks' in task and isinstance(task['tasks'], list):
                        real_tasks = [t for t in task['tasks'] if t and t.strip()]
                    
                    # Extract resources list  
                    if 'resources' in task and isinstance(task['resources'], list):
                        real_resources = [r for r in task['resources'] if r and r.strip()]
                    
                    # Build enriched content for assessment
                    real_content = {
                        'task': real_task_title or f"Day {day} Learning Session",
                        'description': real_description or "Complete today's learning objectives",
                        'day': day,
                        'tasks': real_tasks,
                        'resources': real_resources,
                        'phase_name': phase.get('name', 'Learning Phase'),
                        'phase_skills': phase.get('skills', []),
                        'week_context': {
                            'week_number': week.get('week', w_idx + 1),
                            'week_title': week.get('title', ''),
                            'learning_objectives': week.get('learning_objectives', [])
                        },
                        # Include completion tracking
                        'completed': task.get('completed', False),
                        'task_id': task.get('task_id', f'task_{day}')
                    }
                    
                    print(f"✅ REAL content extracted:")
                    print(f"   📌 Title: {real_content['task']}")
                    print(f"   📌 Description: {real_content['description']}")
                    print(f"   📌 Tasks: {real_content['tasks']}")
                    print(f"   📌 Resources: {real_content['resources']}")
                    print(f"   📌 Phase skills: {real_content['phase_skills']}")
                    
                    break
            
            if real_content:
                break
        
        if not real_content:
            flash(f"Learning content for day {day} not found.", "error")
            return redirect(url_for("roadmap_bp.roadmap"))
        user = '9KDztbl5QFedLtfzuc4doQ'
        
        return render_template('integrated_assessment.html',
                                phase=phase,
                                phase_id=phase_id,
                                day=day,
                                day_content=real_content,
                                week_index=week_index,
                                task_index=task_index,
                                user=user)
    
        
    except Exception as e:
        print(f"❌ Assessment error: {e}")
        import traceback
        traceback.print_exc()
        flash("Assessment not found.", "error")
        return redirect(url_for("roadmap_bp.roadmap"))
    
# ADD this new route for storing assessments in nested structure:

@integrated_assessment_bp.route('/api/assessment/store', methods=['POST'])
def store_assessment():
    """
    Store assessment in NESTED structure like learning plans
    Structure: user -> phase -> week -> day -> assessment
    """
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        user_id = session["user_id"]
        phase_id = data.get('phase_id')
        week_index = data.get('week_index')
        task_index = data.get('task_index')
        day = data.get('day')
        assessment_data = data.get('assessment_data')
        assessment_result = data.get('assessment_result')
        
        # Get user's current roadmap
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Navigate to the EXACT same location as the task
        target_phase = roadmap_data['phases'][phase_id]
        target_week = target_phase['learning_plan']['weekly_schedule'][week_index]
        target_task = target_week['daily_tasks'][task_index]
        
        # Store assessment IN THE SAME NESTED STRUCTURE
        if 'assessment' not in target_task:
            target_task['assessment'] = {}
        
        # Store the assessment data
        target_task['assessment'] = {
            'assessment_data': assessment_data,      # Generated questions/project
            'assessment_result': assessment_result,  # User's answers/submission
            'completed': True,
            'completed_at': datetime.now().isoformat(),
            'score': assessment_result.get('score', 0),
            'status': 'completed',
            'attempts': target_task['assessment'].get('attempts', 0) + 1
        }
        
        # Mark task as assessed
        target_task['assessed'] = True
        target_task['assessment_completed'] = True
        
        # Update the roadmap back in database
        from app.utils.db_utils import get_db
        db = get_db()
        
        result = db.users.update_one(
            {"user_id": user_id},
            {"$set": {"road_map": json.dumps(roadmap_data)}}
        )
        
        # Also update learning progress for unlock logic
        db.learning_progress.update_one(
            {"user_id": user_id, "phase_id": phase_id},
            {
                "$addToSet": {"completed_assessments": day},
                "$set": {"updated_at": datetime.now()}
            },
            upsert=True
        )
        
        print(f"✅ Assessment stored in nested structure: Phase {phase_id} -> Week {week_index} -> Task {task_index}")
        
        return jsonify({
            "status": "success",
            "message": "Assessment stored successfully",
            "storage_path": f"phases[{phase_id}].learning_plan.weekly_schedule[{week_index}].daily_tasks[{task_index}].assessment"
        })
        
    except Exception as e:
        print(f"❌ Assessment storage error: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

@integrated_assessment_bp.route('/api/assessment/generate', methods=['POST'])
def generate_assessment():
    """
    ✅ LLAMA-POWERED: Generate assessment using Llama (no throttling!)
    """
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        user_id = session["user_id"]
        day_content = data.get('day_content', {})
        phase_id = data.get('phase_id')
        week_index = data.get('week_index')
        task_index = data.get('task_index')
        use_smart_detection = data.get('use_smart_detection', True)
        
        print(f"🦙 LLAMA assessment generation:")
        print(f"   📍 Location: Phase {phase_id} -> Week {week_index} -> Task {task_index}")
        print(f"   📝 Day content: {day_content.get('task', 'Unknown')}")
        print(f"   🤖 Smart detection: {use_smart_detection}")
        
        # Check if assessment already exists for this exact task
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        try:
            existing_assessment = roadmap_data['phases'][phase_id]['learning_plan']['weekly_schedule'][week_index]['daily_tasks'][task_index].get('assessment')
            
            if existing_assessment and existing_assessment.get('assessment_data'):
                print(f"✅ Using existing assessment for task {task_index}")
                return jsonify({
                    "status": "success",
                    "assessment": existing_assessment['assessment_data'],
                    "from_cache": True,
                    "timestamp": existing_assessment.get('completed_at')
                })
        except (KeyError, IndexError):
            pass  # No existing assessment, continue with generation
        
        # Generate assessment using Llama (no throttling!)
        if use_smart_detection:
            print(f"🦙 Using Enhanced Llama Engine with AI detection...")
            assessment = enhanced_llama_engine.generate_assessment(day_content)
        else:
            # Fallback to basic Llama generation
            print(f"🦙 Using Basic Llama Engine...")
            assessment_type = data.get('assessment_type', 'theory')
            assessment = llama_engine.generate_assessment(day_content, assessment_type)
        
        if "error" not in assessment:
            print(f"✅ Llama assessment generated successfully")
            
            return jsonify({
                "status": "success",
                "assessment": assessment,
                "from_cache": False,
                "generator": "llama",
                "timestamp": datetime.now().isoformat()
            })
        else:
            print(f"❌ Llama assessment generation error: {assessment['error']}")
            return jsonify({
                "status": "error",
                "error": assessment["error"]
            }), 500
            
    except Exception as e:
        print(f"❌ Assessment generation exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

@integrated_assessment_bp.route('/api/assessment/submit', methods=['POST'])
def submit_assessment():
    """✅ ENHANCED: Submit assessment with automatic unlock toggle"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    try:
        data = request.get_json()
        user_id = session["user_id"]
        
        phase_id = data.get('phase_id')
        day = data.get('day')
        week_index = data.get('week_index')
        task_index = data.get('task_index')
        assessment_type = data.get('assessment_type')
        assessment_answers = data.get('assessment_answers')
        day_content = data.get('day_content')
        
        print(f"📤 Enhanced assessment submission:")
        print(f"   📍 Phase {phase_id}, Day {day}")
        print(f"   📝 Type: {assessment_type}")
        
        # Validate required fields
        if not all([phase_id is not None, assessment_answers, assessment_type]):
            return jsonify({
                "status": "error", 
                "error": "Missing required fields"
            }), 400
        
        # Evaluate assessment
        if assessment_type == 'theory':
            evaluation_result = strict_theory_evaluation(assessment_answers, day_content)
        elif assessment_type == 'coding':
            evaluation_result = strict_coding_evaluation(assessment_answers, day_content)
        else:
            evaluation_result = strict_theory_evaluation(assessment_answers, day_content)
        
        final_score = evaluation_result.get('score', 0)
        passed = final_score >= 70
        
        print(f"📊 Evaluation result: {final_score}% - {'PASSED' if passed else 'FAILED'}")
        
        # Get user's roadmap for storage
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        # Create assessment record
        assessment_record = {
            'user_answers': assessment_answers,
            'evaluation': evaluation_result,
            'submitted_at': datetime.now().isoformat(),
            'completed': passed,  # ✅ CRITICAL: Only mark as completed if PASSED
            'score': final_score,
            'status': 'passed' if passed else 'failed',
            'attempts': 1
        }
        
        # Store in nested structure
        try:
            # Check for previous attempts
            existing_assessment = roadmap_data['phases'][phase_id]['learning_plan']['weekly_schedule'][week_index]['daily_tasks'][task_index].get('assessment')
            if existing_assessment:
                assessment_record['attempts'] = existing_assessment.get('attempts', 0) + 1
            
            # Store the assessment record
            roadmap_data['phases'][phase_id]['learning_plan']['weekly_schedule'][week_index]['daily_tasks'][task_index]['assessment'] = assessment_record
            
            # Update database
            from app.utils.db_utils import get_db
            db = get_db()
            db.users.update_one(
                {"user_id": user_id},
                {"$set": {"road_map": json.dumps(roadmap_data)}}
            )
            
            unlock_result = None
            
            # ✅ CRITICAL: Update progress ONLY if assessment was PASSED
            if passed:
                # Update completed assessments
                db.learning_progress.update_one(
                    {"user_id": user_id, "phase_id": phase_id},
                    {
                        "$addToSet": {"completed_assessments": day},
                        "$set": {"updated_at": datetime.now()}
                    },
                    upsert=True
                )
                print(f"✅ Assessment PASSED - added Day {day} to completed_assessments")
                
                # 🚀 AUTOMATIC UNLOCK: Trigger next assessment unlock
                unlock_result = unlock_manager.trigger_automatic_unlock(user_id, phase_id, day)
                print(f"🔓 Automatic unlock result: {unlock_result}")
                
            else:
                print(f"❌ Assessment FAILED - no progress update, no unlock")
        
        except Exception as storage_error:
            print(f"❌ Storage error: {storage_error}")
            return jsonify({
                "status": "error",
                "error": f"Failed to store assessment: {storage_error}"
            }), 500
        
        # Prepare response
        response_data = {
            "status": "success",
            "message": "Assessment evaluated and stored",
            "evaluation": evaluation_result,
            "passed": passed,
            "attempts": assessment_record['attempts'],
            "score": final_score
        }
        
        # ✅ ADD UNLOCK INFORMATION TO RESPONSE
        if passed and unlock_result:
            response_data["unlock_result"] = unlock_result
            if unlock_result.get("status") == "success":
                response_data["next_day_unlocked"] = unlock_result.get("unlocked_day")
                response_data["unlock_message"] = unlock_result.get("message")
            else:
                response_data["unlock_message"] = "Assessment passed but next unlock failed"
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"❌ Assessment submission error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "error": str(e)}), 500

def strict_theory_evaluation(user_answers: dict, day_content: dict) -> dict:
    """
    STRICT evaluation of theory assessment
    """
    try:
        total_questions = len(user_answers)
        answered_questions = 0
        score = 0
        
        # Check each answer
        for key, answer in user_answers.items():
            if answer and str(answer).strip():
                answered_questions += 1
                
                # Simple scoring: each answered question gets points
                answer_text = str(answer).strip().lower()
                
                # Give more points for longer, thoughtful answers
                if len(answer_text) > 10:
                    score += 25  # Good answer
                elif len(answer_text) > 3:
                    score += 15  # Basic answer
                else:
                    score += 5   # Minimal answer
        
        # Penalty for unanswered questions
        unanswered = total_questions - answered_questions
        score -= (unanswered * 20)  # -20 points per unanswered question
        
        # Ensure score is between 0-100
        final_score = max(0, min(100, score))
        
        # Determine feedback based on score
        if final_score >= 70:
            feedback = "🎉 Excellent work! You've demonstrated good understanding of the concepts. You have successfully completed this assessment."
            status = "PASSED"
        else:
            feedback = f"📚 You scored {final_score}%, but need 70% to pass. Please review the learning materials and try again. Focus on providing more detailed answers."
            status = "FAILED - RETAKE REQUIRED"
        
        return {
            "score": final_score,
            "feedback": feedback,
            "status": status,
            "answered_questions": answered_questions,
            "total_questions": total_questions,
            "next_steps": "Continue to next module" if final_score >= 70 else "Review materials and retake assessment"
        }
        
    except Exception as e:
        print(f"❌ Theory evaluation error: {e}")
        return {
            "score": 0,
            "feedback": "Evaluation error occurred. Please try again.",
            "status": "ERROR"
        }

def strict_coding_evaluation(user_answers: dict, day_content: dict) -> dict:
    """
    STRICT evaluation of coding assessment
    """
    try:
        github_url = user_answers.get('github_url', '')
        description = user_answers.get('description', '')
        
        score = 0
        feedback_points = []
        
        # Check GitHub URL (30 points)
        if github_url and 'github.com' in github_url:
            score += 30
            feedback_points.append("✅ Valid GitHub URL provided")
        else:
            feedback_points.append("❌ Invalid or missing GitHub URL")
        
        # Check description quality (40 points)
        if description and len(description.strip()) > 50:
            score += 40
            feedback_points.append("✅ Detailed project description provided")
        elif description and len(description.strip()) > 20:
            score += 20
            feedback_points.append("⚠️ Basic description provided, could be more detailed")
        else:
            feedback_points.append("❌ Missing or insufficient project description")
        
        # Bonus points for good practices (30 points)
        if description and any(keyword in description.lower() for keyword in ['readme', 'documentation', 'comments']):
            score += 15
            feedback_points.append("✅ Good documentation practices mentioned")
        
        if description and any(keyword in description.lower() for keyword in ['test', 'error', 'validation']):
            score += 15
            feedback_points.append("✅ Testing or error handling mentioned")
        
        # Determine status
        if score >= 70:
            status = "PASSED"
            feedback = f"🎉 Great coding project! {' '.join(feedback_points)}"
        else:
            status = "FAILED - RETAKE REQUIRED"
            feedback = f"📚 Score: {score}%. Need 70% to pass. {' '.join(feedback_points)} Please improve and resubmit."
        
        return {
            "score": score,
            "feedback": feedback,
            "status": status,
            "next_steps": "Continue coding journey" if score >= 70 else "Improve project and resubmit"
        }
        
    except Exception as e:
        print(f"❌ Coding evaluation error: {e}")
        return {
            "score": 0,
            "feedback": "Evaluation error occurred. Please try again.",
            "status": "ERROR"
        }

@integrated_assessment_bp.route('/api/assessment/reset-all-phases')
def reset_all_phases():
    """Reset unlock status for ALL phases"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session["user_id"]
    
    try:
        # Get user's roadmap to find all phases
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        results = {}
        
        # Reset each phase
        for phase_id in roadmap_data.get('phases', {}):
            result = unlock_manager.reset_unlock_status(user_id, phase_id)
            results[f"phase_{phase_id}"] = result
        
        return jsonify({
            "status": "success",
            "message": "All phases reset",
            "results": results
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

def reset_unlock_status(self, user_id: str, phase_id: int) -> dict:
    """🔄 FIXED: Handle continuous day numbering correctly"""
    try:
        print(f"🔄 Resetting unlock status for Phase {phase_id}")
        
        # Get user's roadmap to check ACTUAL completion status
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        actually_completed = []
        
        # Check ONLY this specific phase
        phase_data = roadmap_data.get('phases', {}).get(phase_id, {})
        weekly_schedule = phase_data.get('learning_plan', {}).get('weekly_schedule', [])
        
        print(f"📊 Phase {phase_id} has {len(weekly_schedule)} weeks")
        
        for week_idx, week in enumerate(weekly_schedule):
            print(f"   📅 Week {week_idx + 1}: {len(week.get('daily_tasks', []))} tasks")
            
            for task_idx, task in enumerate(week.get('daily_tasks', [])):
                day = task.get('day', 0)
                assessment = task.get('assessment', {})
                
                # Debug task info
                print(f"      🎯 Task Day {day}: completed={assessment.get('completed')}, score={assessment.get('score', 0)}")
                
                # Only count if score >= 70% AND completed=True
                if (assessment.get('completed') == True and 
                    assessment.get('score', 0) >= 70):
                    actually_completed.append(day)
                    print(f"✅ Phase {phase_id} Day {day}: PASSED with {assessment.get('score')}%")
        
        # Build correct unlock sequence (continuous numbering)
        corrected_unlocked = [1]  # Always unlock Day 1
        
        # Sequential unlock based on completed assessments
        for day in sorted(actually_completed):
            next_day = day + 1
            if next_day not in corrected_unlocked and next_day <= 50:  # Reasonable limit
                corrected_unlocked.append(next_day)
        
        # Update database for this specific phase
        self.db.learning_progress.update_one(
            {"user_id": user_id, "phase_id": phase_id},
            {
                "$set": {
                    "unlocked_days": corrected_unlocked,
                    "completed_assessments": actually_completed,
                    "unlock_trigger": "reset_corrected",
                    "updated_at": datetime.now()
                }
            },
            upsert=True
        )
        
        print(f"✅ Phase {phase_id} RESET:")
        print(f"   📊 Actually completed days: {actually_completed}")
        print(f"   🔓 Should be unlocked: {corrected_unlocked}")
        
        return {
            "status": "success",
            "before_completed": actually_completed,
            "corrected_unlocked": corrected_unlocked,
            "message": f"Phase {phase_id} unlock status corrected",
            "debug_info": {
                "total_weeks": len(weekly_schedule),
                "total_tasks": sum(len(week.get('daily_tasks', [])) for week in weekly_schedule)
            }
        }
        
    except Exception as e:
        print(f"❌ Reset error for Phase {phase_id}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# SOLUTION 2: Add debug route to check roadmap structure

@integrated_assessment_bp.route('/api/assessment/debug-roadmap/<int:phase_id>')
def debug_roadmap_structure(phase_id):
    """Debug route to check roadmap structure"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session["user_id"]
    
    try:
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        phase_data = roadmap_data.get('phases', {}).get(phase_id, {})
        weekly_schedule = phase_data.get('learning_plan', {}).get('weekly_schedule', [])
        
        structure_info = {
            "phase_id": phase_id,
            "phase_name": phase_data.get('name', 'Unknown'),
            "total_weeks": len(weekly_schedule),
            "weeks_detail": []
        }
        
        for week_idx, week in enumerate(weekly_schedule):
            week_info = {
                "week_number": week.get('week', week_idx + 1),
                "week_title": week.get('title', f'Week {week_idx + 1}'),
                "total_tasks": len(week.get('daily_tasks', [])),
                "tasks_detail": []
            }
            
            for task_idx, task in enumerate(week.get('daily_tasks', [])):
                task_info = {
                    "task_index": task_idx,
                    "day": task.get('day', 'NO_DAY'),
                    "task_title": task.get('task', task.get('title', 'NO_TITLE'))[:50],
                    "completed": task.get('completed', False),
                    "has_assessment": 'assessment' in task,
                    "assessment_completed": task.get('assessment', {}).get('completed', False),
                    "assessment_score": task.get('assessment', {}).get('score', 0)
                }
                week_info["tasks_detail"].append(task_info)
            
            structure_info["weeks_detail"].append(week_info)
        
        return jsonify({
            "status": "success",
            "roadmap_structure": structure_info
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

# SOLUTION 3: Add route to fix day numbering if needed

@integrated_assessment_bp.route('/api/assessment/fix-day-numbering/<int:phase_id>')
def fix_day_numbering(phase_id):
    """Fix day numbering to be week-specific instead of continuous"""
    if "user_id" not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session["user_id"]
    
    try:
        user = get_user_by_id(user_id)
        roadmap_data = json.loads(user.get('road_map', '{}'))
        
        phase_data = roadmap_data.get('phases', {}).get(phase_id, {})
        weekly_schedule = phase_data.get('learning_plan', {}).get('weekly_schedule', [])
        
        changes_made = []
        
        for week_idx, week in enumerate(weekly_schedule):
            for task_idx, task in enumerate(week.get('daily_tasks', [])):
                old_day = task.get('day', 0)
                new_day = task_idx + 1  # Day 1-7 for each week
                
                if old_day != new_day:
                    task['day'] = new_day
                    task['original_day'] = old_day  # Keep track of original
                    changes_made.append({
                        "week": week_idx + 1,
                        "task": task_idx,
                        "old_day": old_day,
                        "new_day": new_day
                    })
        
        if changes_made:
            # Update database
            from app.utils.db_utils import get_db
            db = get_db()
            db.users.update_one(
                {"user_id": user_id},
                {"$set": {"road_map": json.dumps(roadmap_data)}}
            )
            
            return jsonify({
                "status": "success",
                "message": f"Fixed day numbering for {len(changes_made)} tasks",
                "changes": changes_made
            })
        else:
            return jsonify({
                "status": "no_changes",
                "message": "Day numbering is already correct"
            })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500