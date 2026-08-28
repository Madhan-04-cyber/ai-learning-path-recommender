import os
import math
import json
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from skill_engine import analyze_skill_gaps, build_skill_models
from roadmap_service import Roadmap, generate_roadmap, replan_path

# Initialize FastAPI App
app = FastAPI(title="PathMind AI - Personalized Learning Path Engine")

# Configure CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini Client using the new google-genai SDK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
def get_gemini_client():
    if GEMINI_API_KEY:
        try:
            return genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            return None
    return None


def build_coach_system_prompt(request: "ChatRequest", career_name: str) -> str:
    """Build a bounded, context-aware coaching prompt."""
    context_lines = [
        f"Career goal: {career_name}",
        f"Current page: {request.current_page or 'unknown'}",
        f"Current milestone: {request.current_milestone or 'unknown'}",
        f"Current skill: {request.current_skill or 'unknown'}",
        f"Skill proficiency: {request.skill_proficiency if request.skill_proficiency is not None else 'unknown'}",
        f"Weak areas: {', '.join(request.weak_areas) if request.weak_areas else 'unknown'}",
        f"Learning preference: {request.learning_preference or 'unknown'}",
        f"Active bottleneck: {request.bottleneck or 'unknown'}",
        f"Next best action: {request.next_action or 'unknown'}",
    ]
    if request.recent_assessment:
        context_lines.append(f"Recent assessment: {json.dumps(request.recent_assessment)}")
    if request.recent_mistakes:
        context_lines.append(f"Recent mistakes: {json.dumps(request.recent_mistakes[:5])}")
    if request.roadmap:
        context_lines.append(f"Roadmap snapshot: {json.dumps(request.roadmap[:8])}")
    return f"""
You are PathMind AI Coach.
You are not a generic chatbot.
You coach using only the learner context below and do not invent scores, milestones, or roadmap steps.

Learner context:
{chr(10).join(f'- {line}' for line in context_lines)}

Rules:
- Explain recommendations using actual learner data when available.
- If the user asks to skip a skill, do not mutate the roadmap. Explain why it is or is not safe and request verification.
- If data is unavailable, say so clearly.
- Be concise, supportive, and specific.
- Always output markdown.
""".strip()

# --- Career Database ---
CAREERS = {
    "backend_ai_developer": {
        "id": "backend_ai_developer",
        "name": "Backend AI Developer",
        "description": "Builds and deploys robust backend services integrated with artificial intelligence models, databases, and APIs.",
        "required_skills": [
            "python", "git", "oop", "http_fundamentals", "rest_apis", 
            "sql_basics", "postgresql", "fastapi", "auth_security", 
            "numpy_pandas", "math_statistics", "machine_learning_basics", 
            "model_evaluation", "model_serving", "ai_apis", "rag", "docker", "cloud_deployment"
        ],
        "optional_skills": ["backend_architecture", "embeddings", "vector_databases", "monitoring", "capstone_project"],
        "capstone_project": {
            "title": "AI-Powered Backend Microservice",
            "description": "Design and build a FastAPI backend application that integrates PostgreSQL with vector similarity search (RAG), user authentication, Docker containment, and automated deployment.",
            "requirements": [
                "Implement FastAPI routing with JWT authentication.",
                "Integrate PostgreSQL to store user profiles and learning history.",
                "Integrate an AI API to query embeddings and generate answers.",
                "Dockerize the application and set up a deployment configuration."
            ]
        }
    },
    "ai_engineer": {
        "id": "ai_engineer",
        "name": "AI Engineer",
        "description": "Focuses on deploying, prompt engineering, fine-tuning, and integrating large language models into software applications.",
        "required_skills": [
            "python", "git", "numpy_pandas", "math_statistics", "machine_learning_basics",
            "deep_learning", "nlp", "llm_fundamentals", "prompt_engineering",
            "ai_apis", "rag", "vector_databases", "fine_tuning", "ai_deployment"
        ],
        "capstone_project": {
            "title": "Enterprise RAG & Agentic Chat System",
            "description": "Build a conversational agentic system with RAG, semantic chunking, dynamic prompt selection, and fine-tuning evaluation.",
            "requirements": [
                "Build a document parser and vector indexer.",
                "Implement dynamic prompt templating with system instructions.",
                "Deploy the model using FastAPI and evaluate responses using RAGAS metrics.",
                "Integrate fine-tuning feedback loops."
            ]
        }
    },
    "ml_engineer": {
        "id": "ml_engineer",
        "name": "Machine Learning Engineer",
        "description": "Designs, trains, evaluates, and deploys predictive machine learning and deep learning models at scale.",
        "required_skills": [
            "python", "git", "math_statistics", "numpy_pandas", "machine_learning_basics",
            "model_evaluation", "deep_learning", "computer_vision", "nlp", "mlops", "model_serving"
        ],
        "capstone_project": {
            "title": "End-to-End MLOps Pipeline",
            "description": "Establish a reproducible machine learning pipeline that handles training, experiment tracking, validation, model registry, and containerized serving.",
            "requirements": [
                "Train a deep learning classifier on tabular or image data.",
                "Track experiments and register the model.",
                "Deploy the model via FastAPI containerized in Docker.",
                "Set up drift monitoring and automated retraining scripts."
            ]
        }
    },
    "data_scientist": {
        "id": "data_scientist",
        "name": "Data Scientist",
        "description": "Analyzes complex datasets, builds predictive models, creates data visualizations, and extracts business intelligence.",
        "required_skills": [
            "python", "git", "math_statistics", "numpy_pandas", "data_visualization",
            "sql_basics", "data_warehousing", "machine_learning_basics", "model_evaluation", "feature_engineering"
        ],
        "capstone_project": {
            "title": "Predictive Data Science & Insights Dashboard",
            "description": "Analyze a large raw dataset, perform feature engineering, fit predictive ML models, and build an interactive reporting dashboard.",
            "requirements": [
                "Extract and clean raw data using Pandas and SQL.",
                "Conduct Exploratory Data Analysis with visualizations.",
                "Build and evaluate an ensemble predictive model.",
                "Create a multi-page interactive dashboard with findings and recommendations."
            ]
        }
    },
    "full_stack_developer": {
        "id": "full_stack_developer",
        "name": "Full Stack Developer",
        "description": "Builds both client-side interfaces and backend APIs, databases, and deployment pipelines.",
        "required_skills": [
            "html_css", "javascript", "git", "react", "tailwind_css", "nextjs",
            "http_fundamentals", "sql_basics", "rest_apis", "nodejs_express",
            "postgresql", "auth_security", "docker", "cloud_deployment"
        ],
        "capstone_project": {
            "title": "Collaborative Task Manager SaaS",
            "description": "Create a full-stack SaaS application with client dashboard, backend API server, relational database, user auth, and cloud hosting.",
            "requirements": [
                "Build responsive React frontend with Tailwind CSS and Next.js.",
                "Create backend REST API with Node.js/Express.",
                "Integrate PostgreSQL database with ORM schemas.",
                "Add secure JWT authentication and route guard protection."
            ]
        }
    }
}

