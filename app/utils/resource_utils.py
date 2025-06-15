import os
import requests
from urllib.parse import quote
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def fetch_youtube_videos(query, max_results=5):
    """
    Fetch relevant videos from YouTube API
    
    Args:
        query (str): The search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of video data
    """
    try:
        # Initialize the YouTube API client
        youtube = build(
            'youtube', 
            'v3', 
            developerKey=os.getenv('YOUTUBE_API_KEY')
        )
        
        # Execute the search
        search_response = youtube.search().list(
            q=query,
            part='snippet',
            maxResults=max_results,
            type='video',
            relevanceLanguage='en',
            safeSearch='moderate'
        ).execute()
        
        # Process the results
        videos = []
        for item in search_response.get('items', []):
            video_id = item['id']['videoId']
            videos.append({
                'id': video_id,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'thumbnail': item['snippet']['thumbnails']['medium']['url'],
                'publishedAt': item['snippet']['publishedAt'],
                'channelTitle': item['snippet']['channelTitle'],
                'url': f"https://www.youtube.com/watch?v={video_id}"
            })
        
        return videos
    
    except HttpError as e:
        print(f"YouTube API error: {e}")
        return []
    except Exception as e:
        print(f"Error fetching YouTube videos: {e}")
        return []

def fetch_google_scholar_papers(query, max_results=5):
    """
    Fetch academic papers from Google Scholar via RapidAPI with better error handling
    """
    try:
        # RapidAPI endpoint for Google Scholar
        url = "https://google-scholar1.p.rapidapi.com/search_pubs"
        
        # Clean the query - remove special characters that might cause issues
        clean_query = query.replace(':', '').replace('-', ' ').strip()
        
        # Set up the request parameters
        querystring = {
            "query": clean_query,
            "max_results": str(min(max_results, 10)),  # Limit to max 10
            "patents": "false",  # Changed from "true" to "false"
            "citations": "true",
            "sort_by": "relevance",
            "start_index": "0"
        }
        
        headers = {
            "x-rapidapi-key": os.getenv('GOOGLE_SCHOLOR_API_KEY'),
            "x-rapidapi-host": "google-scholar1.p.rapidapi.com"
        }
        
        print(f"🔍 Fetching papers with query: {clean_query}")
        
        # Make the API request with timeout
        response = requests.get(url, headers=headers, params=querystring, timeout=10)
        
        print(f"📊 Scholar API Response: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Google Scholar API error: {response.status_code} - {response.text}")
            return []  # Return empty list instead of failing
        
        # Process the results
        data = response.json()
        papers = []
        
        # Handle the actual response format returned by the API
        if 'result' in data and isinstance(data['result'], list):
            for item in data['result'][:max_results]:
                # Extract author names from the bib.author list
                authors = []
                if 'bib' in item and 'author' in item['bib'] and isinstance(item['bib']['author'], list):
                    authors = item['bib']['author']
                
                # Create paper object with available fields
                paper = {
                    'title': item.get('bib', {}).get('title', 'Untitled'),
                    'authors': authors,
                    'abstract': item.get('bib', {}).get('abstract', 'No abstract available'),
                    'year': item.get('bib', {}).get('pub_year', 'Unknown year'),
                    'citations': item.get('num_citations', 0),
                    'url': item.get('pub_url', '')
                }
                papers.append(paper)
        
        print(f"✅ Successfully fetched {len(papers)} papers")
        return papers
    
    except requests.exceptions.Timeout:
        print("⏰ Google Scholar API timeout")
        return []
    except requests.exceptions.RequestException as e:
        print(f"🌐 Google Scholar API request error: {e}")
        return []
    except Exception as e:
        print(f"❌ Google Scholar API unexpected error: {e}")
        return []
    
def fetch_google_search_results(query, max_results=5):
    """
    Fetch general web resources from Google Custom Search API
    
    Args:
        query (str): The search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of web resource data
    """
    try:
        # Google Custom Search API endpoint
        url = "https://www.googleapis.com/customsearch/v1"
        
        # Parameters for the API request
        params = {
            'key': os.getenv('GOOGLE_CUSTOM_SEARCH_API_KEY'),
            'cx': '017576662512468239146:omuauf_lfve',  # This is a placeholder, you need to create a CSE and get your own cx value
            'q': query,
            'num': max_results
        }
        
        # Make the API request
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            print(f"Google Search API error: {response.status_code} - {response.text}")
            return []
        
        # Process the results
        data = response.json()
        results = []
        
        for item in data.get('items', []):
            results.append({
                'title': item.get('title', 'Untitled'),
                'link': item.get('link'),
                'snippet': item.get('snippet', 'No description available'),
                'displayLink': item.get('displayLink'),
                'formattedUrl': item.get('formattedUrl')
            })
        
        return results
    
    except Exception as e:
        print(f"Error fetching Google search results: {e}")
        return []

