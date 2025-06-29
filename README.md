# PBSC-Ignite 2.11: AI-Powered Career Readiness Platform

*An AI-Powered Learning Platform for Personalized Career Development*

PBSC-Ignite is a comprehensive learning management system that creates personalized learning roadmaps, provides AI-powered tutoring, and includes integrated assessments to help users achieve their career goals.

## ✨ Features

### 🎯 Personalized Learning Roadmaps
- AI-generated career-specific learning paths
- Multi-phase structured curriculum with weekly schedules
- Adaptive roadmap system that adjusts based on user progress
- Real-time progress tracking and analytics

### 🤖 AI-Powered Components
- **Leo AI Mentor**: Personalized tutoring and guidance powered by Claude Sonnet 4
- **Career Coach**: Professional development advice with advanced reasoning
- **Integrated Assessments**: Theory and coding evaluations
- **Smart Content Generation**: Using AWS Bedrock, Groq, Llama, and Perplexity APIs
- **Intelligent Progress Posts**: AI-generated LinkedIn content for achievement sharing

### 📊 Assessment System
- Automated coding project evaluations
- GitHub repository analysis
- Theory-based assessments
- Progress-based task unlocking
- Real-time feedback and scoring

### 🔗 Enhanced LinkedIn Integration
- **Unipile Integration**: Seamless LinkedIn account connection
- Profile data fetching and analysis
- **One-Click Progress Sharing**: AI-generated posts for learning milestones
- Professional networking insights
- Automated achievement publishing
- Custom post generation based on user progress and achievements

### ⚡ Performance Optimization
- Redis caching for LLM operations
- Profile data caching system
- Optimized database queries
- Smart resource management
- AWS Bedrock optimization for reasoning tasks

## 🏗 Architecture

### Tech Stack
- **Backend**: Flask (Python)
- **Database**: MongoDB
- **Caching**: Redis
- **Frontend**: HTML, CSS, JavaScript
- **AI APIs**: 
  - **AWS Bedrock**: Claude Sonnet 4 for advanced reasoning and tutoring
  - **Groq**: Fast inference for real-time responses
  - **Perplexity**: Real-time information and research
  - **Llama**: Structured content generation
- **Social Integration**: Unipile API for LinkedIn connectivity
- **Authentication**: Session-based auth with bcrypt

### Project Structure

```
PBSC-Ignite/
├── app/
│   ├── __init__.py                 # Flask app factory
│   ├── routes/
│   │   ├── auth.py                 # Authentication routes
│   │   ├── main.py                 # Main application routes
│   │   ├── roadmap.py              # Learning roadmap management
│   │   ├── career_coach.py         # Career coaching features
│   │   ├── tutor.py                # AI tutor functionality
│   │   ├── integrated_assessment.py # Assessment system
│   │   ├── linkedin_routes.py      # LinkedIn integration
│   │   └── social_sharing.py       # Social media sharing routes
│   ├── utils/
│   │   ├── db_utils.py             # Database operations
│   │   ├── llm_utils.py            # LLM API integrations
│   │   ├── cached_llm_utils.py     # Cached LLM operations
│   │   ├── bedrock_utils.py        # AWS Bedrock integration
│   │   ├── redis_cache_manager.py  # Redis caching system
│   │   ├── simple_profile_manager.py # Profile management
│   │   ├── resource_utils.py       # External resource fetching
│   │   ├── linkedin_integration.py # LinkedIn API integration
│   │   ├── unipile_integration.py  # Unipile API integration
│   │   └── post_generator.py       # AI-powered post generation
│   ├── templates/
│   │   ├── roadmap_v1.html         # Roadmap visualization
│   │   ├── learning_plan.html      # Learning plan interface
│   │   ├── integrated_assessment.html # Assessment interface
│   │   ├── social_sharing.html     # Social sharing interface
│   │   └── ...                     # Other templates
│   └── static/
│       ├── css/                    # Stylesheets
│       ├── js/                     # JavaScript files
│       └── assets/                 # Images and other assets
├── run.py                          # Application entry point
└── README.md                       # This file
```

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- MongoDB
- Redis (optional, for caching)
- AWS Account with Bedrock access
- API Keys for:
  - AWS Bedrock (Claude Sonnet 4)
  - Groq
  - Perplexity
  - Unipile (LinkedIn integration)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/PBSC-Ignite.git
   cd PBSC-Ignite
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # Flask Configuration
   SECRET_KEY=your-secret-key-here
   
   # Database Configuration
   MONGO_URI=mongodb://localhost:27017/
   DB_NAME=PBSC-Ignite-db
   
   # Redis Configuration (Optional)
   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=
   REDIS_DB=0
   
   # AWS Bedrock Configuration
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_REGION=us-east-1
   BEDROCK_MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0
   
   # AI API Keys
   GROQ_API_KEY=your-groq-api-key
   PERPLEXITY_API_KEY=your-perplexity-api-key
   
   # Unipile Integration
   UNIPILE_API_KEY=your-unipile-api-key
   UNIPILE_BASE_URL=https://api.unipile.com/v1
   
   # LinkedIn API (Legacy - Optional)
   LINKEDIN_CLIENT_ID=your-linkedin-client-id
   LINKEDIN_CLIENT_SECRET=your-linkedin-client-secret
   ```

4. **Start MongoDB and Redis**
   ```bash
   # Start MongoDB
   mongod
   
   # Start Redis (optional)
   redis-server
   ```

5. **Run the application**
   ```bash
   python run.py
   ```

6. **Access the application**
   
   Open your browser and navigate to `http://localhost:5000`