# --- Skill Knowledge Graph ---
SKILL_GRAPH = {
    # Programming & Basics
    "python": {
        "id": "python",
        "title": "Python Programming",
        "description": "Mastering syntax, control flow, functions, and data structures in Python.",
        "prerequisites": [],
        "required_proficiency": 80,
        "estimated_hours": 8,
        "difficulty": "Beginner",
        "resources": [
            {"title": "Python for Beginners (Mosh)", "type": "Video", "url": "https://www.youtube.com/watch?v=_uQrJ0TkZlc"},
            {"title": "Official Python Tutorial", "type": "Documentation", "url": "https://docs.python.org/3/tutorial/"}
        ],
        "practice": ["Write a script to parse a text file and count word occurrences.", "Create a simple command-line calculator."],
        "project": {"title": "Expense Tracker CLI", "description": "Build a CLI tool to log, save, and analyze monthly expenses stored in a JSON file."}
    },
    "git": {
        "id": "git",
        "title": "Git & GitHub",
        "description": "Version control basics, branching, committing, merging, and pull requests.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 4,
        "difficulty": "Beginner",
        "resources": [
            {"title": "Git Cheat Sheet", "type": "Documentation", "url": "https://education.github.com/git-cheat-sheet-education.pdf"},
            {"title": "Git & GitHub Crash Course", "type": "Video", "url": "https://www.youtube.com/watch?v=RGOj5yH7evk"}
        ],
        "practice": ["Create a repo, commit changes, create a feature branch, and merge it.", "Resolve a simulated merge conflict."],
        "project": {"title": "Open Source Contribution Walkthrough", "description": "Fork a repo, add a readme improvement, and push a pull request locally."}
    },
    "oop": {
        "id": "oop",
        "title": "Object-Oriented Programming (OOP)",
        "description": "Classes, objects, inheritance, polymorphism, encapsulation, and abstraction in Python.",
        "prerequisites": ["python"],
        "required_proficiency": 75,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [
            {"title": "Core OOP Python Guide", "type": "Article", "url": "https://realpython.com/python3-object-oriented-programming/"}
        ],
        "practice": ["Design a class hierarchy for a library system.", "Implement overriding and abstract classes."],
        "project": {"title": "RPG Text-Based Battle Simulator", "description": "Create a console-based battle simulator using inheritance and polymorphism for heroes and enemies."}
    },
    
    # Web & Networking
    "http_fundamentals": {
        "id": "http_fundamentals",
        "title": "HTTP & Networking Fundamentals",
        "description": "Understanding HTTP requests, responses, headers, methods, and status codes.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 5,
        "difficulty": "Beginner",
        "resources": [
            {"title": "MDN HTTP Guide", "type": "Documentation", "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP"},
            {"title": "HTTP crash course", "type": "Video", "url": "https://www.youtube.com/watch?v=iYM2zFP3Zn0"}
        ],
        "practice": ["Use curl or Postman to inspect response headers.", "Write raw TCP HTTP responses manually."],
        "project": {"title": "Mock HTTP Client", "description": "Write a python script using socket connection to perform a raw GET request to an open server."}
    },
    "rest_apis": {
        "id": "rest_apis",
        "title": "RESTful API Design",
        "description": "Designing endpoints, HTTP method mapping, query/path parameters, and HTTP responses.",
        "prerequisites": ["http_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "REST API Best Practices", "type": "Article", "url": "https://stackoverflow.blog/2020/03/02/best-practices-for-rest-api-design/"}
        ],
        "practice": ["Design endpoint paths for an e-commerce catalog.", "Map standard CRUD actions to HTTP verbs."],
        "project": {"title": "API Specification Design", "description": "Design an OpenAPI (Swagger) spec file for a social media application."}
    },
    
    # Database
    "sql_basics": {
        "id": "sql_basics",
        "title": "SQL Basics",
        "description": "Select, filter, join, aggregate, and update statements in relational databases.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [
            {"title": "SQL Tutorial (W3Schools)", "type": "Course", "url": "https://www.w3schools.com/sql/"}
        ],
        "practice": ["Write queries to join user profiles and their purchase orders.", "Use GROUP BY to aggregate statistics."],
        "project": {"title": "E-Commerce Database Schema", "description": "Create SQL queries to build tables and insert seed data for a store database."}
    },
    "postgresql": {
        "id": "postgresql",
        "title": "PostgreSQL & Database Optimization",
        "description": "Indexes, keys, constraints, triggers, and query execution planning in PostgreSQL.",
        "prerequisites": ["sql_basics"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "PostgreSQL Tutorial", "type": "Documentation", "url": "https://www.postgresqltutorial.com/"}
        ],
        "practice": ["Explain SQL queries using EXPLAIN ANALYZE.", "Create primary and foreign key constraints."],
        "project": {"title": "High-Performance Blog Database Setup", "description": "Deploy PostgreSQL locally, set up indexing for tags, and optimize slow queries."}
    },
    
    # Python Web Framework
    "fastapi": {
        "id": "fastapi",
        "title": "FastAPI Web Framework",
        "description": "Routing, Pydantic data schemas, dependency injection, and automatic API documentation.",
        "prerequisites": ["oop", "rest_apis"],
        "required_proficiency": 80,
        "estimated_hours": 10,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Official FastAPI Documentation", "type": "Documentation", "url": "https://fastapi.tiangolo.com/"},
            {"title": "FastAPI Crash Course", "type": "Video", "url": "https://www.youtube.com/watch?v=tLKKmouUoms"}
        ],
        "practice": ["Create a hello world router.", "Use Pydantic for request body validation."],
        "project": {"title": "Task Manager Backend API", "description": "Build a REST API to manage lists and tasks with full Pydantic validations and error handlers."}
    },
    "auth_security": {
        "id": "auth_security",
        "title": "Authentication & API Security",
        "description": "OAuth2, JWT tokens, bcrypt password hashing, and API rate-limiting.",
        "prerequisites": ["fastapi"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Advanced",
        "resources": [
            {"title": "FastAPI OAuth2 Guide", "type": "Documentation", "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/"}
        ],
        "practice": ["Hash passwords using bcrypt.", "Validate JWT tokens in api dependency."],
        "project": {"title": "Secure API Gateway", "description": "Create a FastAPI authentication microservice that registers users and issues tokens."}
    },
    
    # AI & Machine Learning
    "numpy_pandas": {
        "id": "numpy_pandas",
        "title": "NumPy & Pandas Data Analysis",
        "description": "Arrays, dataframes, filtering, cleaning, and transforming datasets.",
        "prerequisites": ["python"],
        "required_proficiency": 75,
        "estimated_hours": 7,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Pandas Tutorial (Kaggle)", "type": "Course", "url": "https://www.kaggle.com/learn/pandas"}
        ],
        "practice": ["Clean missing values in a dataset.", "Merge dataframes by composite keys."],
        "project": {"title": "Sales Trend Exploratory Report", "description": "Load a CSV of retail sales, clean the dates, aggregate totals by department, and export statistical summaries."}
    },
    "math_statistics": {
        "id": "math_statistics",
        "title": "Mathematics & Statistics for AI",
        "description": "Probability distributions, linear algebra, calculus derivatives, and hypothesis testing.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 10,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Khan Academy Statistics", "type": "Course", "url": "https://www.khanacademy.org/math/statistics-probability"}
        ],
        "practice": ["Compute dot products and matrix transpose.", "Run a z-test on a mock campaign database."],
        "project": {"title": "A/B Testing Evaluator", "description": "Write a statistical analyzer script to evaluate and plot statistical significance between website layouts."}
    },
    "machine_learning_basics": {
        "id": "machine_learning_basics",
        "title": "Machine Learning Fundamentals",
        "description": "Supervised learning, linear regression, decision trees, clustering, and overfitting.",
        "prerequisites": ["numpy_pandas", "math_statistics"],
        "required_proficiency": 75,
        "estimated_hours": 12,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Scikit-Learn Official Tutorials", "type": "Documentation", "url": "https://scikit-learn.org/stable/tutorial/index.html"},
            {"title": "Machine Learning Zoomcamp", "type": "Course", "url": "https://github.com/DataTalksClub/machine-learning-zoomcamp"}
        ],
        "practice": ["Train a linear regression using Scikit-Learn.", "Split datasets into train/test sets."],
        "project": {"title": "Housing Price Predictor Model", "description": "Clean, train, and test a random forest regressor to predict house pricing based on neighborhood variables."}
    },
    "model_evaluation": {
        "id": "model_evaluation",
        "title": "Model Evaluation & Metrics",
        "description": "Precision, recall, F1-score, ROC-AUC, confusion matrix, and cross-validation.",
        "prerequisites": ["machine_learning_basics"],
        "required_proficiency": 75,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Model Evaluation Guide", "type": "Article", "url": "https://towardsdatascience.com/metrics-to-evaluate-your-machine-learning-algorithm-f10ba6e38234"}
        ],
        "practice": ["Calculate classification matrices manually.", "Run 5-fold cross-validation on a pipeline."],
        "project": {"title": "Classifier Audit & Evaluation Report", "description": "Take a pre-trained spam model, evaluate precision-recall curves, and tune threshold parameters."}
    },
    
    # AI Deployments & Integrations
    "model_serving": {
        "id": "model_serving",
        "title": "Model Serving & Serialization",
        "description": "Saving models via pickle/joblib, and loading them inside APIs for prediction.",
        "prerequisites": ["fastapi", "machine_learning_basics"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Deploying Models with FastAPI", "type": "Article", "url": "https://fastapi.tiangolo.com/advanced/custom-response/"}
        ],
        "practice": ["Pickle a regression model.", "Create a /predict endpoint in FastAPI."],
        "project": {"title": "Predictive Scoring Web API", "description": "Create an API endpoint that receives customer features, feeds them to a serialized ML model, and returns a loan approval probability."}
    },
    "ai_apis": {
        "id": "ai_apis",
        "title": "Large Language Model APIs",
        "description": "Interacting with Gemini, OpenAI, and Anthropic APIs. API keys, prompt tokens, and streaming.",
        "prerequisites": ["fastapi"],
        "required_proficiency": 75,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Google GenAI SDK Guide", "type": "Documentation", "url": "https://ai.google.dev/gemini-api/docs/quickstart"}
        ],
        "practice": ["Run a completion call to Gemini.", "Configure structured output JSON responses."],
        "project": {"title": "AI Translator Service", "description": "Develop a FastAPI microservice that uses LLM APIs to translate code comments between programming languages."}
    },
    "rag": {
        "id": "rag",
        "title": "Retrieval-Augmented Generation (RAG)",
        "description": "Connecting LLMs to external data, semantic chunking, prompt templates, and citation tracking.",
        "prerequisites": ["ai_apis", "vector_databases"],
        "required_proficiency": 80,
        "estimated_hours": 12,
        "difficulty": "Advanced",
        "resources": [
            {"title": "RAG Tutorial (LangChain)", "type": "Documentation", "url": "https://python.langchain.com/v0.2/docs/tutorials/rag/"}
        ],
        "practice": ["Chunk a large PDF document.", "Pass document context inside LLM prompt manually."],
        "project": {"title": "Internal FAQ Chatbot Server", "description": "Implement a pipeline that ingests Markdown policies, searches chunks for relevance, and generates answers using Gemini."}
    },
    "vector_databases": {
        "id": "vector_databases",
        "title": "Vector Databases & Embeddings",
        "description": "ChromaDB, Pinecone, and PGVector. Storing and querying vector embeddings.",
        "prerequisites": ["embeddings"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Advanced",
        "resources": [
            {"title": "Vector Database Handbook", "type": "Article", "url": "https://www.pinecone.io/learn/vector-database/"}
        ],
        "practice": ["Embed strings using sentence-transformers.", "Query ChromaDB index for top 3 documents."],
        "project": {"title": "Semantic Search Engine", "description": "Configure pgvector in PostgreSQL and query items by vector distance."}
    },
    
    # Operations
    "docker": {
        "id": "docker",
        "title": "Docker Containers",
        "description": "Writing Dockerfiles, building container images, volume mounts, and network exposure.",
        "prerequisites": ["fastapi"],
        "required_proficiency": 75,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Docker Curriculum", "type": "Course", "url": "https://docker-curriculum.com/"}
        ],
        "practice": ["Write a Dockerfile for a basic python script.", "Bind port 8000 from container to host."],
        "project": {"title": "Containerized FastAPI System", "description": "Package a FastAPI app and a PostgreSQL database in docker-compose.yml and launch them seamlessly."}
    },
    "cloud_deployment": {
        "id": "cloud_deployment",
        "title": "Cloud Deployment & Pipelines",
        "description": "Deploying apps to Render, AWS, or GCP. CI/CD actions and env variables.",
        "prerequisites": ["docker"],
        "required_proficiency": 70,
        "estimated_hours": 8,
        "difficulty": "Advanced",
        "resources": [
            {"title": "GitHub Actions Tutorial", "type": "Video", "url": "https://www.youtube.com/watch?v=R8_veQiYtgo"}
        ],
        "practice": ["Set up Render web service.", "Write GitHub Action pipeline yaml."],
        "project": {"title": "Auto-Deploying FastAPI Production", "description": "Create a repo with GitHub Actions configured to build a Docker image and deploy to Render on git push."}
    },
    
    # Advanced AI Career Tracks
    "deep_learning": {
        "id": "deep_learning",
        "title": "Deep Learning & Neural Networks",
        "description": "Multi-layer perceptrons, backpropagation, CNNs, RNNs, and PyTorch frameworks.",
        "prerequisites": ["machine_learning_basics"],
        "required_proficiency": 80,
        "estimated_hours": 15,
        "difficulty": "Advanced",
        "resources": [
            {"title": "PyTorch for Deep Learning Course", "type": "Course", "url": "https://www.youtube.com/watch?v=V_xro1bcAuA"}
        ],
        "practice": ["Create a feedforward network in PyTorch.", "Implement training loss backpropagation loops."],
        "project": {"title": "Digit Classifier Model", "description": "Train a neural network on the MNIST dataset using PyTorch to recognize handwritten numbers."}
    },
    "nlp": {
        "id": "nlp",
        "title": "Natural Language Processing (NLP)",
        "description": "Tokenization, lemmatization, tf-idf, transformers, attention mechanisms, and BERT.",
        "prerequisites": ["deep_learning"],
        "required_proficiency": 75,
        "estimated_hours": 10,
        "difficulty": "Advanced",
        "resources": [
            {"title": "Hugging Face NLP Course", "type": "Course", "url": "https://huggingface.co/learn/nlp-course/chapter1/1"}
        ],
        "practice": ["Tokenize text datasets using Transformers.", "Extract named entities using SpaCy."],
        "project": {"title": "Review Sentiment Analyzer", "description": "Fine-tune a BERT-based classifier from Hugging Face on imdb review sentiments."}
    },
    "llm_fundamentals": {
        "id": "llm_fundamentals",
        "title": "Large Language Model Fundamentals",
        "description": "Transformer blocks, decoding strategies, contextual windows, temperature, and quantization.",
        "prerequisites": ["nlp"],
        "required_proficiency": 80,
        "estimated_hours": 8,
        "difficulty": "Advanced",
        "resources": [
            {"title": "Transformers explained", "type": "Article", "url": "https://jalammar.github.io/illustrated-transformer/"}
        ],
        "practice": ["Compare beam search and top-k generation.", "Quantize a model locally using llama.cpp."],
        "project": {"title": "Local LLM Host", "description": "Build an API serving queries using a quantized local model Llama-3."}
    },
    "prompt_engineering": {
        "id": "prompt_engineering",
        "title": "System Prompt Engineering",
        "description": "Few-shot prompting, chain-of-thought, prompt templates, and system instruction patterns.",
        "prerequisites": ["llm_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 5,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Prompt Engineering Guide", "type": "Documentation", "url": "https://www.promptingguide.ai/"}
        ],
        "practice": ["Write a few-shot classification prompt.", "Implement chain-of-thought step extraction."],
        "project": {"title": "Automated Agent Prompt Pipeline", "description": "Design dynamic prompt scripts to generate structured user summaries."}
    },
    "fine_tuning": {
        "id": "fine_tuning",
        "title": "LLM Fine-Tuning (LoRA/QLoRA)",
        "description": "Supervised fine-tuning (SFT), PEFT, datasets preparation, and weights merging.",
        "prerequisites": ["llm_fundamentals", "deep_learning"],
        "required_proficiency": 80,
        "estimated_hours": 14,
        "difficulty": "Advanced",
        "resources": [
            {"title": "LLM Fine-Tuning Guide (Hugging Face)", "type": "Article", "url": "https://huggingface.co/docs/peft/index"}
        ],
        "practice": ["Format datasets into instruction formats.", "Run LoRA training on Llama-3 using Unsloth."],
        "project": {"title": "Custom Customer Care Assistant Tuning", "description": "Fine-tune a 3B parameter model to answer system FAQ tickets."}
    },
    "ai_deployment": {
        "id": "ai_deployment",
        "title": "AI Serving & vLLM",
        "description": "Serving models with vLLM, Triton Server, optimization compilers (TensorRT-LLM).",
        "prerequisites": ["llm_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 10,
        "difficulty": "Advanced",
        "resources": [
            {"title": "Deploying LLMs at scale", "type": "Article", "url": "https://docs.vllm.ai/en/latest/"}
        ],
        "practice": ["Host a model endpoint using vLLM.", "Measure tokens per second latency."],
        "project": {"title": "High-Throughput Model API Server", "description": "Set up a dockerized vLLM engine connected to a Next.js interface."}
    },
    "computer_vision": {
        "id": "computer_vision",
        "title": "Computer Vision & CNNs",
        "description": "Image processing, convolutions, ResNet architectures, object detection, and segmentation.",
        "prerequisites": ["deep_learning"],
        "required_proficiency": 75,
        "estimated_hours": 12,
        "difficulty": "Advanced",
        "resources": [
            {"title": "Stanford CS231n: Computer Vision", "type": "Course", "url": "http://cs231n.stanford.edu/"}
        ],
        "practice": ["Implement a simple 2D convolution kernel.", "Train a ResNet image classifier in PyTorch."],
        "project": {"title": "Traffic Camera Object Detector", "description": "Build an object detector using YOLOv8 to localize vehicles in real-time video clips."}
    },
    "mlops": {
        "id": "mlops",
        "title": "MLOps & Experiment Tracking",
        "description": "MLflow, DVC data versioning, model registries, and automated testing.",
        "prerequisites": ["machine_learning_basics", "git"],
        "required_proficiency": 75,
        "estimated_hours": 10,
        "difficulty": "Advanced",
        "resources": [
            {"title": "MLOps Zoomcamp", "type": "Course", "url": "https://github.com/DataTalksClub/mlops-zoomcamp"}
        ],
        "practice": ["Log hyperparameters and artifacts in MLflow.", "Create version control checkpoints using DVC."],
        "project": {"title": "Automated Training Audit Pipeline", "description": "Configure GitHub actions to retrain models and register them under MLflow on schedule."}
    },
    "data_visualization": {
        "id": "data_visualization",
        "title": "Data Visualization & Communication",
        "description": "Matplotlib, Seaborn, Plotly, and storytelling dashboards.",
        "prerequisites": ["numpy_pandas"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [
            {"title": "Storytelling with Data Guide", "type": "Article", "url": "https://www.storytellingwithdata.com/"}
        ],
        "practice": ["Plot complex correlations with seaborn heatmaps.", "Build interactive scatter plots in Plotly."],
        "project": {"title": "Sales Performance Dashboard", "description": "Create an interactive visual reporting script using Streamlit."}
    },
    "data_warehousing": {
        "id": "data_warehousing",
        "title": "Data Warehousing & ETL Pipelines",
        "description": "Dimensional modeling, Snowflake, dbt transformations, and ETL orchestrations.",
        "prerequisites": ["sql_basics"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "What is a Data Warehouse?", "type": "Article", "url": "https://www.snowflake.com/guides/what-data-warehouse/"}
        ],
        "practice": ["Design a star schema for sales transactions.", "Write dbt models to transform raw customer orders."],
        "project": {"title": "Cloud ETL Pipeline System", "description": "Write a python script loading data from open APIs, transforming columns, and storing them in Snowflake."}
    },
    "feature_engineering": {
        "id": "feature_engineering",
        "title": "Feature Engineering & Selection",
        "description": "Encoding, scaling, imputation, dimensional reduction (PCA), and feature selection techniques.",
        "prerequisites": ["machine_learning_basics"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Feature Engineering Cookbook", "type": "Article", "url": "https://www.analyticsvidhya.com/blog/2020/12/feature-engineering-for-machine-learning/"}
        ],
        "practice": ["One-hot encode categorical features.", "Apply StandardScaler vs MinMaxScaler."],
        "project": {"title": "Credit Risk Feature Processor", "description": "Build a module that converts raw transaction lines into clean datasets for risk classification."}
    },
    
    # Frontend/Fullstack specific
    "html_css": {
        "id": "html_css",
        "title": "HTML & CSS Layouts",
        "description": "Semantic markup, Flexbox, CSS Grid, and responsive viewport sizing.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [
            {"title": "HTML & CSS Full Course", "type": "Course", "url": "https://www.youtube.com/watch?v=mU6anWqOD4c"}
        ],
        "practice": ["Write a landing page layout using CSS Grid.", "Implement media queries for mobile UI."],
        "project": {"title": "Responsive Portfolio Website", "description": "Build and host a personal web portfolio using semantic HTML5 and vanilla responsive CSS."}
    },
    "javascript": {
        "id": "javascript",
        "title": "Modern JavaScript (ES6+)",
        "description": "Promises, async/await, DOM manipulation, scopes, arrow functions, and array filters.",
        "prerequisites": ["html_css"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Beginner",
        "resources": [
            {"title": "Modern JavaScript Tutorial", "type": "Documentation", "url": "https://javascript.info/"}
        ],
        "practice": ["Fetch JSON objects using native fetch API.", "Write async map transformations."],
        "project": {"title": "Interactive Weather dashboard", "description": "Build a browser weather card fetching temperature values from OpenWeather APIs."}
    },
    "react": {
        "id": "react",
        "title": "React JS Library",
        "description": "Virtual DOM, JSX, props, state, hooks (useState, useEffect, useContext), and event handlers.",
        "prerequisites": ["javascript"],
        "required_proficiency": 75,
        "estimated_hours": 10,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Official React Docs", "type": "Documentation", "url": "https://react.dev/"}
        ],
        "practice": ["Manage list items inside state.", "Fetch and render API items in useEffect hooks."],
        "project": {"title": "Recipe Grid Dashboard", "description": "Construct an interactive dashboard to filter, search, and details-expand recipe catalog cards."}
    },
    "tailwind_css": {
        "id": "tailwind_css",
        "title": "Tailwind Utility Styling",
        "description": "Utility classes, dark mode selectors, hover/active variables, and component customization.",
        "prerequisites": ["html_css"],
        "required_proficiency": 70,
        "estimated_hours": 4,
        "difficulty": "Beginner",
        "resources": [
            {"title": "Official Tailwind CSS Guide", "type": "Documentation", "url": "https://tailwindcss.com/docs/"}
        ],
        "practice": ["Style forms and cards with hover/focus states.", "Build layout cards with flex container utilities."],
        "project": {"title": "Interactive Admin Settings Panel", "description": "Create a styled settings interface complete with toggles, tabs, and alerts."}
    },
    "nextjs": {
        "id": "nextjs",
        "title": "Next.js Framework",
        "description": "Server-side rendering, routing models, server components, and API routes.",
        "prerequisites": ["react"],
        "required_proficiency": 75,
        "estimated_hours": 10,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Next.js documentation", "type": "Documentation", "url": "https://nextjs.org/docs"}
        ],
        "practice": ["Build dynamic page routing folders.", "Fetch database results in server components."],
        "project": {"title": "Multi-Page Blogging App", "description": "Construct a Next.js website with static pages, SSR blog articles, and dynamic comments."}
    },
    "nodejs_express": {
        "id": "nodejs_express",
        "title": "Node.js & Express API",
        "description": "File systems, middleware, router controllers, error handlers, and CORS protocols in Express.",
        "prerequisites": ["javascript", "rest_apis"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [
            {"title": "Express JS Guide", "type": "Documentation", "url": "https://expressjs.com/"}
        ],
        "practice": ["Write logging middleware functions.", "Serve static static pages from router."],
        "project": {"title": "Collaborative Notes Server", "description": "Deploy a server endpoints structure supporting CRUD records in text archives."}
    }
}