def fetch_github_repositories(query, max_results=5):
    """
    Fetch relevant GitHub repositories
    
    Args:
        query (str): The search query
        max_results (int): Maximum number of results to return
        
    Returns:
        list: List of repository data
    """
    try:
        # GitHub Search API endpoint
        url = f"https://api.github.com/search/repositories?q={quote(query)}&sort=stars&order=desc&per_page={max_results}"
        
        # Make the API request
        response = requests.get(url)
        
        if response.status_code != 200:
            print(f"GitHub API error: {response.status_code} - {response.text}")
            return []
        
        # Process the results
        data = response.json()
        repos = []
        
        for item in data.get('items', []):
            repos.append({
                'name': item.get('name'),
                'full_name': item.get('full_name'),
                'description': item.get('description', 'No description available'),
                'url': item.get('html_url'),
                'stars': item.get('stargazers_count', 0),
                'forks': item.get('forks_count', 0),
                'language': item.get('language'),
                'updated_at': item.get('updated_at')
            })
        
        return repos
    
    except Exception as e:
        print(f"Error fetching GitHub repositories: {e}")
        return []
    




# Add this function to your existing app/utils/llm_utils.py

import re
from groq import Groq
import os

# Your existing GROQ configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

def extract_citations_from_response(response_text):
    """Extract citations from AI response and return clean text + citations"""
    citations = []
    
    # Pattern to match citations like [1], [2], etc.
    citation_pattern = r'\[(\d+)\]'
    citation_matches = re.findall(citation_pattern, response_text)
    
    # Pattern to match reference sections
    reference_patterns = [
        r'📖\s*Sources?\s*&?\s*References?:?\s*\n(.*?)(?=\n\n|\Z)',
        r'Sources?:?\s*\n(.*?)(?=\n\n|\Z)',
        r'References?:?\s*\n(.*?)(?=\n\n|\Z)',
        r'Citations?:?\s*\n(.*?)(?=\n\n|\Z)'
    ]
    
    # Extract reference section
    reference_section = ""
    clean_text = response_text
    
    for pattern in reference_patterns:
        match = re.search(pattern, response_text, re.DOTALL | re.IGNORECASE)
        if match:
            reference_section = match.group(1).strip()
            # Remove the reference section from main text
            clean_text = re.sub(pattern, '', response_text, flags=re.DOTALL | re.IGNORECASE).strip()
            break
    
    # Parse individual references
    if reference_section:
        # Split by lines and process each reference
        ref_lines = reference_section.split('\n')
        for line in ref_lines:
            line = line.strip()
            if not line or not re.match(r'\[\d+\]', line):
                continue
            
            # Try different reference formats
            formats = [
                r'\[(\d+)\]\s*\[([^\]]+)\]\(([^)]+)\)',  # [1] [title](url)
                r'\[(\d+)\]\s*([^(]+)\s*\(([^)]+)\)',    # [1] title (url)
                r'\[(\d+)\]\s*([^-\n]+)-?\s*(https?://[^\s\n]+)',  # [1] title - url
                r'\[(\d+)\]\s*(https?://[^\s\n]+)\s*(.+)?',  # [1] url title
            ]
            
            citation_found = False
            for fmt in formats:
                match = re.match(fmt, line)
                if match:
                    groups = match.groups()
                    
                    if len(groups) >= 3:
                        num = groups[0]
                        
                        # Determine which group contains URL and title
                        if 'http' in groups[1]:  # URL is in group 1
                            url, title = groups[1], groups[2] or ""
                        elif len(groups) > 2 and 'http' in groups[2]:  # URL is in group 2
                            title, url = groups[1], groups[2]
                        else:
                            title, url = groups[1], groups[2] if len(groups) > 2 else ""
                        
                        # Extract domain from URL
                        domain = ""
                        if url and 'http' in url:
                            try:
                                domain = url.split('/')[2]
                            except:
                                domain = url
                        
                        citations.append({
                            'number': int(num),
                            'title': title.strip(),
                            'url': url.strip() if url else "",
                            'domain': domain
                        })
                        citation_found = True
                        break
            
            # If no format matched, try to extract basic info
            if not citation_found:
                basic_match = re.match(r'\[(\d+)\]\s*(.+)', line)
                if basic_match:
                    num, content = basic_match.groups()
                    # Look for URL in content
                    url_match = re.search(r'(https?://[^\s]+)', content)
                    if url_match:
                        url = url_match.group(1)
                        title = content.replace(url, '').strip()
                        domain = url.split('/')[2] if '/' in url else url
                        
                        citations.append({
                            'number': int(num),
                            'title': title,
                            'url': url,
                            'domain': domain
                        })
    
    # Sort citations by number
    citations.sort(key=lambda x: x['number'])
    
    return clean_text, citations