## 📖 Usage

### User Registration & Profile Setup
1. Create an account with your career goals and interests
2. Complete profile information including skills and experience
3. Connect LinkedIn profile via Unipile for enhanced personalization
4. Enable one-click progress sharing features

### Learning Roadmap Generation
1. Navigate to the roadmap section
2. Select your desired career path or topic
3. Claude Sonnet 4 generates a personalized multi-phase learning plan
4. Follow the structured weekly schedule with daily tasks

### AI Tutoring with Claude Sonnet 4
1. Access the tutor section for advanced personalized help
2. Ask complex questions about your learning content
3. Get sophisticated explanations with advanced reasoning
4. Receive tailored practice problems and coding challenges
5. Benefit from Claude's superior reasoning capabilities for complex concepts

### Assessment System
1. Complete assessments for each learning phase
2. Submit coding projects via GitHub integration
3. Receive automated evaluation and feedback from Claude Sonnet 4
4. Progress tracking unlocks new content

### Career Coaching
1. Get professional development advice powered by advanced AI reasoning
2. Industry insights and trend analysis
3. Interview preparation and skill recommendations
4. Career path optimization with intelligent suggestions

### One-Click LinkedIn Sharing
1. Complete learning milestones or assessments
2. Click the "Share Progress" button
3. AI automatically generates professional LinkedIn post content
4. Review and customize the generated post
5. Publish directly to LinkedIn via Unipile integration
6. Track engagement and professional network growth

## 🔧 Configuration

### Database Collections
- `users`: User profiles and authentication data
- `learning_progress`: Progress tracking and achievements
- `linkedin_data`: LinkedIn profile information via Unipile
- `linkedin_posts`: Achievement sharing history and analytics
- `companies`: Company information database
- `social_posts`: Generated post templates and performance metrics


## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Flask Community** for the excellent web framework
- **MongoDB** for flexible data storage
- **Redis** for high-performance caching
- **AWS Bedrock** for providing access to Claude Sonnet 4
- **Unipile** for seamless LinkedIn integration
- **Groq, Perplexity, and Llama** for AI capabilities
- **Anthropic** for Claude Sonnet 4's advanced reasoning capabilities

---

**PBSC-Ignite 2.11** - *Enhanced with Real-Time Intelligence & Powered by Perplexity and Claude Sonnet for Evaluation and Adaptive Roadmaps*

*An AF's Endeavor Developed with 🥤 and 💡*