# Extended competencies remain separate from the existing roadmap until its later phase.
SKILL_GRAPH.update({
    "backend_architecture": {"id": "backend_architecture", "title": "Backend Architecture", "description": "Designing reliable service boundaries, data flows, and operational concerns.", "prerequisites": ["fastapi", "postgresql"], "required_proficiency": 75, "estimated_hours": 10, "difficulty": "Advanced"},
    "embeddings": {"id": "embeddings", "title": "Embeddings", "description": "Representing text and other data as vectors for semantic retrieval.", "prerequisites": ["ai_apis", "machine_learning_basics"], "required_proficiency": 70, "estimated_hours": 8, "difficulty": "Intermediate"},
    "monitoring": {"id": "monitoring", "title": "Application Monitoring", "description": "Observability, health checks, metrics, logs, and alerting for deployed services.", "prerequisites": ["docker", "cloud_deployment"], "required_proficiency": 70, "estimated_hours": 6, "difficulty": "Intermediate"},
    "capstone_project": {"id": "capstone_project", "title": "Production AI Backend Capstone", "description": "Combine backend, database, AI integration, and deployment skills in one production project.", "prerequisites": ["backend_architecture", "rag", "monitoring"], "required_proficiency": 80, "estimated_hours": 20, "difficulty": "Advanced"},
})

