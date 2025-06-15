# REPLACE your entire linkedin_integration.py file with this clean version:

import requests
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional

class LinkedInAchievementPublisher:
    """
    Complete LinkedIn Achievement Publisher using Unipile API
    """
    
    def __init__(self):
        self.unipile_api_key = os.getenv('UNIPILE_API_KEY')
        # HARDCODE API key for demo
        if not self.unipile_api_key:
            self.unipile_api_key = "yun9nI3q.PoV0m+sVz/s4xyoftdLGKjgC3prm902wIbv0F1gFlG8="
        
        # Use the working API endpoint
        self.unipile_base_url = "https://api11.unipile.com:14160"
        
        print(f"🔧 LinkedIn Publisher initialized")
        print(f"🌐 API Endpoint: {self.unipile_base_url}")
        print(f"🔑 API Key present: {bool(self.unipile_api_key)}")
    
    def create_achievement_post_content(self, achievement_data: Dict[str, Any]) -> str:
        """
        Generate engaging LinkedIn post content based on achievement type
        """
        achievement_type = achievement_data.get('type', 'task_completion')
        user_name = achievement_data.get('user_name', 'Student')
        
        if achievement_type == 'assessment_passed':
            score = achievement_data.get('score', 0)
            phase_name = achievement_data.get('phase_name', 'Learning Phase')
            day = achievement_data.get('day', 1)
            
            post_content = f"""🏆 Assessment Completed Successfully! 

Proud to share that I just passed my Day {day} assessment in {phase_name} with a score of {score}%! 

✅ Key takeaways:
• Consistent practice leads to measurable progress
• Each challenge is an opportunity to grow
• Building expertise one step at a time

Excited to continue this learning journey and apply these new skills! 

#Achievement #LearningJourney #Assessment #ProfessionalGrowth #SkillDevelopment #Success"""

        elif achievement_type == 'task_completion':
            phase_name = achievement_data.get('phase_name', 'Learning Phase')
            day = achievement_data.get('day', 1)
            skills = achievement_data.get('skills', [])
            
            post_content = f"""🎯 Learning Milestone Achieved! 

Just completed Day {day} of my {phase_name} learning journey! 

💡 Key skills I'm developing:
{chr(10).join(f'• {skill}' for skill in skills[:4])}

The journey of continuous learning never stops, and every day brings new opportunities to grow! 

#Learning #ProfessionalDevelopment #SkillBuilding #Growth #TechEducation #CareerDevelopment"""

        else:
            # Generic achievement post
            post_content = f"""🎯 Learning Progress Update! 

Another milestone reached in my continuous learning journey! Every day brings new opportunities to grow and develop professionally.

#LearningJourney #ProfessionalDevelopment #Growth #CareerGoals"""
        
        return post_content
    
    def create_achievement_image(self, achievement_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate achievement image (placeholder for now)
        """
        print("📸 Image generation placeholder - integrate with your preferred service")
        return None
    
    def publish_to_linkedin(self, post_content: str, linkedin_account_id: str, image_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Publish post to LinkedIn using Unipile API - WORKING VERSION
        """
        # Use the correct API endpoint and format
        headers = {
            'X-API-KEY': self.unipile_api_key,
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Use the exact format from working example
        post_data = {
            "account_id": linkedin_account_id,
            "text": post_content
        }
        
        # Use the working API URL
        api_url = f'{self.unipile_base_url}/api/v1/posts'
        
        print(f"📤 Using working API endpoint: {api_url}")
        print(f"🔑 Account ID: {linkedin_account_id}")
        print(f"📝 Post length: {len(post_content)} chars")
        
        try:
            # Use shorter timeout like working example
            response = requests.post(
                api_url,
                headers=headers,
                json=post_data,
                timeout=15
            )
            
            print(f"📡 API Response: {response.status_code}")
            print(f"📋 Response text: {response.text[:200]}...")
            
            # Check for both 200 and 201 like working example
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    print(f"✅ LinkedIn post published successfully: {result}")
                    return {
                        'success': True,
                        'message': 'Achievement shared on LinkedIn successfully!',
                        'post_id': result.get('id', 'success'),
                        'unipile_response': result
                    }
                except:
                    print(f"✅ LinkedIn post published (no JSON response)")
                    return {
                        'success': True,
                        'message': 'Achievement shared on LinkedIn successfully!',
                        'post_id': 'success',
                        'unipile_response': {'status': 'success'}
                    }
            
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Invalid Unipile API key. Please check your API key.'
                }
            
            elif response.status_code == 404:
                return {
                    'success': False,
                    'message': f'LinkedIn account {linkedin_account_id} not found. Please check your Account ID.'
                }
            
            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'LinkedIn account access denied. Please reconnect your account in Unipile dashboard.'
                }
            
            else:
                error_msg = f"API Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f": {error_data.get('message', response.text[:200])}"
                except:
                    error_msg += f": {response.text[:200]}"
                
                print(f"❌ LinkedIn post failed: {error_msg}")
                return {
                    'success': False,
                    'message': error_msg
                }
        
        except requests.exceptions.Timeout:
            print("⏰ Request timeout")
            return {
                'success': False,
                'message': 'Request timeout. Please try again or check your internet connection.'
            }
        
        except requests.exceptions.ConnectionError:
            print("🌐 Connection error")
            return {
                'success': False,
                'message': 'Connection error. Please check your internet connection.'
            }
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error: {e}")
            return {
                'success': False,
                'message': f'Network error: {str(e)}'
            }
        
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return {
                'success': False,
                'message': f'Unexpected error: {str(e)}'
            }
    
    def create_and_publish_achievement_with_content(self, post_content: str, user_linkedin_account_id: str, include_image: bool = False) -> Dict[str, Any]:
        """
        Publish pre-generated content to LinkedIn
        """
        try:
            print(f"🚀 Publishing custom content to LinkedIn")
            print(f"✅ Content ready: {len(post_content)} characters")
            
            # Generate image (optional)
            image_url = None
            if include_image:
                image_url = self.create_achievement_image({})
                if image_url:
                    print(f"✅ Achievement image generated: {image_url}")
                else:
                    print("ℹ️ No image generated - posting text only")
            
            # Publish to LinkedIn
            result = self.publish_to_linkedin(post_content, user_linkedin_account_id, image_url)
            
            # Add additional info to result
            result['post_content'] = post_content
            result['image_generated'] = bool(image_url)
            result['achievement_type'] = 'custom_content'
            
            return result
            
        except Exception as e:
            print(f"❌ Custom content publishing error: {e}")
            return {
                'success': False,
                'message': f'Failed to publish content: {str(e)}',
                'post_content': post_content,
                'image_generated': False
            }
    
    def create_and_publish_achievement(self, achievement_data: Dict[str, Any], user_linkedin_account_id: str, include_image: bool = False) -> Dict[str, Any]:
        """
        Complete workflow: Create content, generate image (optional), and publish to LinkedIn
        """
        try:
            print(f"🚀 Creating LinkedIn achievement post for: {achievement_data.get('type', 'unknown')}")
            
            # Create post content
            post_content = self.create_achievement_post_content(achievement_data)
            print(f"✅ Post content created: {len(post_content)} characters")
            
            # Generate image (optional)
            image_url = None
            if include_image:
                image_url = self.create_achievement_image(achievement_data)
                if image_url:
                    print(f"✅ Achievement image generated: {image_url}")
                else:
                    print("ℹ️ No image generated - posting text only")
            
            # Publish to LinkedIn
            result = self.publish_to_linkedin(post_content, user_linkedin_account_id, image_url)
            
            # Add additional info to result
            result['post_content'] = post_content
            result['image_generated'] = bool(image_url)
            result['achievement_type'] = achievement_data.get('type', 'unknown')
            result['user_name'] = achievement_data.get('user_name', 'Student')
            
            return result
            
        except Exception as e:
            print(f"❌ Achievement creation and publishing error: {e}")
            return {
                'success': False,
                'message': f'Failed to create/publish achievement: {str(e)}',
                'post_content': '',
                'image_generated': False
            }