def ai_mentor_response(message, topic, objectives, skills, resources, conversation_context=[], user_profile=""):
    """Enhanced AI mentor response with citation extraction and profile awareness"""
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        # Format resources into a readable string
        resources_str = ""
        for category, items in resources.items():
            if items:  # Only include non-empty categories
                resources_str += f"{category}: {', '.join(items)}\n"
        
        # Create enhanced system prompt with profile awareness
        system_prompt = f"""You are an expert AI Study Mentor specializing in {topic}. You provide educational, supportive, and personalized guidance.

CURRENT LEARNING CONTEXT:
- Topic: {topic}
- Learning Objectives: {', '.join(objectives)}
- Key Skills to Master: {', '.join(skills)}

STUDENT PROFILE:
{user_profile}

AVAILABLE LEARNING RESOURCES:
{resources_str}

YOUR ROLE AS A STUDY MENTOR:
1. Provide clear, educational explanations tailored to the student's background
2. Break down complex concepts into digestible parts
3. Offer practical examples and real-world applications
4. Suggest specific practice exercises and projects
5. Reference current industry trends and requirements
6. Provide actionable study strategies and tips
7. Include relevant citations and sources when possible
8. Encourage critical thinking and problem-solving
9. Adapt your teaching style to the student's needs and progress

RESPONSE GUIDELINES:
- Be encouraging and supportive while maintaining academic rigor
- Use the student's profile to personalize recommendations
- Include specific, actionable advice
- Reference the available learning resources when appropriate
- Structure responses with clear headings and bullet points when helpful
- Include citations for factual claims when possible using format [1], [2], etc.
- If providing sources, include them at the end in format:
  📖 Sources & References:
  [1] [title](url) or [1] title - url

Remember: You're not just answering questions - you're guiding a learning journey."""

        # Prepare messages including conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation context (limited to last 8 messages to avoid token limits)
        if conversation_context:
            recent_context = conversation_context[-8:]  # Last 8 messages
            for msg in recent_context:
                if msg.get('role') and msg.get('content'):
                    messages.append({
                        "role": msg['role'],
                        "content": msg['content']
                    })
        
        # Add the current user message
        messages.append({"role": "user", "content": message})
        
        # Get response from Groq
        response = client.chat.completions.create(
            messages=messages,
            model=MODEL,
            temperature=0.6,  # Balanced for educational content
            max_tokens=2000,  # Generous limit for detailed explanations
            top_p=0.9
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Extract citations from response
        clean_response, citations = extract_citations_from_response(ai_response)
        
        return {
            'response': clean_response,
            'citations': citations
        }
        
    except Exception as e:
        print(f"❌ AI Mentor Response Error: {e}")
        return {
            'response': "I apologize, but I'm having trouble processing your request right now. Please try again in a moment.",
            'citations': []
        }

# Keep your existing get_groq_response function as fallback
def get_groq_response(message, topic, objectives, skills, resources, conversation_context=[]):
    """Your existing Groq response function - kept for backward compatibility"""
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
        for msg in conversation_context:
            messages.append(msg)
    
    messages.append({"role": "user", "content": message})
    
    response = client.chat.completions.create(
        messages=messages,
        model=MODEL,
        temperature=0.5,
        max_tokens=1000
    )
    
    return response.choices[0].message.content.strip()