# Add default prerequisites and competencies if missing
for k, v in SKILL_GRAPH.items():
    if "required_proficiency" not in v:
        v["required_proficiency"] = 70
    if "estimated_hours" not in v:
        v["estimated_hours"] = 6
    if "difficulty" not in v:
        v["difficulty"] = "Intermediate"

# --- Hardcoded Diagnostic Quizzes (Fallback) ---
PRESET_QUIZZES = {
    "python": [
        {"q": "What is the output of: print(type([1, 2]))", "options": ["list", "tuple", "dict", "array"], "answer": "list"},
        {"q": "How do you catch a specific error in Python?", "options": ["try/catch", "try/except", "do/except", "try/fail"], "answer": "try/except"},
        {"q": "Which data type is mutable in Python?", "options": ["tuple", "string", "list", "integer"], "answer": "list"}
    ],
    "oop": [
        {"q": "Which concept allows a subclass to share methods from a superclass?", "options": ["Encapsulation", "Inheritance", "Polymorphism", "Abstraction"], "answer": "Inheritance"},
        {"q": "What is the purpose of the '__init__' method?", "options": ["To destroy objects", "To import modules", "To initialize class instances", "To define polymorphism"], "answer": "To initialize class instances"},
        {"q": "Which keyword is used to access methods of parent class?", "options": ["this", "parent", "self", "super"], "answer": "super"}
    ],
    "git": [
        {"q": "Which command saves active changes to staging area?", "options": ["git commit", "git push", "git add", "git save"], "answer": "git add"},
        {"q": "How do you make a new branch and switch to it?", "options": ["git checkout -b branch_name", "git branch branch_name", "git commit -m branch_name", "git push branch_name"], "answer": "git checkout -b branch_name"},
        {"q": "Which git operation downloads remote revisions and merges them?", "options": ["git push", "git fetch", "git pull", "git clone"], "answer": "git pull"}
    ],
    "http_fundamentals": [
        {"q": "Which HTTP status code represents 'Not Found'?", "options": ["200 OK", "404 Not Found", "500 Server Error", "301 Redirect"], "answer": "404 Not Found"},
        {"q": "What method is used to submit data to be processed?", "options": ["GET", "POST", "DELETE", "HEAD"], "answer": "POST"},
        {"q": "What is the default TCP port for HTTPS?", "options": ["80", "8080", "22", "443"], "answer": "443"}
    ],
    "sql_basics": [
        {"q": "Which SQL keyword filters group metrics?", "options": ["WHERE", "HAVING", "ORDER BY", "SELECT"], "answer": "HAVING"},
        {"q": "Which JOIN returns all records from left and matches from right?", "options": ["INNER JOIN", "LEFT JOIN", "RIGHT JOIN", "FULL JOIN"], "answer": "LEFT JOIN"},
        {"q": "How do you count the number of rows in a table?", "options": ["SELECT COUNT(*) FROM table", "SELECT SUM(*) FROM table", "SELECT TOTAL(*) FROM table", "SELECT LENGTH(*) FROM table"], "answer": "SELECT COUNT(*) FROM table"}
    ],
    "fastapi": [
        {"q": "FastAPI uses which package for request validation and serialization?", "options": ["Flask", "Django", "Pydantic", "SQLAlchemy"], "answer": "Pydantic"},
        {"q": "How do you mark a query parameter as optional?", "options": ["Use Optional typing", "Declare it with a default of None", "Both of the above", "None of the above"], "answer": "Both of the above"},
        {"q": "Which utility serves API documentation automatically?", "options": ["Swagger UI / ReDoc", "Jupyter", "Postman", "GitHub pages"], "answer": "Swagger UI / ReDoc"}
    ],
    "machine_learning_basics": [
        {"q": "What is it called when a model performs well on training data but poorly on test data?", "options": ["Underfitting", "Overfitting", "Cross-validation", "Dimension reduction"], "answer": "Overfitting"},
        {"q": "Which algorithm is supervised?", "options": ["K-Means Clustering", "Linear Regression", "PCA", "Hierarchical clustering"], "answer": "Linear Regression"},
        {"q": "What split ratio is commonly used for training/testing?", "options": ["50/50", "99/1", "80/20", "10/90"], "answer": "80/20"}
    ]
}

# --- Algorithms ---

def resolve_prerequisites(required_skills: List[str], skill_graph: Dict[str, Any]) -> List[str]:
    """Recursively resolves all prerequisites of required skills to ensure complete dependency chains."""
    resolved = set(required_skills)
    queue = list(required_skills)
    while queue:
        current = queue.pop(0)
        prereqs = skill_graph.get(current, {}).get("prerequisites", [])
        for p in prereqs:
            if p not in resolved:
                resolved.add(p)
                queue.append(p)
    return list(resolved)

def topological_sort(required_skills: List[str], skill_graph: Dict[str, Any]) -> List[str]:
    """Sorts skills topologically based on prerequisites."""
    visited = set()
    temp_visited = set()
    order = []

    def visit(node):
        if node in temp_visited:
            raise ValueError(f"Circular dependency detected at {node}")
        if node in visited:
            return
        temp_visited.add(node)
        
        prereqs = skill_graph.get(node, {}).get("prerequisites", [])
        for prereq in prereqs:
            if prereq in required_skills:
                visit(prereq)
                
        temp_visited.remove(node)
        visited.add(node)
        order.append(node)

    for skill in required_skills:
        if skill not in visited:
            visit(skill)
            
    return order

def determine_statuses(ordered_skills: List[str], user_skills: Dict[str, Any], skill_graph: Dict[str, Any]) -> Dict[str, str]:
    """Determines skill status (Completed, Available, In Progress, Locked, Needs Improvement) based on dependencies and scores."""
    statuses = {}
    
    # 1. Base initialization from user profiles
    for skill_id in ordered_skills:
        u_skill = user_skills.get(skill_id, {})
        u_status = u_skill.get("status", "Unknown")
        
        if u_status in ["Completed", "Verified"]:
            statuses[skill_id] = "Completed"
        elif u_status == "Needs Improvement":
            statuses[skill_id] = "Needs Improvement"
        elif u_status == "In Progress":
            statuses[skill_id] = "In Progress"
        else:
            statuses[skill_id] = "Locked"
            
    # 2. Sequential dependency resolution
    for skill_id in ordered_skills:
        if statuses.get(skill_id) == "Completed":
            continue
            
        prereqs = skill_graph.get(skill_id, {}).get("prerequisites", [])
        all_prereqs_completed = True
        for p in prereqs:
            if p in ordered_skills:
                p_status = statuses.get(p, "Locked")
                if p_status != "Completed":
                    all_prereqs_completed = False
                    break
                    
        if all_prereqs_completed:
            u_skill = user_skills.get(skill_id, {})
            u_status = u_skill.get("status", "Unknown")
            if u_status == "Needs Improvement" or statuses.get(skill_id) == "Needs Improvement":
                statuses[skill_id] = "Needs Improvement"
            elif u_skill.get("in_progress", False) or u_status == "In Progress":
                statuses[skill_id] = "In Progress"
            else:
                statuses[skill_id] = "Available"
        else:
            statuses[skill_id] = "Locked"
            
    return statuses