# Convenience functions for specific achievement types
def publish_task_completion_achievement(user_linkedin_account_id: str, phase_name: str, day: int, skills: list, user_name: str = "Student") -> Dict[str, Any]:
    """
    Quick function to publish task completion achievement
    """
    publisher = LinkedInAchievementPublisher()
    
    achievement_data = {
        'type': 'task_completion',
        'phase_name': phase_name,
        'day': day,
        'skills': skills,
        'user_name': user_name
    }
    
    return publisher.create_and_publish_achievement(
        achievement_data=achievement_data,
        user_linkedin_account_id=user_linkedin_account_id,
        include_image=False
    )

def publish_assessment_achievement(user_linkedin_account_id: str, score: int, phase_name: str, day: int, user_name: str = "Student") -> Dict[str, Any]:
    """
    Quick function to publish assessment completion achievement
    """
    publisher = LinkedInAchievementPublisher()
    
    achievement_data = {
        'type': 'assessment_passed',
        'score': score,
        'phase_name': phase_name,
        'day': day,
        'user_name': user_name
    }
    
    return publisher.create_and_publish_achievement(
        achievement_data=achievement_data,
        user_linkedin_account_id=user_linkedin_account_id,
        include_image=False
    )

def publish_phase_completion_achievement(user_linkedin_account_id: str, phase_name: str, total_progress: int, skills: list, user_name: str = "Student") -> Dict[str, Any]:
    """
    Quick function to publish phase completion achievement
    """
    publisher = LinkedInAchievementPublisher()
    
    achievement_data = {
        'type': 'phase_completed',
        'phase_name': phase_name,
        'total_progress': total_progress,
        'skills': skills,
        'user_name': user_name
    }
    
    return publisher.create_and_publish_achievement(
        achievement_data=achievement_data,
        user_linkedin_account_id=user_linkedin_account_id,
        include_image=False
    )

# Test function (optional - for manual testing)
def test_linkedin_integration():
    """Test the LinkedIn integration with dummy data"""
    print("🧪 Testing LinkedIn Integration...")
    
    publisher = LinkedInAchievementPublisher()
    
    test_data = {
        'type': 'test_connection',
        'user_name': 'Test User',
        'phase_name': 'Integration Testing',
        'day': 1,
        'skills': ['API Integration', 'LinkedIn Automation', 'Social Media'],
        'total_progress': 100
    }
    
    result = publisher.create_and_publish_achievement(
        achievement_data=test_data,
        user_linkedin_account_id="9KDztbl5QFedLtfzuc4doQ",
        include_image=False
    )
    
    print(f"Test result: {result}")
    return result