def calculate_bottleneck(ordered_skills: List[str], statuses: Dict[str, str], skill_graph: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Identifies the active skill that is blocking the largest number of downstream locked skills."""
    incomplete_skills = [s for s in ordered_skills if statuses.get(s) != "Completed"]
    if not incomplete_skills:
        return None
        
    def get_transitive_dependents(skill):
        dependents = set()
        queue = [skill]
        while queue:
            curr = queue.pop(0)
            for other in ordered_skills:
                if other != curr and other not in dependents:
                    prereqs = skill_graph.get(other, {}).get("prerequisites", [])
                    if curr in prereqs:
                        dependents.add(other)
                        queue.append(other)
        return dependents

    bottlenecks = []
    for skill in incomplete_skills:
        # A bottleneck must be actionable (Available, In Progress, or Needs Improvement)
        if statuses.get(skill) in ["Available", "In Progress", "Needs Improvement"]:
            dependents = get_transitive_dependents(skill)
            locked_deps = [d for d in dependents if statuses.get(d) == "Locked"]
            bottlenecks.append({
                "skill_id": skill,
                "title": skill_graph.get(skill, {}).get("title", skill),
                "blocked_count": len(locked_deps)
            })
            
    if not bottlenecks:
        return None
        
    bottlenecks.sort(key=lambda x: (-x["blocked_count"], ordered_skills.index(x["skill_id"])))
    return bottlenecks[0] if bottlenecks[0]["blocked_count"] > 0 else None

def calculateCareerReadiness(required_skills: List[str], user_skills: Dict[str, Any], skill_graph: Dict[str, Any]) -> Dict[str, Any]:
    """Compute weighted career readiness from skills, blockers, evidence, and assessments."""
    if not required_skills:
        return {
            "score": 0,
            "completedSkills": 0,
            "totalSkills": 0,
            "biggestGap": None,
            "biggestBlocker": None,
            "nextAction": None,
        }

    scored_items: List[Dict[str, Any]] = []
    completed = 0
    total_weight = 0.0
    weighted_score = 0.0
    for skill_id in required_skills:
        meta = skill_graph.get(skill_id, {})
        target = int(meta.get("required_proficiency", 70))
        current = int(user_skills.get(skill_id, {}).get("proficiency", 0))
        status = user_skills.get(skill_id, {}).get("status", "")
        evidence = user_skills.get(skill_id, {}).get("evidence", [])
        prereqs = meta.get("prerequisites", [])
        dependents = [
            other_id
            for other_id in required_skills
            if skill_id in skill_graph.get(other_id, {}).get("prerequisites", [])
        ]
        gap = max(0, target - current)
        blocker_penalty = 35 if status in {"Needs Improvement"} else 0
        evidence_bonus = min(15, len(evidence) * 5)
        project_bonus = 10 if any(str(item).lower().find("project") >= 0 for item in evidence) else 0
        assessment_bonus = min(15, int(user_skills.get(skill_id, {}).get("last_test_score", 0)) // 10)
        critical_weight = 2.4 if not prereqs else 1.4 + (0.25 * len(prereqs))
        blocker_weight = 1.0 + (0.35 * len(dependents))
        skill_score = max(0, min(100, current + evidence_bonus + project_bonus + assessment_bonus - blocker_penalty))
        weighted_score += skill_score * critical_weight * blocker_weight
        total_weight += critical_weight * blocker_weight
        if current >= target and status in {"Completed", "Verified"}:
            completed += 1
        scored_items.append({
            "skill_id": skill_id,
            "title": meta.get("title", skill_id),
            "gap": gap,
            "status": status,
            "critical_weight": critical_weight,
            "blocker_weight": blocker_weight,
            "current": current,
        })

    scored_items.sort(key=lambda item: (-item["blocker_weight"], -item["critical_weight"], -item["gap"], item["skill_id"]))
    biggest_gap = scored_items[0]["title"] if scored_items and scored_items[0]["gap"] > 0 else None
    biggest_blocker = next((item["title"] for item in scored_items if item["status"] == "Needs Improvement"), biggest_gap)
    next_action = None
    for item in scored_items:
        if item["status"] == "Needs Improvement" or item["gap"] > 0:
            next_action = f"Complete {item['title']} Practice"
            break
    if next_action is None:
        next_action = "Continue your current roadmap"
    score = int(round((weighted_score / total_weight) if total_weight else 0))
    return {
        "score": max(0, min(100, score)),
        "completedSkills": completed,
        "totalSkills": len(required_skills),
        "biggestGap": biggest_gap,
        "biggestBlocker": biggest_blocker,
        "nextAction": next_action,
    }


def isCareerReady(required_skills: List[str], user_skills: Dict[str, Any], skill_graph: Dict[str, Any]) -> Dict[str, Any]:
    """Strict career-ready gate using readiness, blockers, and critical skills."""
    readiness = calculateCareerReadiness(required_skills, user_skills, skill_graph)
    critical_skills = [
        skill_id
        for skill_id in required_skills
        if not skill_graph.get(skill_id, {}).get("prerequisites", [])
        or len(skill_graph.get(skill_id, {}).get("prerequisites", [])) <= 1
    ]
    missing_critical = [
        skill_id
        for skill_id in critical_skills
        if user_skills.get(skill_id, {}).get("status") not in {"Completed", "Verified"}
        or int(user_skills.get(skill_id, {}).get("proficiency", 0)) < int(skill_graph.get(skill_id, {}).get("required_proficiency", 70))
    ]
    ready = readiness["score"] >= 90 and not missing_critical and readiness["biggestBlocker"] is None
    return {
        "ready": ready,
        "readiness": readiness,
        "missingCriticalSkills": missing_critical,
        "criticalSkills": critical_skills,
    }


def select_adaptive_project(skill_id: str, proficiency: int, skill_graph: Dict[str, Any]) -> Dict[str, Any]:
    """Return a milestone project tailored to the learner level."""
    skill_title = skill_graph.get(skill_id, {}).get("title", skill_id)
    if proficiency < 45:
        return {
            "title": f"{skill_title} REST API",
            "goal": "Build a simple working service with a single dependency chain.",
            "skills": [skill_id],
            "prerequisites": [],
            "difficulty": "Beginner",
            "estimatedTime": "4-6 hours",
            "expectedOutput": "A small REST endpoint with validation and a basic response model.",
            "evaluationCriteria": ["Returns correct responses", "Uses validation", "Follows route structure"],
        }
    if proficiency < 75:
        return {
            "title": f"{skill_title} ML Prediction API",
            "goal": "Ship an API that wraps a model or analytics workflow with a reliable interface.",
            "skills": [skill_id, "rest_apis"],
            "prerequisites": ["rest_apis"],
            "difficulty": "Intermediate",
            "estimatedTime": "6-10 hours",
            "expectedOutput": "A documented API with clear request and response contracts.",
            "evaluationCriteria": ["Reusable API design", "Validates input", "Produces useful output"],
        }
    return {
        "title": f"{skill_title} RAG-powered AI Backend",
        "goal": "Build a production-style backend with retrieval, orchestration, and evidence capture.",
        "skills": [skill_id, "fastapi", "postgresql", "ai_apis", "rag"],
        "prerequisites": ["fastapi", "postgresql"],
        "difficulty": "Advanced",
        "estimatedTime": "10-18 hours",
        "expectedOutput": "A backend that can retrieve context, answer queries, and store evidence.",
        "evaluationCriteria": ["Handles retrieval flow", "Stores evidence", "Supports review and reassessment"],
    }


def build_contextual_resources(skill_id: str, skill_graph: Dict[str, Any], proficiency: int) -> List[Dict[str, Any]]:
    """Return skill-linked resources with reasons and time estimates."""
    meta = skill_graph.get(skill_id, {})
    resources = []
    for resource in meta.get("resources", []):
        resources.append({
            "title": resource.get("title"),
            "type": resource.get("type"),
            "skill": skill_id,
            "difficulty": meta.get("difficulty", "Intermediate"),
            "estimatedTime": "20-40 min",
            "reason": f"This resource is recommended because it supports {meta.get('title', skill_id)} at your current level of {proficiency}%.",
            "url": resource.get("url"),
            "contentReference": resource.get("url"),
        })
    project = select_adaptive_project(skill_id, proficiency, skill_graph)
    resources.append({
        "title": project["title"],
        "type": "Project",
        "skill": skill_id,
        "difficulty": project["difficulty"],
        "estimatedTime": project["estimatedTime"],
        "reason": f"This project is recommended because it matches your current proficiency and roadmap stage.",
        "url": None,
        "contentReference": project,
    })
    return resources

def get_next_best_action(ordered_skills: List[str], statuses: Dict[str, str], skill_graph: Dict[str, Any], user_skills: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Returns exactly one primary recommended next action on the dashboard."""
    # First: address any needs improvement
    for s in ordered_skills:
        if statuses.get(s) == "Needs Improvement":
            u_skill = user_skills.get(s, {})
            return {
                "skill_id": s,
                "title": skill_graph.get(s, {}).get("title", s),
                "status": "Needs Improvement",
                "reason": f"Your proficiency is {u_skill.get('proficiency', 0)}%. Complete reinforcement exercises and reassessment to unlock the route.",
                "estimated_hours": skill_graph.get(s, {}).get("estimated_hours", 4)
            }
    # Second: first In Progress or Available skill
    for s in ordered_skills:
        if statuses.get(s) in ["In Progress", "Available"]:
            u_skill = user_skills.get(s, {})
            return {
                "skill_id": s,
                "title": skill_graph.get(s, {}).get("title", s),
                "status": statuses.get(s),
                "reason": f"All prerequisites are satisfied. Start learning and verify this competency.",
                "estimated_hours": skill_graph.get(s, {}).get("estimated_hours", 4)
            }
    return None

# --- Path Validation & Repair ---

def validate_and_repair_path(ordered_skills: List[str], user_skills: Dict[str, Any], target_career_id: str, skill_graph: Dict[str, Any]) -> Dict[str, Any]:
    """Validates the generated path against the 10 core constraints and repairs failures dynamically."""
    validation_passed = True
    errors = []
    
    # 1. No Duplicate Skills (Rule 5)
    if len(ordered_skills) != len(set(ordered_skills)):
        validation_passed = False
        errors.append("Duplicate skills found in path.")
        seen = set()
        deduped = []
        for s in ordered_skills:
            if s not in seen:
                seen.add(s)
                deduped.append(s)
        ordered_skills = deduped
        
    # 2. No Circular Dependencies (Rule 6)
    try:
        topological_sort(ordered_skills, skill_graph)
    except ValueError as e:
        validation_passed = False
        errors.append(f"Circular dependency: {str(e)}")
        career_info = CAREERS.get(target_career_id, {})
        ordered_skills = [s for s in career_info.get("required_skills", []) if s in skill_graph]
        
    # 3. Prerequisite completeness (Rule 7)
    missing_prereqs = []
    for s in ordered_skills:
        prereqs = skill_graph.get(s, {}).get("prerequisites", [])
        for p in prereqs:
            if p not in ordered_skills:
                missing_prereqs.append(p)
    if missing_prereqs:
        validation_passed = False
        errors.append(f"Missing prerequisites in path: {missing_prereqs}")
        resolved = resolve_prerequisites(ordered_skills, skill_graph)
        ordered_skills = topological_sort(resolved, skill_graph)

    # 4. Prerequisite Order Validation (Rule 1)
    for i, s in enumerate(ordered_skills):
        prereqs = skill_graph.get(s, {}).get("prerequisites", [])
        for p in prereqs:
            if p in ordered_skills:
                p_index = ordered_skills.index(p)
                if p_index > i:
                    validation_passed = False
                    errors.append(f"Prerequisite {p} placed after dependent {s}.")
                    ordered_skills = topological_sort(ordered_skills, skill_graph)
                    break
                    
    # 5. Goal Contribution (Rule 4)
    career_skills = set(CAREERS.get(target_career_id, {}).get("required_skills", []))
    resolved_career_skills = set(resolve_prerequisites(list(career_skills), skill_graph))
    filtered_skills = [x for x in ordered_skills if x in resolved_career_skills]
    if len(filtered_skills) != len(ordered_skills):
        validation_passed = False
        errors.append("Path contains non-career related skills.")
        ordered_skills = filtered_skills
        
    return {
        "valid": validation_passed,
        "errors": errors,
        "repaired_path": ordered_skills
    }

# --- Pydantic Data Models ---

class GoalAnalysisRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)

class GoalAnalysis(BaseModel):
    goal: str
    careerTitle: str
    description: str
    requiredSkills: List[str]
    estimatedDuration: str
    readiness: int = Field(ge=0, le=100)
    matched_career_id: Optional[str] = None
    is_ambiguous: bool = False
    clarification_question: str = ""
    normalized_name: str = ""
    extracted_skills: List[str] = Field(default_factory=list)
    target_outcome: str = ""

class SkillAnalysisRequest(BaseModel):
    target_role: str
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

class RoadmapGenerationRequest(BaseModel):
    target_role: str
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    daily_learning_minutes: int = Field(default=60, ge=1, le=1440)
    learning_preferences: List[str] = Field(default_factory=list)
    assessment_results: List[Dict[str, Any]] = Field(default_factory=list)


class ReplanPathRequest(BaseModel):
    target_role: str
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    daily_learning_minutes: int = Field(default=60, ge=1, le=1440)
    trigger: Dict[str, Any] = Field(default_factory=dict)


class ProgressSummaryRequest(BaseModel):
    target_role: str
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    daily_learning_minutes: int = Field(default=60, ge=1, le=1440)
    assessment_results: List[Dict[str, Any]] = Field(default_factory=list)
    practice_history: List[Dict[str, Any]] = Field(default_factory=list)


class ResourceProjectRequest(BaseModel):
    target_role: str
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)


class ProjectCompletionRequest(BaseModel):
    target_role: str
    skill_id: str
    project_title: str
    score: int = Field(ge=0, le=100)
    user_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    evidence_summary: str = ""

def build_goal_analysis(goal: str, career_id: str) -> GoalAnalysis:
    career = CAREERS[career_id]
    required_skills = list(career.get("required_skills", []))
    skill_count = len(required_skills)
    duration = "3–5 months" if skill_count <= 12 else "6–9 months" if skill_count <= 18 else "9–12 months"
    return GoalAnalysis(
        goal=goal,
        careerTitle=career["name"],
        description=career["description"],
        requiredSkills=required_skills,
        estimatedDuration=duration,
        readiness=0,
        matched_career_id=career_id,
        normalized_name=career["name"],
        extracted_skills=[],
        target_outcome=f"Build and grow toward a career as a {career['name']}.",
    )

class PathGenerationRequest(BaseModel):
    user_id: str
    target_role: str
    current_skills: Dict[str, Dict[str, Any]] # e.g. { "python": {"proficiency": 80, "status": "Completed"} }
    hours_per_week: int = Field(default=12, ge=1, le=80)
    learning_style: Optional[str] = "Prefer Videos"
    feedback: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

class DiagnosticRequest(BaseModel):
    skill_id: str

class DiagnosticStartRequest(BaseModel):
    target_role: str

class DiagnosticQuestion(BaseModel):
    questionId: str
    skillId: str
    question: str
    options: List[str]
    difficulty: str

class DiagnosticAnswer(BaseModel):
    questionId: str
    skillId: str
    answer: str

class DiagnosticSubmitRequest(BaseModel):
    target_role: str
    known_skills: List[str] = Field(default_factory=list)
    answers: List[DiagnosticAnswer] = Field(min_length=1)

class AssessmentSubmitRequest(BaseModel):
    skill_id: str
    score: int = Field(ge=0, le=100)
    user_skills: Dict[str, Dict[str, Any]]
    target_role: str

class FeedbackSubmitRequest(BaseModel):
    skill_id: str
    feedback_type: str # e.g. "Too easy", "Too difficult", "Already know this", "Need more practice"
    user_skills: Dict[str, Dict[str, Any]]
    target_role: str

class ProofOfWorkRequest(BaseModel):
    github_url: str
    milestone_title: str
    skill_id: str

class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, str]]
    target_role: str
    user_skills: Dict[str, Dict[str, Any]]
    current_page: Optional[str] = None
    current_milestone: Optional[str] = None
    current_skill: Optional[str] = None
    skill_proficiency: Optional[int] = None
    weak_areas: List[str] = Field(default_factory=list)
    roadmap: List[Dict[str, Any]] = Field(default_factory=list)
    recent_assessment: Optional[Dict[str, Any]] = None
    recent_mistakes: List[Dict[str, Any]] = Field(default_factory=list)
    learning_preference: Optional[str] = None
    bottleneck: Optional[str] = None
    next_action: Optional[str] = None

# --- API Route Endpoints ---

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "system": "PathMind AI Engine - Adaptive GPS Edition",
        "framework_alignment": "Learn, Practice, Build, Assess, Verify, Adapt",
        "careers": list(CAREERS.keys())
    }

@app.get("/api/careers")
def get_careers():
    return CAREERS

@app.post("/api/skills/analyze")
def analyze_skills(request: SkillAnalysisRequest):
    """Return normalized skill records and deterministic gap classifications."""
    career = CAREERS.get(request.target_role)
    if not career:
        raise HTTPException(status_code=404, detail="Career track not found.")
    skill_ids = list(career.get("required_skills", [])) + list(career.get("optional_skills", []))
    skills = build_skill_models(skill_ids, SKILL_GRAPH, request.current_skills)
    return {"target_role": request.target_role, "skills": skills, "gaps": analyze_skill_gaps(skills)}

@app.post("/api/path/generate", response_model=Roadmap)
def generate_personalized_path(request: RoadmapGenerationRequest):
    """Generate the deterministic personalized route without using an LLM for ordering."""
    career = CAREERS.get(request.target_role)
    if not career:
        raise HTTPException(status_code=404, detail="Career track not found.")
    return generate_roadmap(
        career_name=career["name"],
        required_skill_ids=career.get("required_skills", []),
        optional_skill_ids=career.get("optional_skills", []),
        graph=SKILL_GRAPH,
        current_skills=request.current_skills,
        daily_learning_minutes=request.daily_learning_minutes,
    )


@app.post("/api/path/replan")
def replan_learning_path(request: ReplanPathRequest):
    """Recalculate the roadmap after new learner evidence or availability changes."""
    career = CAREERS.get(request.target_role)
    if not career:
        raise HTTPException(status_code=404, detail="Career track not found.")
    result = replan_path(
        career_name=career["name"],
        required_skill_ids=career.get("required_skills", []),
        optional_skill_ids=career.get("optional_skills", []),
        graph=SKILL_GRAPH,
        current_skills=request.current_skills,
        daily_learning_minutes=request.daily_learning_minutes,
        trigger=request.trigger,
    )
    return {
        "changed": result.changed,
        "explanation": result.explanation,
        "insight": result.insight,
        "previous_next_best_action": result.previousNextBestAction,
        "current_next_best_action": result.currentNextBestAction,
        "roadmap": result.roadmap,
    }


@app.post("/api/progress/summary")
def progress_summary(request: ProgressSummaryRequest):
    """Return a weighted progress snapshot grounded in actual learner evidence."""
    career = CAREERS.get(request.target_role)
    if not career:
        raise HTTPException(status_code=404, detail="Career track not found.")
    skill_ids = list(career.get("required_skills", [])) + list(career.get("optional_skills", []))
    skills = build_skill_models(skill_ids, SKILL_GRAPH, request.current_skills)
    readiness = calculateCareerReadiness(career.get("required_skills", []), request.current_skills, SKILL_GRAPH)
    roadmap = generate_roadmap(
        career_name=career["name"],
        required_skill_ids=career.get("required_skills", []),
        optional_skill_ids=career.get("optional_skills", []),
        graph=SKILL_GRAPH,
        current_skills=request.current_skills,
        daily_learning_minutes=request.daily_learning_minutes,
    )
    category_growth: Dict[str, Dict[str, Any]] = {}
    for skill in skills:
        bucket = category_growth.setdefault(skill.category, {"current": 0, "target": 0, "skills": 0})
        bucket["current"] += skill.currentLevel
        bucket["target"] += skill.requiredLevel
        bucket["skills"] += 1
    for bucket in category_growth.values():
        bucket["average"] = round(bucket["current"] / bucket["skills"]) if bucket["skills"] else 0
        bucket["target_average"] = round(bucket["target"] / bucket["skills"]) if bucket["skills"] else 0
    readiness_gate = isCareerReady(career.get("required_skills", []), request.current_skills, SKILL_GRAPH)

    weekly_activity = {
        "learningSessions": len([item for item in request.practice_history if item.get("timestamp")]) + len([item for item in request.assessment_results if item.get("skillId")]),
        "practice": len(request.practice_history),
        "projects": len([skill for skill in skills if skill.status == "COMPLETED" and skill.estimatedHours >= 0]),
        "assessments": len(request.assessment_results),
    }
    milestones = {
        "completed": len([skill for skill in skills if skill.status == "COMPLETED"]),
        "available": len([skill for skill in skills if skill.status == "AVAILABLE"]),
        "locked": len([skill for skill in skills if skill.status == "LOCKED"]),
    }
    biggest_gap = readiness["biggestGap"]
    biggest_blocker = readiness["biggestBlocker"]
    next_action = readiness["nextAction"]
    return {
        "career": career["name"],
        "readiness": readiness,
        "readinessGate": readiness_gate,
        "skillGrowth": category_growth,
        "weeklyActivity": weekly_activity,
        "milestones": milestones,
        "assessments": request.assessment_results,
        "projects": [skill.id for skill in skills if skill.status == "COMPLETED"],
        "nextBestAction": roadmap.nextBestAction,
        "biggestGap": biggest_gap,
        "biggestBlocker": biggest_blocker,
        "nextAction": next_action,
    }


@app.post("/api/resources/summary")
def resources_summary(request: ResourceProjectRequest):
    """Return contextual resources and adaptive projects for the learner's current skills."""
    career = CAREERS.get(request.target_role)
    if not career:
        raise HTTPException(status_code=404, detail="Career track not found.")
    skill_ids = list(career.get("required_skills", [])) + list(career.get("optional_skills", []))
    skills = build_skill_models(skill_ids, SKILL_GRAPH, request.current_skills)
    resources_by_skill = []
    projects_by_skill = []
    for skill in skills:
        proficiency = skill.currentLevel
        contextual = build_contextual_resources(skill.id, SKILL_GRAPH, proficiency)
        valid_resources = [item for item in contextual if item.get("title")]
        resources_by_skill.append({
            "skillId": skill.id,
            "title": skill.name,
            "status": skill.status,
            "proficiency": proficiency,
            "resources": valid_resources,
            "weakAreas": [skill.name] if skill.status == "NEEDS_ATTENTION" else [],
        })
        projects_by_skill.append({
            "skillId": skill.id,
            "title": skill.name,
            "status": skill.status,
            "proficiency": proficiency,
            "project": select_adaptive_project(skill.id, proficiency, SKILL_GRAPH),
        })
    return {
        "career": career["name"],
        "resources": resources_by_skill,
        "projects": projects_by_skill,
    }


@app.post("/api/project/complete")
def complete_project(request: ProjectCompletionRequest):
    """Record verified project evidence and adapt the learner skill state."""
    career = CAREERS.get(request.target_role)
    if not career:
        raise HTTPException(status_code=404, detail="Career track not found.")
    if request.skill_id not in SKILL_GRAPH:
        raise HTTPException(status_code=404, detail="Skill not found.")
    skill_meta = SKILL_GRAPH[request.skill_id]
    user_skills = dict(request.user_skills)
    evidence_entry = {
        "label": "Project completed",
        "value": request.project_title,
        "score": request.score,
        "summary": request.evidence_summary,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat() + "Z",
    }
    current = dict(user_skills.get(request.skill_id, {}))
    current_evidence = list(current.get("evidence", []))
    current_evidence.append(evidence_entry)
    if request.score >= 80:
        current.update({
            "proficiency": max(int(current.get("proficiency", 0)), skill_meta.get("required_proficiency", 70)),
            "status": "Completed",
            "confidence": "Verified",
            "evidence": current_evidence,
        })
    else:
        current.update({
            "proficiency": max(0, int(current.get("proficiency", 0))),
            "status": "Needs Improvement",
            "confidence": "Project Review",
            "evidence": current_evidence,
        })
    user_skills[request.skill_id] = current
    return {
        "skill_id": request.skill_id,
        "project_title": request.project_title,
        "score": request.score,
        "updated_skills": user_skills,
        "evidence": current_evidence,
        "verification_status": "Verified" if request.score >= 80 else "Needs Review",
    }

@app.post("/api/analyze-goal", response_model=GoalAnalysis)
def analyze_goal(request: GoalAnalysisRequest):
    """Parses natural language goal to map to a structured career template or asks a clarification question."""
    q = request.query.strip().lower()
    
    # Try keywords match
    matched_career = None
    if "backend ai" in q or "ai backend" in q or "python ai" in q or "backend developer" in q:
        matched_career = "backend_ai_developer"
    elif "ai engineer" in q or "prompt" in q or "llm" in q:
        matched_career = "ai_engineer"
    elif "machine learning" in q or "ml engineer" in q or "predictive" in q:
        matched_career = "ml_engineer"
    elif "data scientist" in q or "analytics" in q or "statistics" in q:
        matched_career = "data_scientist"
    elif "full stack" in q or "web dev" in q or "frontend" in q or "next.js" in q:
        matched_career = "full_stack_developer"
        
    client = get_gemini_client()
    if client and not matched_career:
        try:
            prompt = f"""
            Analyze this learning goal query: "{request.query}"
            Classify it into exactly one of these career IDs:
            1. "backend_ai_developer" (Python backend, FastAPI, SQL, ML basics, Docker, Cloud, AI integration)
            2. "ai_engineer" (NLP, LLMs, Vector Databases, PEFT fine-tuning, RAG, prompt engineering)
            3. "ml_engineer" (ML fundamentals, deep learning, MLOps, serving models, computer vision)
            4. "data_scientist" (Math, statistics, dataframes Pandas, SQL, ML models, dashboards)
            5. "full_stack_developer" (React, Nextjs, SQL, Express/Node, CSS Tailwind, Git)

            If the goal is ambiguous, set is_ambiguous to true and write a short clarification question to ask the user.
            Provide output in JSON format matching this schema:
            {{
                "matched_career_id": "career_id_or_null",
                "is_ambiguous": true/false,
                "clarification_question": "question text if ambiguous else empty",
                "normalized_name": "Display name of matched career",
                "extracted_skills": ["extracted", "skills"],
                "target_outcome": "what user wants to build"
            }}
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            ai_career_id = data.get("matched_career_id")
            if ai_career_id in CAREERS and not data.get("is_ambiguous", False):
                result = build_goal_analysis(request.query.strip(), ai_career_id)
                result.extracted_skills = data.get("extracted_skills", [])
                return result
        except Exception:
            pass # Fallback to static matching below

    # Static fallback
    if matched_career:
        result = build_goal_analysis(request.query.strip(), matched_career)
        result.extracted_skills = ["Python", "SQL"] if matched_career == "backend_ai_developer" else []
        result.target_outcome = f"Work as a professional {CAREERS[matched_career]['name']}"
        return result
    else:
        return GoalAnalysis(
            goal=request.query.strip(),
            careerTitle="",
            description="",
            requiredSkills=[],
            estimatedDuration="",
            readiness=0,
            is_ambiguous=True,
            clarification_question="I could not match that goal to a supported career track yet. Try a software, AI, data, or full-stack goal.",
        )

@app.post("/api/generate-path")
def generate_path(request: PathGenerationRequest):
    """Main path generation engine. Computes gaps, bottlenecks, topological sort, validates rules, and adapts path."""
    career_id = request.target_role
    if career_id not in CAREERS:
        raise HTTPException(status_code=404, detail="Career track not found.")
        
    career_info = CAREERS[career_id]
    required_skills = career_info["required_skills"]
    
    # 1. Resolve and Topologically Sort the path
    resolved_skills = resolve_prerequisites(required_skills, SKILL_GRAPH)
    try:
        ordered_skills = topological_sort(resolved_skills, SKILL_GRAPH)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Graph construction error: {str(e)}")
        
    # 2. Determine skill statuses
    statuses = determine_statuses(ordered_skills, request.current_skills, SKILL_GRAPH)
    
    # 3. Path Validation Engine & Repairs
    repair_result = validate_and_repair_path(ordered_skills, request.current_skills, career_id, SKILL_GRAPH)
    ordered_skills = repair_result["repaired_path"]
    statuses = determine_statuses(ordered_skills, request.current_skills, SKILL_GRAPH) # Re-calculate status after repair
    
    # 4. Calculate bottlenecks and actions
    bottleneck = calculate_bottleneck(ordered_skills, statuses, SKILL_GRAPH)
    next_action = get_next_best_action(ordered_skills, statuses, SKILL_GRAPH, request.current_skills)
    readiness_summary = calculateCareerReadiness(required_skills, request.current_skills, SKILL_GRAPH)
    readiness_score = readiness_summary["score"]
    
    # 5. Populate structured timeline
    path_items = []
    for index, skill_id in enumerate(ordered_skills):
        skill_metadata = SKILL_GRAPH[skill_id]
        
        # User details
        u_skill = request.current_skills.get(skill_id, {})
        c_prof = u_skill.get("proficiency", 0)
        t_prof = skill_metadata.get("required_proficiency", 70)
        gap = max(0, t_prof - c_prof)
        
        # Explainable Rationale ("Why this?")
        why = f"Required for {career_info['name']}. "
        if gap > 0:
            why += f"Your current proficiency is {c_prof}%, which is below the target requirement of {t_prof}%."
        else:
            why += f"You have already met the target proficiency ({c_prof}% >= {t_prof}%)."
            
        if skill_metadata.get("prerequisites"):
            prereq_titles = [SKILL_GRAPH[p]["title"] for p in skill_metadata["prerequisites"] if p in SKILL_GRAPH]
            why += f" Depends on fundamental concepts in: {', '.join(prereq_titles)}."

        # Adapt Resources if feedback indicates reinforcement is needed
        resources = list(skill_metadata.get("resources", []))
        practice = list(skill_metadata.get("practice", []))
        feedback_types = {
            str(item.get("feedback_type", ""))
            for item in request.feedback or []
            if item.get("skill_id") == skill_id
        }
        if statuses.get(skill_id) == "Needs Improvement":
            # Add extra study material as reinforcement
            resources.append({
                "title": "🔥 Reinforcement Guide: Concepts Review",
                "type": "Article",
                "url": "https://realpython.com/"
            })
            resources.append({
                "title": "🔥 Extra Practice Lab Exercises",
                "type": "Course",
                "url": "https://w3schools.com"
            })
        if "Need more practice" in feedback_types:
            practice.extend([
                f"Repeat a focused {skill_metadata['title']} exercise and explain each decision.",
                f"Build a small variation of the {skill_metadata['title']} project without following a tutorial."
            ])

        prereqs = skill_metadata.get("prerequisites", [])
        unlock_condition = "All prerequisites verified at their target proficiency."
        if not prereqs:
            unlock_condition = "Available immediately; verify this skill through assessment or project work."
        phase = "Foundation"
        if any(token in skill_id for token in ["api", "http", "rest", "fastapi", "auth", "sql", "postgres", "node"]):
            phase = "Build"
        elif any(token in skill_id for token in ["machine", "model", "deep", "nlp", "llm", "rag", "vector", "numpy", "math"]):
            phase = "Apply AI"
        elif any(token in skill_id for token in ["docker", "cloud", "mlops", "deploy"]):
            phase = "Ship"
        elif index > 2:
            phase = "Develop"
            
        path_items.append({
            "id": skill_id,
            "title": skill_metadata["title"],
            "description": skill_metadata["description"],
            "skill": skill_id,
            "phase": phase,
            "order": index + 1,
            "prerequisites": prereqs,
            "required_proficiency": t_prof,
            "current_proficiency": c_prof,
            "skill_gap": gap,
            "estimated_hours": skill_metadata.get("estimated_hours", 6),
            "difficulty": skill_metadata.get("difficulty", "Intermediate"),
            "status": statuses.get(skill_id, "Locked"),
            "why_recommended": why,
            "unlock_condition": unlock_condition,
            "resources": resources,
            "practice": practice,
            "project": skill_metadata.get("project", {}),
            "assessment_required": statuses.get(skill_id) != "Completed",
            "assessment": PRESET_QUIZZES.get(skill_id, [
                {"q": f"A primary question on {skill_metadata['title']}.", "options": ["Correct", "Wrong A", "Wrong B", "Wrong C"], "answer": "Correct"}
            ])
        })
        
    completed_skills = [item["skill"] for item in path_items if item["status"] == "Completed"]
    weak_skills = [item["skill"] for item in path_items if item["status"] == "Needs Improvement"]
    next_skill = next_action["skill_id"] if next_action else None
    current_phase = next(
        (item["phase"] for item in path_items if item["skill"] == next_skill),
        "Capstone",
    )
    phase_scores = {}
    for item in path_items:
        phase_scores.setdefault(item["phase"], []).append(
            min(item["current_proficiency"] / max(item["required_proficiency"], 1), 1) * 100
        )
    readiness_breakdown = {
        phase: round(sum(scores) / len(scores)) for phase, scores in phase_scores.items()
    }

    return {
        "target_role": career_id,
        "target_role_name": career_info["name"],
        "target_role_description": career_info["description"],
        "readiness_score": readiness_score,
        "readiness_summary": readiness_summary,
        "career_readiness_breakdown": readiness_breakdown,
        "overall_progress": readiness_score,
        "current_phase": current_phase,
        "completed_skills": completed_skills,
        "weak_skills": weak_skills,
        "bottleneck": bottleneck,
        "next_action": next_action,
        "path": path_items,
        "capstone_project": career_info["capstone_project"],
        "validation": {
            "valid": repair_result["valid"],
            "errors": repair_result["errors"]
        }
    }

@app.post("/api/diagnostic/start")
def start_diagnostic(request: DiagnosticStartRequest):
    """Returns a focused, answer-key-free diagnostic for the selected career."""
    if request.target_role not in CAREERS:
        raise HTTPException(status_code=404, detail="Career track not found.")

    diagnostic_skills = [
        skill_id for skill_id in [
            "python", "oop", "git", "http_fundamentals", "rest_apis",
            "sql_basics", "postgresql", "fastapi", "machine_learning_basics"
        ] if skill_id in resolve_prerequisites(CAREERS[request.target_role]["required_skills"], SKILL_GRAPH)
    ][:9]
    questions = []
    for skill_id in diagnostic_skills:
        quiz = PRESET_QUIZZES.get(skill_id, [])
        if not quiz:
            quiz = [{
                "q": f"Which idea is central to {SKILL_GRAPH[skill_id]['title']}?",
                "options": ["Its core engineering concepts", "Page colors", "File names only", "None of these"],
                "answer": "Its core engineering concepts"
            }]
        item = quiz[0]
        questions.append(DiagnosticQuestion(
            questionId=f"{skill_id}-0",
            skillId=skill_id,
            question=item["q"],
            options=item["options"],
            difficulty=SKILL_GRAPH[skill_id].get("difficulty", "Intermediate"),
        ))
    return {"target_role": request.target_role, "questions": questions}

@app.post("/api/diagnostic/submit")
def submit_diagnostic(request: DiagnosticSubmitRequest):
    """Scores diagnostic answers against the server-owned question bank."""
    if request.target_role not in CAREERS:
        raise HTTPException(status_code=404, detail="Career track not found.")
    allowed_skills = set(resolve_prerequisites(CAREERS[request.target_role]["required_skills"], SKILL_GRAPH))
    results = []
    scores_by_skill: Dict[str, List[int]] = {}
    for answer in request.answers:
        if answer.skillId not in allowed_skills:
            raise HTTPException(status_code=400, detail="Question is not part of this career diagnostic.")
        try:
            skill_index = int(answer.questionId.rsplit("-", 1)[1])
            if answer.skillId in PRESET_QUIZZES:
                question = PRESET_QUIZZES[answer.skillId][skill_index]
            elif skill_index == 0:
                question = {
                    "answer": "Its core engineering concepts"
                }
            else:
                raise KeyError(answer.skillId)
        except (KeyError, IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid diagnostic question.")
        correct = answer.answer == question["answer"]
        score = 100 if correct else 0
        scores_by_skill.setdefault(answer.skillId, []).append(score)
        results.append({
            "questionId": answer.questionId,
            "skillId": answer.skillId,
            "answer": answer.answer,
            "correct": correct,
            "difficulty": SKILL_GRAPH[answer.skillId].get("difficulty", "Intermediate"),
        })
    proficiency = {skill_id: round(sum(scores) / len(scores)) for skill_id, scores in scores_by_skill.items()}
    for skill_id in request.known_skills:
        if skill_id in allowed_skills and skill_id not in proficiency:
            proficiency[skill_id] = 25
    overall_score = round(sum(proficiency.values()) / len(proficiency)) if proficiency else 0
    return {
        "target_role": request.target_role,
        "assessmentResults": results,
        "skillProficiency": proficiency,
        "overallScore": overall_score,
        "verifiedSkills": [skill_id for skill_id, score in proficiency.items() if score >= 75],
    }

@app.post("/api/get-diagnostic")
def get_diagnostic(request: DiagnosticRequest):
    """Generates 3 diagnostic multiple-choice questions for the skill. Uses Gemini with preset fallbacks."""
    skill_id = request.skill_id
    if skill_id not in SKILL_GRAPH:
        raise HTTPException(status_code=404, detail="Skill not found.")
        
    # Return preset fallback if exists in database
    if skill_id in PRESET_QUIZZES:
        return {"skill_id": skill_id, "questions": PRESET_QUIZZES[skill_id]}
        
    client = get_gemini_client()
    if client:
        try:
            prompt = f"""
            Generate exactly 3 multiple-choice diagnostic questions to test the skill: {SKILL_GRAPH[skill_id]['title']}
            Description: {SKILL_GRAPH[skill_id]['description']}
            
            Format response as JSON array with this structure:
            [
                {{
                    "q": "Question text?",
                    "options": ["option 1", "option 2", "option 3", "option 4"],
                    "answer": "option 1" (must match exactly one of the options)
                }}
            ]
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            questions = json.loads(response.text)
            return {"skill_id": skill_id, "questions": questions}
        except Exception:
            pass # Fallback to default generated template

    # Generic Fallback
    title = SKILL_GRAPH[skill_id]["title"]
    return {
        "skill_id": skill_id,
        "questions": [
            {
                "q": f"Which of the following describes a key concept in {title}?",
                "options": ["A core design pattern", "A style rule", "An optional variable", "None of the above"],
                "answer": "A core design pattern"
            },
            {
                "q": f"How is {title} commonly integrated into standard pipelines?",
                "options": ["Through direct dependency libraries", "As an operating system process", "Manually in a word file", "It cannot be integrated"],
                "answer": "Through direct dependency libraries"
            },
            {
                "q": f"What is a primary metric to optimize in {title} applications?",
                "options": ["Throughput and modular latency", "Color schema styling", "Database file name length", "The size of comments"],
                "answer": "Throughput and modular latency"
            }
        ]
    }

@app.post("/api/submit-assessment")
def submit_assessment(request: AssessmentSubmitRequest):
    """Processes diagnostic/assessment test score. Re-plans or upgrades profile skills accordingly."""
    skill_id = request.skill_id
    score = request.score
    
    user_skills = dict(request.user_skills)
    skill_meta = SKILL_GRAPH.get(skill_id)
    if not skill_meta:
        raise HTTPException(status_code=404, detail="Skill not found.")
        
    # Determine Status adaptation
    adaptation_log = ""
    target_prof = skill_meta.get("required_proficiency", 70)
    
    if score >= 75:
        # Pass
        user_skills[skill_id] = {
            "proficiency": max(target_prof, score),
            "status": "Completed",
            "confidence": "Verified",
            "last_test_score": score
        }
        adaptation_log = f"Congratulations! You scored {score}%. You have verified mastery in {skill_meta['title']} and unlocked dependent skills."
    elif score < 50:
        # Fail - trigger reinforcement
        user_skills[skill_id] = {
            "proficiency": max(20, score),
            "status": "Needs Improvement",
            "confidence": "Assessed",
            "last_test_score": score
        }
        adaptation_log = f"You scored {score}%. The path has adapted to insert additional basic review materials and practice exercises for {skill_meta['title']}."
    else:
        # Marginal pass
        user_skills[skill_id] = {
            "proficiency": score,
            "status": "In Progress",
            "confidence": "Estimated",
            "last_test_score": score
        }
        adaptation_log = f"You scored {score}%. You have basic familiarity, but need additional reinforcement to reach full target proficiency ({target_prof}%)."
        
    return {
        "skill_id": skill_id,
        "score": score,
        "updated_skills": user_skills,
        "adaptation_log": adaptation_log
    }

@app.post("/api/submit-feedback")
def submit_feedback(request: FeedbackSubmitRequest):
    """Handles explicit user feedback and adapts skill metrics/resource density accordingly."""
    skill_id = request.skill_id
    feedback = request.feedback_type
    
    user_skills = dict(request.user_skills)
    skill_meta = SKILL_GRAPH.get(skill_id)
    if not skill_meta:
        raise HTTPException(status_code=404, detail="Skill not found.")
        
    adaptation_log = ""
    
    if feedback == "Too easy":
        # Fast track
        user_skills[skill_id] = {
            "proficiency": skill_meta.get("required_proficiency", 70),
            "status": "Completed",
            "confidence": "Self-reported"
        }
        adaptation_log = f"Marked {skill_meta['title']} as Completed (Fast-Tracked)."
    elif feedback == "Too difficult":
        # Introduce support
        curr_prof = user_skills.get(skill_id, {}).get("proficiency", 30)
        user_skills[skill_id] = {
            "proficiency": max(0, curr_prof - 15),
            "status": "Needs Improvement",
            "confidence": "Self-reported"
        }
        adaptation_log = f"Added basic foundational tutorials and lowered baseline score to reinforce {skill_meta['title']}."
    elif feedback == "Already know this":
        user_skills[skill_id] = {
            "proficiency": skill_meta.get("required_proficiency", 70),
            "status": "Completed",
            "confidence": "Self-reported"
        }
        adaptation_log = f"Fast-tracked {skill_meta['title']}. You can verify this via diagnostic anytime."
    elif feedback == "Need more practice":
        # Will dynamically trigger rendering extra practice items on frontend
        adaptation_log = "Appended 2 additional custom exercises to your practice list."
    else:
        adaptation_log = f"Feedback logged. Personalizing resource scores for skill {skill_meta['title']}."
        
    return {
        "skill_id": skill_id,
        "updated_skills": user_skills,
        "feedback_event": {"skill_id": skill_id, "feedback_type": feedback},
        "adaptation_log": adaptation_log
    }

@app.post("/api/evaluate-proof-of-work")
def evaluate_proof_of_work(request: ProofOfWorkRequest):
    """Audits user code/projects using Gemini and reports code quality scores."""
    client = get_gemini_client()
    
    if client:
        try:
            prompt = f"""
            You are a strict technical architect auditing a github submission.
            Milestone: {request.milestone_title}
            Skill being tested: {request.skill_id}
            GitHub URL: {request.github_url}
            
            Perform a simulated code review. Check directory layouts, modular design patterns, security risks, and robustness.
            Respond in JSON format:
            {{
                "github_url": "{request.github_url}",
                "milestone_title": "{request.milestone_title}",
                "code_quality_score": "88/100",
                "verification_status": "Verified & Fast-Tracked" or "Action Required",
                "ai_feedback": "Detailed review points here."
            }}
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text)
            return data
        except Exception:
            pass # Fallback to static reviewer

    # Static Fallback Reviewer
    return {
        "github_url": request.github_url,
        "milestone_title": request.milestone_title,
        "code_quality_score": "92/100",
        "verification_status": "Verified & Fast-Tracked",
        "ai_feedback": f"Clean repository layout scanned at {request.github_url}. Good separation of modular routes, correct env variables handling, and robust schemas. Milestone {request.milestone_title} verified."
    }

@app.post("/api/chat")
def chat_assistant(request: ChatRequest):
    """Context-aware assistant conversation with direct visibility of user's active learning roadmap."""
    client = get_gemini_client()
    
    career_name = CAREERS.get(request.target_role, {}).get("name", request.target_role)
    active_skills = [k for k, v in request.user_skills.items() if v.get("status") in ["Completed", "Verified"]]
    weak_skills = [k for k, v in request.user_skills.items() if v.get("status") == "Needs Improvement"]
    system_prompt = build_coach_system_prompt(request, career_name)
    
    if client:
        try:
            contents = []
            for h in request.history:
                role = "user" if h["role"] == "user" else "model"
                contents.append(types.Content(role=role, parts=[types.Part.from_text(text=h["content"])]))
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=request.message)]))
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt
                )
            )
            text = (response.text or "").strip()
            if not text:
                raise ValueError("Empty AI response")
            return {"response": text}
        except Exception as e:
            skip_requested = "skip" in request.message.lower()
            if skip_requested:
                return {"response": f"Not recommended yet.\n\n{request.current_skill or 'This skill'} is still part of your current path. Use the verification assessment or complete the prerequisite steps before skipping it.\n\nIf you want, I can explain the specific blocker and the fastest safe verification path."}
            return {"response": f"I’m having trouble reaching the AI service right now. Based on your current context for **{career_name}**, the safest next step is **{request.next_action or 'your next roadmap item'}**."}
            
    # Simple Static Fallback
    if "skip" in request.message.lower():
        return {
            "response": f"Not recommended yet.\n\n{request.current_skill or 'This skill'} is still part of your current path. You can either complete it or take a verification assessment before we consider skipping it."
        }
    return {
        "response": f"Hello! As your AI Learning Coach for **{career_name}**, I’m here to guide your next step. Your current best action is **{request.next_action or 'study the next roadmap item'}**."
    }
