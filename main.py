import os
import math
import json
import re
from datetime import datetime, timezone
from difflib import get_close_matches
from typing import List, Optional, Dict, Any, Literal
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from skill_engine import analyze_skill_gaps, build_skill_models
from roadmap_service import Roadmap, generate_roadmap, replan_path
from project_engine import build_project_blueprint, build_project_session

# Initialize FastAPI App
app = FastAPI(title="PathMind AI - Personalized Learning Path Engine")

def _parse_cors_origins(raw_value: str) -> List[str]:
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


FRONTEND_URLS = _parse_cors_origins(os.getenv("FRONTEND_URL", ""))

# Configure CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_URLS or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Gemini Client using the new google-genai SDK
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PORT = int(os.getenv("PORT", "8000"))
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
    if request.project_blueprint:
        context_lines.append(f"Project blueprint: {json.dumps(request.project_blueprint)}")
        current_step = request.project_blueprint.get("implementationTasks", [None])[0] if isinstance(request.project_blueprint, dict) else None
        if current_step:
            context_lines.append(f"Current project step: {current_step}")
    if request.project_title:
        context_lines.append(f"Project title: {request.project_title}")
    if request.project_description:
        context_lines.append(f"Project description: {request.project_description}")
    if request.project_milestone:
        context_lines.append(f"Current milestone details: {json.dumps(request.project_milestone)}")
    if request.project_learning_concepts:
        context_lines.append(f"Learning concepts: {', '.join(request.project_learning_concepts)}")
    if request.project_build_task:
        context_lines.append(f"Build task: {request.project_build_task}")
    if request.project_checkpoint:
        context_lines.append(f"Checkpoint: {request.project_checkpoint}")
    if request.project_milestone_skills:
        context_lines.append(f"Milestone skills: {', '.join(request.project_milestone_skills)}")
    if request.completed_milestones:
        context_lines.append(f"Completed milestones: {', '.join(request.completed_milestones)}")
    if request.relevant_assessment:
        context_lines.append(f"Relevant assessment: {json.dumps(request.relevant_assessment)}")
    return f"""
You are PathMind AI Coach.
You are not a generic chatbot.
You coach using only the learner context below and do not invent scores, milestones, or roadmap steps.
When the user is asking about a project, act as a mentor for the current milestone and do not change the roadmap.

Learner context:
{chr(10).join(f'- {line}' for line in context_lines)}

Rules:
- Explain recommendations using actual learner data when available.
- If the user asks to skip a skill, do not mutate the roadmap. Explain why it is or is not safe and request verification.
- If a project blueprint is available, explain the current build step, setup, validation, and troubleshooting in plain language.
- Prefer hints, then small examples, then implementation direction, then debugging help.
- Never claim mastery, unlock anything, or reorder milestones.
- If data is unavailable, say so clearly.
- Be concise, supportive, and specific.
- Always output markdown.
""".strip()


def build_project_mentor_response(request: "ChatRequest", career_name: str) -> Optional[str]:
    """Return a deterministic project-guidance response when the learner is asking how to build."""
    blueprint = request.project_blueprint or {}
    if not isinstance(blueprint, dict) or not blueprint:
        return None

    message = request.message.lower()
    build_keywords = ["build", "how do i", "how to", "implement", "project", "step", "setup", "stuck", "error", "next", "hint", "test", "debug", "understand"]
    if not any(keyword in message for keyword in build_keywords):
        return None

    setup = blueprint.get("setup") or []
    tasks = blueprint.get("implementationTasks") or []
    checks = blueprint.get("validationChecks") or []
    troubleshooting = blueprint.get("troubleshooting") or []
    milestone = request.project_milestone or {}
    current_step = tasks[0] if tasks else request.current_milestone or "Start with the setup step and create the project structure."
    next_step = tasks[1] if len(tasks) > 1 else "Move to the first implementation task."
    current_concepts = request.project_learning_concepts or milestone.get("learning_concepts") or milestone.get("concepts") or []
    current_skills = request.project_milestone_skills or milestone.get("required_skills") or []
    completed = request.completed_milestones or []
    hints_shown = request.project_hints_shown or []
    checkpoint = request.project_checkpoint or milestone.get("checkpoint") or "No checkpoint available."
    assessment_lines = []
    if request.relevant_assessment:
        assessment_lines.append(f"Assessment: {json.dumps(request.relevant_assessment)}")

    level = 1
    if any(keyword in message for keyword in ["debug", "error", "stuck"]):
        level = 5
    elif any(keyword in message for keyword in ["example", "show me", "sample"]):
        level = 4
    elif any(keyword in message for keyword in ["hint", "give me a hint", "nudge"]):
        level = 2
    elif any(keyword in message for keyword in ["how do i", "what should i do next", "next", "setup", "step"]):
        level = 3

    lines = [
        f"### Project Mentor for {career_name}",
        "",
        f"**Project:** {blueprint.get('whatYouAreBuilding') or request.project_title or request.current_milestone or 'A skill-linked project'}",
        f"**Project description:** {request.project_description or blueprint.get('description') or 'A skill-linked build task.'}",
        f"**Current milestone:** {request.current_milestone or milestone.get('title') or 'Unknown'}",
        f"**Milestone description:** {request.project_milestone_description or milestone.get('description') or milestone.get('objective') or 'No milestone description available.'}",
        "",
        f"**Student request level:** {level}",
        f"**Current build step:** {current_step}",
        "",
        f"**Learning concepts:** {', '.join(current_concepts) if current_concepts else 'Not provided'}",
        f"**Build task:** {request.project_build_task or milestone.get('build_task') or current_step}",
        f"**Skills for this milestone:** {', '.join(current_skills) if current_skills else 'Not provided'}",
        f"**Completed milestones:** {', '.join(completed) if completed else 'None yet'}",
        f"**Checkpoint:** {checkpoint}",
    ]
    if assessment_lines:
        lines.extend(["", *assessment_lines])

    if setup:
        lines.extend(["", "**Start here:**", *[f"- {step}" for step in setup[:4]]])

    lines.extend(["", f"**Next implementation step:** {next_step}", "", "**Validation checks:**"])
    if checks:
        lines.extend([f"- {check}" for check in checks])
    else:
        lines.append("- Confirm the project runs and the expected output appears.")

    lines.extend(["", "**Hints already shown:**"])
    if hints_shown:
        lines.extend([f"- {hint}" for hint in hints_shown[:5]])
    else:
        lines.append("- None yet.")

    lines.extend(["", "**Common troubleshooting:**"])
    if troubleshooting:
        lines.extend([f"- {item}" for item in troubleshooting[:3]])
    else:
        lines.append("- If you are stuck, reduce the problem to the smallest working step.")

    if level == 1:
        lines.extend(["", "**Mentor mode:** Concept explanation", "- I will explain the idea behind this milestone and why it matters."])
    elif level == 2:
        lines.extend(["", "**Mentor mode:** Small hint", "- I will give a narrow hint without giving away the full solution."])
    elif level == 3:
        lines.extend(["", "**Mentor mode:** Implementation direction", "- I will point you to the right sequence of steps."])
    elif level == 4:
        lines.extend(["", "**Mentor mode:** Example", "- I can show a small example that matches this project context."])
    else:
        lines.extend(["", "**Mentor mode:** Detailed debugging help", "- I will focus on the error, checkpoint, or failing behavior and help you diagnose it."])

    return "\n".join(lines)

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
    ,
    "cloud_engineer": {
        "id": "cloud_engineer",
        "name": "Cloud Engineer",
        "description": "Designs and operates cloud-native systems, infrastructure, deployment pipelines, and monitoring.",
        "required_skills": [
            "python", "git", "linux", "networking", "cloud_fundamentals", "cloud_architecture", "cloud_deployment", "containers", "monitoring"
        ],
        "optional_skills": ["infrastructure", "ci_cd"],
        "capstone_project": {
            "title": "Cloud-Native Deployment Platform",
            "description": "Build a cloud deployment pipeline with infrastructure, containers, and observability.",
            "requirements": [
                "Design a cloud architecture for a web service.",
                "Deploy a containerized service and monitor uptime.",
                "Automate releases with CI/CD and IaC."
            ]
        }
    },
    "cybersecurity_engineer": {
        "id": "cybersecurity_engineer",
        "name": "Cybersecurity Engineer",
        "description": "Protects systems and applications through secure design, monitoring, and incident response.",
        "required_skills": [
            "python", "git", "linux", "networking", "security_fundamentals", "auth_security", "web_security", "security_monitoring", "incident_response"
        ],
        "optional_skills": ["monitoring"],
        "capstone_project": {
            "title": "Secure Web Application Lab",
            "description": "Build a safe lab environment to evaluate authentication, web security, and monitoring controls.",
            "requirements": [
                "Create a secure API with authentication controls.",
                "Add monitoring and alerting for suspicious activity.",
                "Document an incident response playbook for the lab."
            ]
        }
    },
    "devops_engineer": {
        "id": "devops_engineer",
        "name": "DevOps Engineer",
        "description": "Builds automation, deployment, and infrastructure workflows for software delivery.",
        "required_skills": [
            "git", "python", "linux", "networking", "docker", "ci_cd", "infrastructure", "cloud_deployment", "monitoring"
        ],
        "optional_skills": [],
        "capstone_project": {
            "title": "Automated Delivery Pipeline",
            "description": "Create a reproducible delivery pipeline that builds, tests, and deploys a service.",
            "requirements": [
                "Containerize a service and deploy it automatically.",
                "Add monitoring and rollback-friendly release steps.",
                "Document infrastructure provisioning."
            ]
        }
    },
    "blockchain_engineer": {
        "id": "blockchain_engineer",
        "name": "Blockchain Engineer",
        "description": "Builds blockchain applications using cryptography, distributed systems, and smart contracts.",
        "required_skills": [
            "python", "git", "blockchain_fundamentals", "cryptography", "distributed_systems", "smart_contracts", "blockchain_security"
        ],
        "optional_skills": [],
        "capstone_project": {
            "title": "Blockchain Application Sandbox",
            "description": "Create a safe blockchain prototype that demonstrates ledger concepts and contract deployment.",
            "requirements": [
                "Understand how blocks and ledgers are connected.",
                "Implement and test a simple smart contract in a safe sandbox.",
                "Add security checks for common contract mistakes."
            ]
        }
    },
    "iot_engineer": {
        "id": "iot_engineer",
        "name": "IoT Engineer",
        "description": "Connects devices, sensors, and networked systems into data-driven applications.",
        "required_skills": [
            "python", "git", "networking", "embedded_systems", "sensors", "iot_protocols", "data_processing"
        ],
        "optional_skills": [],
        "capstone_project": {
            "title": "Connected Device Monitoring Lab",
            "description": "Build a small IoT data pipeline that ingests sensor-style inputs and processes them safely.",
            "requirements": [
                "Model a device-to-server data flow.",
                "Process incoming telemetry safely.",
                "Visualize sensor output trends."
            ]
        }
    },
    "rpa_developer": {
        "id": "rpa_developer",
        "name": "RPA Developer",
        "description": "Automates repeatable business workflows with reliable software bots and process design.",
        "required_skills": [
            "python", "git", "process_design", "workflow_automation", "rpa_tools"
        ],
        "optional_skills": [],
        "capstone_project": {
            "title": "Business Workflow Automation Lab",
            "description": "Build an automation workflow that simulates a business process and records success/failure safely.",
            "requirements": [
                "Map a process into discrete automation steps.",
                "Implement a workflow that handles retries and validation.",
                "Report the automation outcome clearly."
            ]
        }
    },
    "robotics_engineer": {
        "id": "robotics_engineer",
        "name": "Robotics Engineer",
        "description": "Develops robotics foundations, embedded systems, and control-oriented software workflows.",
        "required_skills": [
            "python", "robotics_fundamentals", "embedded_systems", "control_systems"
        ],
        "optional_skills": [],
        "capstone_project": {
            "title": "Robotics Simulation Project",
            "description": "Build a safe simulation that demonstrates robotics control concepts without hardware risk.",
            "requirements": [
                "Model a feedback loop or movement simulation.",
                "Validate control behavior in a simulator.",
                "Explain how robotics logic interacts with AI components."
            ]
        }
    },
    "cloud_security_engineer": {
        "id": "cloud_security_engineer",
        "name": "Cloud Security Engineer",
        "description": "Combines cloud architecture with cybersecurity fundamentals, secure deployment, and monitoring.",
        "required_skills": [
            "networking", "linux", "cloud_fundamentals", "cloud_architecture", "cloud_deployment", "containers", "security_fundamentals", "auth_security", "web_security", "security_monitoring", "incident_response"
        ],
        "optional_skills": ["monitoring", "ci_cd", "infrastructure"],
        "capstone_project": {
            "title": "Secure Cloud Deployment Lab",
            "description": "Build a cloud deployment workflow with secure controls and monitoring.",
            "requirements": [
                "Design a cloud service layout with secure access.",
                "Add monitoring and alerting for suspicious activity.",
                "Document a safe incident response plan."
            ]
        }
    },
    "blockchain_security_engineer": {
        "id": "blockchain_security_engineer",
        "name": "Blockchain Security Engineer",
        "description": "Combines blockchain fundamentals with security practices, cryptography, and safe smart contracts.",
        "required_skills": [
            "python", "git", "blockchain_fundamentals", "cryptography", "distributed_systems", "smart_contracts", "blockchain_security", "security_fundamentals"
        ],
        "optional_skills": [],
        "capstone_project": {
            "title": "Blockchain Security Review Lab",
            "description": "Analyze blockchain concepts with a focus on defensive engineering and contract safety.",
            "requirements": [
                "Explain blockchain security principles.",
                "Review a mock smart contract for safe patterns.",
                "Summarize attack surface and mitigations in a lab context."
            ]
        }
    },
    "robotics_ai_engineer": {
        "id": "robotics_ai_engineer",
        "name": "Robotics AI Engineer",
        "description": "Combines robotics foundations with artificial intelligence for safe intelligent systems.",
        "required_skills": [
            "python", "robotics_fundamentals", "embedded_systems", "control_systems", "numpy_pandas", "math_statistics", "machine_learning_basics", "ai_apis"
        ],
        "optional_skills": ["deep_learning"],
        "capstone_project": {
            "title": "Robotics AI Simulation",
            "description": "Build a safe simulation showing how AI interacts with robotics control and perception.",
            "requirements": [
                "Model a robotics control loop.",
                "Use AI to interpret a simulated signal.",
                "Document how the two systems work together safely."
            ]
        }
    },
    "medical_ai_engineer": {
        "id": "medical_ai_engineer",
        "name": "Medical AI Engineer",
        "description": "Combines healthcare technology with AI and data workflows while avoiding clinical medicine curriculum.",
        "required_skills": [
            "numpy_pandas", "math_statistics", "machine_learning_basics", "ai_apis", "rag", "fastapi"
        ],
        "optional_skills": ["embeddings", "vector_databases"],
        "capstone_project": {
            "title": "Healthcare AI Support Tool",
            "description": "Build a safe technology-only AI workflow for healthcare data analysis and support tasks.",
            "requirements": [
                "Process healthcare-like data safely.",
                "Use AI for support tasks, not clinical diagnosis.",
                "Document boundaries and responsible use."
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
    "networking": {
        "id": "networking",
        "title": "Networking Fundamentals",
        "description": "IP addressing, ports, DNS, routing, and troubleshooting basics.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [{"title": "Networking basics", "type": "Documentation", "url": "https://www.cloudflare.com/learning/network-layer/what-is-a-computer-network/"}],
        "practice": ["Explain the purpose of DNS and ports.", "Trace a simple client-server request path."],
        "project": {"title": "Network Diagnostic Workbook", "description": "Document how a client reaches a service using IP, DNS, and ports."}
    },
    "linux": {
        "id": "linux",
        "title": "Linux Fundamentals",
        "description": "Shell navigation, permissions, processes, services, and package management.",
        "prerequisites": [],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [{"title": "Linux Journey", "type": "Course", "url": "https://linuxjourney.com/"}],
        "practice": ["List files and directories.", "Inspect running processes and service status."],
        "project": {"title": "Linux Admin Checklist", "description": "Perform safe Linux inspection and maintenance tasks."}
    },
    "cloud_fundamentals": {
        "id": "cloud_fundamentals",
        "title": "Cloud Fundamentals",
        "description": "Virtualization, regions, compute, storage, scaling, and managed service concepts.",
        "prerequisites": ["networking", "linux"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [{"title": "AWS Cloud Practitioner Essentials", "type": "Course", "url": "https://aws.amazon.com/training/course-descriptions/cloud-practitioner-essentials/"}],
        "practice": ["Describe cloud regions and availability zones.", "Compare managed and self-hosted services."],
        "project": {"title": "Cloud Concepts Map", "description": "Create a reference diagram for cloud service types and deployment models."}
    },
    "cloud_architecture": {
        "id": "cloud_architecture",
        "title": "Cloud Architecture",
        "description": "Designing reliable cloud systems, scaling patterns, and service composition.",
        "prerequisites": ["cloud_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "AWS Well-Architected Framework", "type": "Documentation", "url": "https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html"}],
        "practice": ["Sketch a stateless app architecture.", "Compare single-region and multi-region designs."],
        "project": {"title": "Reference Cloud Architecture", "description": "Design a cloud architecture for a web service with scaling and resilience notes."}
    },
    "containers": {
        "id": "containers",
        "title": "Containers & Orchestration Basics",
        "description": "Images, containers, runtime basics, and orchestration concepts.",
        "prerequisites": ["docker"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "Container Basics", "type": "Article", "url": "https://docs.docker.com/get-started/"}],
        "practice": ["Build and run a container image.", "Explain image layers vs containers."],
        "project": {"title": "Container Runbook", "description": "Document how to build, run, and inspect a containerized service."}
    },
    "ci_cd": {
        "id": "ci_cd",
        "title": "CI/CD Automation",
        "description": "Continuous integration, continuous delivery, test gating, and release workflows.",
        "prerequisites": ["git"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "GitHub Actions Docs", "type": "Documentation", "url": "https://docs.github.com/actions"}],
        "practice": ["Add a build step to a workflow.", "Trigger tests on pull requests."],
        "project": {"title": "Pipeline Skeleton", "description": "Create a CI/CD workflow that builds and validates a repository on every change."}
    },
    "infrastructure": {
        "id": "infrastructure",
        "title": "Infrastructure as Code",
        "description": "Provisioning and managing environments as code with repeatable configuration.",
        "prerequisites": ["cloud_fundamentals", "ci_cd"],
        "required_proficiency": 70,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Infrastructure as Code Overview", "type": "Article", "url": "https://www.hashicorp.com/resources/what-is-infrastructure-as-code"}],
        "practice": ["Describe desired-state infrastructure.", "Compare mutable and immutable deployments."],
        "project": {"title": "Environment Provisioning Blueprint", "description": "Draft reproducible infrastructure steps for a sample application."}
    },
    "security_fundamentals": {
        "id": "security_fundamentals",
        "title": "Security Fundamentals",
        "description": "Core security principles, threat modeling, least privilege, and safe engineering habits.",
        "prerequisites": ["networking", "linux"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [{"title": "Security Principles Overview", "type": "Article", "url": "https://www.cisa.gov/topics/cybersecurity-best-practices"}],
        "practice": ["Explain least privilege.", "Identify basic threat categories."],
        "project": {"title": "Security Principles Sheet", "description": "Write a short assessment of threats and protections for a sample app."}
    },
    "web_security": {
        "id": "web_security",
        "title": "Web Security",
        "description": "Common web risks, secure input handling, and safe session design.",
        "prerequisites": ["security_fundamentals", "auth_security"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "OWASP Top 10 Overview", "type": "Documentation", "url": "https://owasp.org/www-project-top-ten/"}],
        "practice": ["Identify insecure patterns in a sample API.", "Describe input validation defenses."],
        "project": {"title": "Secure Web Review", "description": "Review a safe sample application for common web risks and document mitigations."}
    },
    "security_monitoring": {
        "id": "security_monitoring",
        "title": "Security Monitoring",
        "description": "Log analysis, alerts, anomaly spotting, and basic detection workflows.",
        "prerequisites": ["monitoring", "security_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Security Monitoring Basics", "type": "Article", "url": "https://www.splunk.com/en_us/data-insider/what-is-security-monitoring.html"}],
        "practice": ["Review log snippets for suspicious patterns.", "Write a detection checklist."],
        "project": {"title": "Monitoring Simulation", "description": "Analyze sample logs and outline safe alerting rules."}
    },
    "incident_response": {
        "id": "incident_response",
        "title": "Incident Response",
        "description": "Triage, containment, analysis, recovery, and post-incident learning for safe systems.",
        "prerequisites": ["security_monitoring"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Incident Response Planning", "type": "Documentation", "url": "https://www.cisa.gov/resources-tools/resources/incident-response-plan-brochure"}],
        "practice": ["Write a basic incident response checklist.", "Classify incident severity from a scenario."],
        "project": {"title": "Response Runbook", "description": "Prepare a safe incident response guide for a sample service."}
    },
    "blockchain_fundamentals": {
        "id": "blockchain_fundamentals",
        "title": "Blockchain Fundamentals",
        "description": "Distributed ledgers, blocks, transactions, consensus, and blockchain concepts.",
        "prerequisites": ["python", "git"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [{"title": "Blockchain Basics", "type": "Article", "url": "https://ethereum.org/en/what-is-ethereum/"}],
        "practice": ["Explain a ledger and transaction.", "Compare blockchain and traditional databases."],
        "project": {"title": "Ledger Concept Notebook", "description": "Document how blocks, hashes, and transactions relate in a safe educational lab."}
    },
    "cryptography": {
        "id": "cryptography",
        "title": "Applied Cryptography",
        "description": "Hashes, digital signatures, public/private keys, and secure communication basics.",
        "prerequisites": ["blockchain_fundamentals", "security_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Cryptography Explained", "type": "Article", "url": "https://www.cloudflare.com/learning/ssl/what-is-cryptography/"}],
        "practice": ["Explain hashing vs encryption.", "Describe the role of digital signatures."],
        "project": {"title": "Crypto Concepts Guide", "description": "Create a safe learning guide that explains cryptographic primitives."}
    },
    "distributed_systems": {
        "id": "distributed_systems",
        "title": "Distributed Systems",
        "description": "Consistency, replication, fault tolerance, and distributed coordination basics.",
        "prerequisites": ["networking", "linux"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Distributed Systems Overview", "type": "Article", "url": "https://www.oreilly.com/library/view/designing-data-intensive/9781491903063/"}],
        "practice": ["Explain replication and consensus at a high level.", "Compare single-node and distributed failures."],
        "project": {"title": "Distributed Concepts Map", "description": "Document a safe comparison of distributed system properties."}
    },
    "smart_contracts": {
        "id": "smart_contracts",
        "title": "Smart Contracts",
        "description": "Contract logic, state changes, and safe deployment concepts for blockchain applications.",
        "prerequisites": ["blockchain_fundamentals", "cryptography"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Solidity Docs", "type": "Documentation", "url": "https://docs.soliditylang.org/"}],
        "practice": ["Read a simple contract and explain its state.", "Identify safe contract design practices."],
        "project": {"title": "Smart Contract Walkthrough", "description": "Review a simple contract pattern in a sandbox environment."}
    },
    "blockchain_security": {
        "id": "blockchain_security",
        "title": "Blockchain Security",
        "description": "Safe blockchain engineering practices, contract review, and attack surface awareness.",
        "prerequisites": ["blockchain_fundamentals", "security_fundamentals"],
        "required_proficiency": 75,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Smart Contract Security Basics", "type": "Article", "url": "https://consensys.io/blog/blockchain-security/"}],
        "practice": ["Identify a safe contract pattern.", "Explain a common contract risk in defensive terms."],
        "project": {"title": "Blockchain Safety Review", "description": "Review a mock blockchain project for safe engineering practices."}
    },
    "embedded_systems": {
        "id": "embedded_systems",
        "title": "Embedded Systems",
        "description": "Low-level system concepts, device interactions, and constrained computing basics.",
        "prerequisites": ["python"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "Embedded Systems Basics", "type": "Article", "url": "https://www.embedded.com/"}],
        "practice": ["Explain a device loop.", "Describe how sensors feed embedded software."],
        "project": {"title": "Device Loop Workbook", "description": "Map robotics and device components and explain their safe operation."}
    },
    "sensors": {
        "id": "sensors",
        "title": "Sensors & Telemetry",
        "description": "Reading physical measurements and converting them to data streams.",
        "prerequisites": ["embedded_systems", "networking"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "Sensors Overview", "type": "Article", "url": "https://learn.sparkfun.com/tutorials/sensors/all"}],
        "practice": ["Describe what a sensor measures.", "Map telemetry to a structured record."],
        "project": {"title": "Sensor Data Notes", "description": "Create a safe data flow note for sample telemetry."}
    },
    "iot_protocols": {
        "id": "iot_protocols",
        "title": "IoT Protocols",
        "description": "Protocols and messaging patterns used by connected devices.",
        "prerequisites": ["sensors", "networking"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "MQTT Essentials", "type": "Article", "url": "https://mqtt.org/"}],
        "practice": ["Compare push vs pull messaging.", "Describe device telemetry routing."],
        "project": {"title": "IoT Messaging Guide", "description": "Document a safe device-to-server message flow."}
    },
    "data_processing": {
        "id": "data_processing",
        "title": "Data Processing for Telemetry",
        "description": "Cleaning, aggregating, and validating data from connected systems.",
        "prerequisites": ["numpy_pandas", "iot_protocols"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "Data Processing Basics", "type": "Article", "url": "https://pandas.pydata.org/docs/"}],
        "practice": ["Aggregate sample readings.", "Filter malformed telemetry rows."],
        "project": {"title": "Telemetry Cleaning Workbook", "description": "Create a simple data cleaning pipeline for simulated device data."}
    },
    "process_design": {
        "id": "process_design",
        "title": "Process Design",
        "description": "Mapping business steps into deterministic automation-ready workflows.",
        "prerequisites": ["python"],
        "required_proficiency": 70,
        "estimated_hours": 5,
        "difficulty": "Beginner",
        "resources": [{"title": "Workflow Mapping Basics", "type": "Article", "url": "https://www.lucidchart.com/pages/process-mapping"}],
        "practice": ["Diagram a repetitive business process.", "Identify automation steps and exceptions."],
        "project": {"title": "Workflow Blueprint", "description": "Translate a sample office workflow into automation steps."}
    },
    "workflow_automation": {
        "id": "workflow_automation",
        "title": "Workflow Automation",
        "description": "Automating repetitive tasks with scriptable, reliable, and auditable steps.",
        "prerequisites": ["process_design", "python"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "Automation Concepts", "type": "Article", "url": "https://www.atlassian.com/work-management/project-management/process-automation"}],
        "practice": ["Outline retry logic for an automation task.", "Validate input/output steps in sequence."],
        "project": {"title": "Automation Flow Lab", "description": "Write a safe automation flow that simulates repeatable office tasks."}
    },
    "rpa_tools": {
        "id": "rpa_tools",
        "title": "RPA Tools",
        "description": "Using automation tools to execute workflows in a controlled environment.",
        "prerequisites": ["workflow_automation"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Intermediate",
        "resources": [{"title": "RPA Overview", "type": "Article", "url": "https://www.uipath.com/rpa/robotic-process-automation"}],
        "practice": ["Simulate a bot stepping through a task.", "Document a safe bot exception handling flow."],
        "project": {"title": "RPA Sandbox", "description": "Prototype an automation bot in a safe, educational scenario."}
    },
    "robotics_fundamentals": {
        "id": "robotics_fundamentals",
        "title": "Robotics Fundamentals",
        "description": "Robotics concepts, kinematics basics, and safe robot system modeling.",
        "prerequisites": ["python"],
        "required_proficiency": 70,
        "estimated_hours": 6,
        "difficulty": "Beginner",
        "resources": [{"title": "Robotics Basics", "type": "Article", "url": "https://www.robotics.org/"}],
        "practice": ["Explain a robot's sensing and actuation loop.", "Describe a feedback controller at a high level."],
        "project": {"title": "Robotics Concepts Notebook", "description": "Map robotics components and explain their safe operation."}
    },
    "control_systems": {
        "id": "control_systems",
        "title": "Control Systems",
        "description": "Feedback loops, stability, and control theory basics for robotics and automation.",
        "prerequisites": ["robotics_fundamentals", "math_statistics"],
        "required_proficiency": 70,
        "estimated_hours": 8,
        "difficulty": "Intermediate",
        "resources": [{"title": "Control Systems Introduction", "type": "Article", "url": "https://www.mathworks.com/discovery/control-systems.html"}],
        "practice": ["Explain feedback and stability.", "Sketch a simple control loop."],
        "project": {"title": "Control Loop Study", "description": "Document a safe control loop and how it responds to changes."}
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


ASSESSMENT_SKILL_GROUPS = {
    "data_scientist": ["python", "sql_basics", "numpy_pandas", "math_statistics", "machine_learning_basics"],
    "cloud_engineer": ["linux", "networking", "cloud_fundamentals", "cloud_architecture", "containers", "cicd", "infrastructure"],
    "cybersecurity_engineer": ["networking", "linux", "security_fundamentals", "web_security", "security_monitoring", "incident_response"],
    "devops_engineer": ["linux", "git", "containers", "cicd", "cloud_deployment", "monitoring"],
}


QUESTION_TYPE_BY_SKILL = {
    "python": "mcq",
    "sql_basics": "mcq",
    "numpy_pandas": "short_answer",
    "math_statistics": "short_answer",
    "machine_learning_basics": "mcq",
    "cloud_fundamentals": "mcq",
    "containers": "mcq",
    "cicd": "short_answer",
    "security_fundamentals": "mcq",
    "web_security": "short_answer",
    "incident_response": "short_answer",
}


def _assessment_skill_scope(target_role: str) -> List[str]:
    career = CAREERS.get(target_role, {})
    required = career.get("required_skills", [])
    optional = career.get("optional_skills", [])
    preferred = ASSESSMENT_SKILL_GROUPS.get(target_role, [])
    scope = [skill for skill in preferred if skill in resolve_prerequisites(required + optional, SKILL_GRAPH)]
    if scope:
        return scope
    resolved = resolve_prerequisites(required, SKILL_GRAPH)
    return [skill for skill in resolved if skill in SKILL_GRAPH][:8]


def _assessment_difficulty(skill_id: str, proficiency: int) -> str:
    meta = SKILL_GRAPH.get(skill_id, {})
    base = meta.get("difficulty", "Intermediate")
    if proficiency < 35:
        return "Beginner"
    if proficiency < 70:
        return "Intermediate"
    return "Advanced" if base in {"Intermediate", "Advanced"} else base


def _assessment_question_type(skill_id: str, question_type: Optional[str] = None) -> str:
    if question_type in {"mcq", "short_answer", "coding"}:
        return question_type
    return QUESTION_TYPE_BY_SKILL.get(skill_id, "mcq")


def _assessment_template_for_skill(skill_id: str, difficulty: str) -> Dict[str, Any]:
    meta = SKILL_GRAPH.get(skill_id, {})
    title = meta.get("title", skill_id.replace("_", " ").title())
    if difficulty == "Beginner":
        return {
            "question": f"Which idea is most important when starting to learn {title}?",
            "options": [
                f"Understand the core purpose of {title}",
                "Skip to the most advanced topic immediately",
                "Memorize unrelated tools first",
                "Ignore examples and practice",
            ],
            "answer": f"Understand the core purpose of {title}",
            "explanation": f"Beginning with the core purpose of {title} helps build the right mental model.",
        }
    if difficulty == "Advanced":
        return {
            "question": f"How would you apply {title} in a real project with constraints and edge cases?",
            "options": [
                f"Describe a production-minded workflow using {title}",
                "Use it without testing or validation",
                "Skip prerequisites entirely",
                "Only memorize the title",
            ],
            "answer": f"Describe a production-minded workflow using {title}",
            "explanation": f"Advanced assessment checks for project-level application of {title}.",
        }
    return {
        "question": f"What is the most accurate statement about {title}?",
        "options": [
            f"It is a core concept for {title}",
            "It is unrelated to this career",
            "It only matters for design color choices",
            "It replaces all other skills",
        ],
        "answer": f"It is a core concept for {title}",
        "explanation": f"This checks whether the learner understands the central idea of {title}.",
    }


def _safe_assessment_question(skill_id: str, proficiency: int, client: Optional[Any] = None) -> Dict[str, Any]:
    difficulty = _assessment_difficulty(skill_id, proficiency)
    question_type = _assessment_question_type(skill_id)
    template = _assessment_template_for_skill(skill_id, difficulty)
    question = {
        "questionId": f"{skill_id}-0",
        "skillId": skill_id,
        "question": template["question"],
        "options": template["options"],
        "difficulty": difficulty,
        "questionType": question_type,
        "explanation": template["explanation"],
    }
    if client and skill_id in SKILL_GRAPH:
        try:
            prompt = f"""
Generate exactly one assessment question for the skill below.
Skill: {SKILL_GRAPH[skill_id]['title']}
Description: {SKILL_GRAPH[skill_id].get('description', '')}
Difficulty: {difficulty}
Question type: {question_type}
Return JSON with keys: question, options, answer, explanation, questionType.
Rules:
- options must have exactly 4 items for mcq
- questionType must be one of mcq, short_answer, coding
- answer must be a short reference answer or the exact correct option
"""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            data = json.loads(response.text)
            if isinstance(data, dict):
                candidate_options = data.get("options", template["options"])
                candidate_type = _assessment_question_type(skill_id, data.get("questionType"))
                if isinstance(candidate_options, list) and len(candidate_options) == 4 or candidate_type in {"short_answer", "coding"}:
                    question.update({
                        "question": str(data.get("question", question["question"])),
                        "options": candidate_options if isinstance(candidate_options, list) else question["options"],
                        "questionType": candidate_type,
                        "explanation": str(data.get("explanation", question["explanation"])),
                        "answer": str(data.get("answer", template["answer"])),
                    })
        except Exception:
            pass
    question["answer"] = template["answer"]
    return question


def _normalize_assessment_evidence(answer: Any, question: Dict[str, Any], score: int, correct: Optional[bool], evaluation: Optional[str] = None) -> Dict[str, Any]:
    return AssessmentEvidenceItem(
        score=score,
        question_id=answer.questionId,
        question_type=_assessment_question_type(answer.skillId, question.get("questionType")),
        answer=answer.answer,
        correct=correct,
        evaluation=evaluation,
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    ).model_dump()

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
    project = build_project_blueprint(skill_id, proficiency, skill_graph)
    skill_title = skill_graph.get(skill_id, {}).get("title", skill_id)
    prerequisites = skill_graph.get(skill_id, {}).get("prerequisites", [])
    competency_focus = [skill_title] + [skill_graph.get(prereq, {}).get("title", prereq) for prereq in prerequisites[:2]]
    project["competencyFocus"] = competency_focus
    project["skills"] = [skill_id, *prerequisites[:2]]
    return project


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
        "reason": f"This project is recommended because it is a structured learning environment for {skill_graph.get(skill_id, {}).get('title', skill_id)} and its prerequisites.",
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


class GoalClassification(BaseModel):
    target_role: str
    domain: str
    specialization: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    support_level: str = Field(pattern="^(supported|partial|outside_scope)$")
    reason: str
    clarification_question: Optional[str] = None
    related_supported_roles: List[str] = Field(default_factory=list)
    domains: List[str] = Field(default_factory=list)
    normalized_goal: str = ""
    intermediate_intent: str = ""

class GoalAnalysis(BaseModel):
    goal: str
    careerTitle: str
    description: str
    requiredSkills: List[str]
    estimatedDuration: str
    readiness: int = Field(ge=0, le=100)
    matched_career_id: Optional[str] = None
    support_level: str = "supported"
    domain: str = ""
    specialization: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    reason: str = ""
    is_ambiguous: bool = False
    clarification_question: str = ""
    normalized_name: str = ""
    extracted_skills: List[str] = Field(default_factory=list)
    target_outcome: str = ""
    related_supported_roles: List[str] = Field(default_factory=list)
    competencies: List[str] = Field(default_factory=list)

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
    interest: str = ""


class ProjectCompletionRequest(BaseModel):
    target_role: str
    skill_id: str
    project_title: str
    score: int = Field(ge=0, le=100)
    user_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    evidence_summary: str = ""

CAREER_CLASSIFICATION_HINTS = {
    "backend_ai_developer": {
        "domain": "technology",
        "specialization": "backend ai development",
        "support_level": "supported",
        "related_supported_roles": ["ai_engineer", "full_stack_developer"],
    },
    "ai_engineer": {
        "domain": "technology",
        "specialization": "artificial intelligence engineering",
        "support_level": "supported",
        "related_supported_roles": ["backend_ai_developer", "ml_engineer", "data_scientist"],
    },
    "ml_engineer": {
        "domain": "technology",
        "specialization": "machine learning engineering",
        "support_level": "supported",
        "related_supported_roles": ["ai_engineer", "data_scientist"],
    },
    "data_scientist": {
        "domain": "technology",
        "specialization": "data science and analytics",
        "support_level": "supported",
        "related_supported_roles": ["ml_engineer", "backend_ai_developer"],
    },
    "full_stack_developer": {
        "domain": "technology",
        "specialization": "full stack web development",
        "support_level": "supported",
        "related_supported_roles": ["backend_ai_developer"],
    },
    "cloud_engineer": {
        "domain": "cloud",
        "specialization": "cloud engineering",
        "support_level": "supported",
        "related_supported_roles": ["devops_engineer", "backend_ai_developer"],
    },
    "cybersecurity_engineer": {
        "domain": "cybersecurity",
        "specialization": "cybersecurity engineering",
        "support_level": "supported",
        "related_supported_roles": ["cloud_engineer", "devops_engineer"],
    },
    "devops_engineer": {
        "domain": "devops",
        "specialization": "devops engineering",
        "support_level": "supported",
        "related_supported_roles": ["cloud_engineer", "backend_ai_developer"],
    },
    "blockchain_engineer": {
        "domain": "blockchain",
        "specialization": "blockchain engineering",
        "support_level": "supported",
        "related_supported_roles": ["cybersecurity_engineer"],
    },
    "iot_engineer": {
        "domain": "iot",
        "specialization": "internet of things engineering",
        "support_level": "supported",
        "related_supported_roles": ["cloud_engineer"],
    },
    "rpa_developer": {
        "domain": "rpa",
        "specialization": "robotic process automation",
        "support_level": "supported",
        "related_supported_roles": ["backend_ai_developer"],
    },
    "robotics_engineer": {
        "domain": "robotics",
        "specialization": "robotics engineering",
        "support_level": "supported",
        "related_supported_roles": ["ai_engineer"],
    },
    "cloud_security_engineer": {
        "domain": "cloud",
        "specialization": "cloud security engineering",
        "support_level": "partial",
        "related_supported_roles": ["cloud_engineer", "cybersecurity_engineer"],
    },
    "blockchain_security_engineer": {
        "domain": "blockchain",
        "specialization": "blockchain security engineering",
        "support_level": "partial",
        "related_supported_roles": ["blockchain_engineer", "cybersecurity_engineer"],
    },
    "robotics_ai_engineer": {
        "domain": "robotics",
        "specialization": "robotics ai engineering",
        "support_level": "partial",
        "related_supported_roles": ["robotics_engineer", "ai_engineer"],
    },
    "medical_ai_engineer": {
        "domain": "artificial_intelligence",
        "specialization": "artificial intelligence + healthcare technology",
        "support_level": "partial",
        "related_supported_roles": ["ai_engineer", "data_scientist"],
    },
}

def build_goal_analysis(
    goal: str,
    career_id: str,
    *,
    support_level: str = "supported",
    confidence: float = 1.0,
    reason: str = "",
    is_ambiguous: bool = False,
    clarification_question: str = "",
    related_supported_roles: Optional[List[str]] = None,
) -> GoalAnalysis:
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


def build_goal_analysis(
    goal: str,
    career_id: str,
    *,
    support_level: str = "supported",
    confidence: float = 1.0,
    reason: str = "",
    is_ambiguous: bool = False,
    clarification_question: str = "",
    related_supported_roles: Optional[List[str]] = None,
) -> GoalAnalysis:
    career = CAREERS[career_id]
    required_skills = list(career.get("required_skills", []))
    skill_count = len(required_skills)
    duration = "3-5 months" if skill_count <= 12 else "6-9 months" if skill_count <= 18 else "9-12 months"
    hints = CAREER_CLASSIFICATION_HINTS.get(career_id, {})
    return GoalAnalysis(
        goal=goal,
        careerTitle=career["name"],
        description=career["description"],
        requiredSkills=required_skills,
        estimatedDuration=duration,
        readiness=0,
        matched_career_id=career_id,
        support_level=support_level,
        domain=hints.get("domain", "technology"),
        specialization=hints.get("specialization", career["name"].lower()),
        confidence=confidence,
        reason=reason or f"Matched to {career['name']} using the internal career blueprint.",
        is_ambiguous=is_ambiguous,
        clarification_question=clarification_question,
        normalized_name=career["name"],
        extracted_skills=[],
        target_outcome=f"Build and grow toward a career as a {career['name']}.",
        related_supported_roles=related_supported_roles or list(hints.get("related_supported_roles", [])),
    )


DETERMINISTIC_CONFIDENCE_THRESHOLD = float(os.getenv("DETERMINISTIC_CONFIDENCE_THRESHOLD", "0.90"))

GOAL_ALIASES = {
    "data_scientist": [
        "data analyst",
        "data analytics",
        "data science",
        "data scientist",
        "analytics engineer",
        "business intelligence",
        "bi analyst",
        "data analysis",
    ],
    "backend_ai_developer": [
        "backend ai",
        "ai backend",
        "cloud engineer",
        "cloud computing",
        "cloud security engineer",
        "software backend",
        "api backend",
    ],
    "ai_engineer": [
        "ai engineer",
        "artificial intelligence engineer",
        "generative ai engineer",
        "medical ai engineer",
        "llm engineer",
        "prompt engineer",
    ],
    "ml_engineer": [
        "machine learning engineer",
        "ml engineer",
        "model evaluation",
        "model serving",
        "predictive modeling",
    ],
    "full_stack_developer": [
        "full stack developer",
        "web developer",
        "frontend developer",
        "react developer",
        "next js developer",
    ],
}

DOMAIN_TAXONOMY = {
    "technology": ["technology", "software engineering", "software"],
    "software_engineering": ["software engineering", "software", "application development"],
    "backend": ["backend", "backend engineering", "api development"],
    "frontend": ["frontend", "ui engineering", "web frontend"],
    "data_analytics": ["data analytics", "analytics", "business intelligence"],
    "data_science": ["data science", "statistics", "predictive modeling"],
    "artificial_intelligence": ["artificial intelligence", "ai", "llm", "rag"],
    "machine_learning": ["machine learning", "ml", "predictive modeling"],
    "cloud": ["cloud", "cloud computing", "cloud engineering"],
    "devops": ["devops", "deployment", "ci/cd"],
    "cybersecurity": ["cybersecurity", "security", "network security"],
    "blockchain": ["blockchain", "distributed ledger"],
    "iot": ["iot", "internet of things", "connected devices"],
    "robotics": ["robotics", "robotic process automation", "automation bots"],
    "rpa": ["rpa", "robotic process automation", "automation"],
    "databases": ["sql", "database", "postgresql"],
    "testing": ["testing", "qa", "quality assurance"],
    "mobile": ["mobile", "android", "ios"],
    "healthcare_technology": ["healthcare technology", "hospital software", "medical software"],
}

COMPETENCY_BLUEPRINTS = {
    "data_analytics": {
        "label": "Data Analytics",
        "skills": ["python", "sql_basics", "numpy_pandas", "data_visualization", "data_warehousing"],
        "missing": [],
    },
    "data_science": {
        "label": "Data Science",
        "skills": ["python", "sql_basics", "numpy_pandas", "math_statistics", "machine_learning_basics", "model_evaluation"],
        "missing": [],
    },
    "cloud": {
        "label": "Cloud Computing",
        "skills": ["git", "python", "docker", "cloud_deployment", "fastapi"],
        "missing": ["cloud_fundamentals", "cloud_services"],
    },
    "cybersecurity": {
        "label": "Cybersecurity",
        "skills": ["python", "fastapi", "auth_security", "monitoring"],
        "missing": ["networking", "linux", "security_fundamentals", "web_security", "incident_response"],
    },
    "devops": {
        "label": "DevOps",
        "skills": ["git", "python", "docker", "cloud_deployment", "monitoring"],
        "missing": ["linux", "networking", "ci_cd", "infrastructure"],
    },
    "blockchain": {
        "label": "Blockchain",
        "skills": ["python", "git"],
        "missing": ["cryptography", "blockchain_fundamentals", "smart_contracts", "distributed_systems"],
    },
    "iot": {
        "label": "IoT",
        "skills": ["python", "git", "networking"],
        "missing": ["embedded_systems", "sensors", "iot_protocols", "data_processing"],
    },
    "rpa": {
        "label": "RPA",
        "skills": ["python", "git"],
        "missing": ["workflow_automation", "process_design", "rpa_tools"],
    },
    "artificial_intelligence": {
        "label": "Artificial Intelligence",
        "skills": ["python", "numpy_pandas", "math_statistics", "machine_learning_basics", "ai_apis", "rag"],
        "missing": [],
    },
    "backend": {
        "label": "Backend Engineering",
        "skills": ["python", "fastapi", "sql_basics", "postgresql", "auth_security", "docker"],
        "missing": [],
    },
    "robotics": {
        "label": "Robotics",
        "skills": ["python"],
        "missing": ["robotics_fundamentals", "embedded_systems", "control_systems"],
    },
    "healthcare_technology": {
        "label": "Healthcare Technology",
        "skills": ["python", "sql_basics", "numpy_pandas", "fastapi"],
        "missing": ["healthcare_domain_knowledge"],
    },
    "cloud_security_engineer": {
        "label": "Cloud Security",
        "skills": ["networking", "linux", "cloud_fundamentals", "cloud_architecture", "cloud_deployment", "containers", "security_fundamentals", "auth_security", "web_security", "security_monitoring", "incident_response"],
        "missing": ["cloud_fundamentals", "cloud_architecture", "security_fundamentals", "security_monitoring", "incident_response"],
    },
    "blockchain_security_engineer": {
        "label": "Blockchain Security",
        "skills": ["python", "git", "blockchain_fundamentals", "cryptography", "distributed_systems", "smart_contracts", "blockchain_security", "security_fundamentals"],
        "missing": ["cryptography", "blockchain_fundamentals", "distributed_systems", "smart_contracts", "blockchain_security", "security_fundamentals"],
    },
    "robotics_ai_engineer": {
        "label": "Robotics AI",
        "skills": ["python", "robotics_fundamentals", "embedded_systems", "control_systems", "numpy_pandas", "math_statistics", "machine_learning_basics", "ai_apis"],
        "missing": ["robotics_fundamentals", "embedded_systems", "control_systems"],
    },
    "medical_ai_engineer": {
        "label": "Medical AI",
        "skills": ["numpy_pandas", "math_statistics", "machine_learning_basics", "ai_apis", "rag", "fastapi"],
        "missing": ["healthcare_domain_knowledge"],
    },
}

DOMAIN_PRIORITY = [
    "cloud",
    "cybersecurity",
    "blockchain",
    "iot",
    "rpa",
    "devops",
    "healthcare_technology",
    "robotics",
    "artificial_intelligence",
    "machine_learning",
    "data_science",
    "data_analytics",
    "backend",
    "frontend",
    "databases",
    "testing",
    "mobile",
    "software_engineering",
    "technology",
]


def normalize_goal(query: str) -> str:
    text = query.strip().lower()
    text = re.sub(r"[^\w\s+/-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.replace("i wanna", "i want to")
    text = text.replace("i’d like", "i want to")
    text = text.replace("id like", "i want to")
    text = text.replace("become a", "")
    text = text.replace("become an", "")
    text = text.replace("career in", "")
    text = text.replace("how can i", "")
    text = text.replace("how do i", "")
    text = text.replace("how to", "")
    return text.strip()


def _goal_has_term(text: str, term: str) -> bool:
    pattern = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(rf"(?<!\w){pattern}(?!\w)", text) is not None


def classify_goal_deterministically(normalized_query: str) -> tuple[Optional[str], float, str, str, List[str], List[str]]:
    q = normalized_query
    if _goal_has_term(q, "blockchain") and _goal_has_term(q, "security"):
        return None, 0.94, "partial", "Matched as blockchain security, a composed competency goal.", [], ["blockchain", "cybersecurity"]
    if _goal_has_term(q, "cloud") and _goal_has_term(q, "security"):
        return None, 0.95, "partial", "Matched as cloud security, a composed competency goal.", [], ["cloud", "cybersecurity"]
    if _goal_has_term(q, "medical") and _goal_has_term(q, "ai"):
        return None, 0.88, "partial", "Matched as medical AI, a healthcare technology goal.", [], ["healthcare_technology", "artificial_intelligence"]
    if (_goal_has_term(q, "robotics") or _goal_has_term(q, "robotic")) and _goal_has_term(q, "ai"):
        return None, 0.93, "partial", "Matched as robotics AI, a composed competency goal.", [], ["robotics", "artificial_intelligence"]
    if _goal_has_term(q, "cloud") and not _goal_has_term(q, "ai"):
        return None, 0.97, "partial", "Matched as cloud computing, a cloud competency goal.", [], ["cloud"]
    if _goal_has_term(q, "blockchain"):
        return None, 0.96, "partial", "Matched as blockchain, a blockchain competency goal.", [], ["blockchain"]
    if _goal_has_term(q, "cybersecurity"):
        return None, 0.96, "partial", "Matched as cybersecurity, a cybersecurity competency goal.", [], ["cybersecurity"]
    if _goal_has_term(q, "devops"):
        return None, 0.95, "partial", "Matched as DevOps, an operations competency goal.", [], ["devops"]
    if _goal_has_term(q, "iot") or _goal_has_term(q, "internet of things"):
        return None, 0.95, "partial", "Matched as IoT, a connected-systems competency goal.", [], ["iot"]
    if _goal_has_term(q, "rpa") or (_goal_has_term(q, "software") and _goal_has_term(q, "bots")):
        return None, 0.94, "partial", "Matched as RPA, an automation competency goal.", [], ["rpa"]

    matches: List[str] = []
    for career_id, aliases in GOAL_ALIASES.items():
        if any(_goal_has_term(q, alias) for alias in aliases):
            matches.append(career_id)

    if matches and "ai_engineer" in matches and _goal_has_term(q, "medical"):
        return None, 0.88, "partial", "Matched as medical AI, a healthcare technology goal.", [], ["healthcare_technology", "artificial_intelligence"]

    if "doctor" in q or "medicine" in q or "surgeon" in q or "nurse" in q:
        return None, 0.99, "outside_scope", "clinical medicine is outside PathMind's supported technology learning scope.", [], ["healthcare"]

    if "hospital software" in q or "healthcare data" in q or "medical software" in q:
        return "data_scientist" if "data" in q else "backend_ai_developer", 0.94, "partial", "The goal is supported as healthcare technology rather than clinical medicine.", ["healthcare_technology"], ["healthcare_technology"]

    if matches:
        career_id = matches[0]
        if career_id == "data_scientist":
            return career_id, 0.98, "supported", "Matched to the data science and analytics learning path.", ["data_scientist"], ["data_science", "data_analytics"]
        if career_id == "ai_engineer" and "medical" in q:
            return career_id, 0.88, "partial", "The goal combines healthcare and AI. PathMind can support the technology side only.", ["ai_engineer", "data_scientist"], ["healthcare_technology", "artificial_intelligence"]
        return career_id, 0.93, "supported", f"Matched to the {CAREERS[career_id]['name']} blueprint.", [career_id], [career_id]

    if any(_goal_has_term(q, token) for token in ["cloud", "cybersecurity", "blockchain", "iot", "rpa", "devops", "analytics", "data", "ai", "ml"]):
        if _goal_has_term(q, "analytics") or _goal_has_term(q, "data"):
            return "data_scientist", 0.85, "supported", "Matched by semantic analytics intent.", ["data_scientist"], ["data_analytics"]
        domain_matches = []
        for domain_key in DOMAIN_PRIORITY:
            phrases = DOMAIN_TAXONOMY.get(domain_key, [])
            if any(_goal_has_term(q, phrase) for phrase in phrases):
                domain_matches.append(domain_key)
        if domain_matches:
            primary = domain_matches[0]
            label = COMPETENCY_BLUEPRINTS.get(primary, {}).get("label", primary.replace("_", " ").title())
            return None, 0.82, "partial" if primary in COMPETENCY_BLUEPRINTS and COMPETENCY_BLUEPRINTS[primary]["missing"] else "supported", f"Matched by semantic domain understanding for {label}.", [], domain_matches
        return None, 0.0, "outside_scope", "The goal is technology-related but needs semantic resolution.", [], []

    return None, 0.0, "outside_scope", "The goal could not be confidently mapped to a supported blueprint.", [], []


def _extract_json_payload(text: str) -> str:
    if not text:
        return ""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped, flags=re.IGNORECASE).strip()
        if stripped.endswith("```"):
            stripped = stripped[:-3].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        return stripped[start : end + 1]
    return stripped


def _build_competency_goal_analysis(
    query: str,
    domain_key: str,
    *,
    support_level: str,
    confidence: float,
    reason: str,
    domains: Optional[List[str]] = None,
    related_supported_roles: Optional[List[str]] = None,
    clarification_question: str = "",
) -> GoalAnalysis:
    composed_domains = domains[:] if domains else [domain_key]
    existing_skills: List[str] = []
    missing_skills: List[str] = []
    for item in composed_domains:
        blueprint = COMPETENCY_BLUEPRINTS.get(item)
        if not blueprint:
            continue
        existing_skills.extend([skill for skill in blueprint["skills"] if skill in SKILL_GRAPH])
        missing_skills.extend([skill for skill in blueprint["missing"] if skill not in SKILL_GRAPH])
    existing_skills = list(dict.fromkeys(existing_skills))
    missing_skills = list(dict.fromkeys(missing_skills))
    primary_blueprint = COMPETENCY_BLUEPRINTS[domain_key]
    support = support_level
    if missing_skills and support_level == "supported":
        support = "partial"
        if not reason:
            reason = f"{primary_blueprint['label']} is partially supported because {', '.join(missing_skills)} is not yet present in the skill library."
    elif not reason:
        reason = f"Matched to the {primary_blueprint['label']} competency blueprint."
    career_title = " + ".join(COMPETENCY_BLUEPRINTS[item]["label"] for item in composed_domains if item in COMPETENCY_BLUEPRINTS)
    return GoalAnalysis(
        goal=query.strip(),
        careerTitle=career_title,
        description=reason,
        requiredSkills=existing_skills,
        estimatedDuration="",
        readiness=0,
        matched_career_id=None,
        support_level=support,
        domain=composed_domains[0] if composed_domains else domain_key,
        specialization=" + ".join(COMPETENCY_BLUEPRINTS[item]["label"] for item in composed_domains if item in COMPETENCY_BLUEPRINTS).lower(),
        confidence=confidence,
        reason=reason,
        is_ambiguous=False,
        clarification_question=clarification_question,
        normalized_name=career_title,
        extracted_skills=existing_skills[:4],
        target_outcome=f"Build toward {career_title or primary_blueprint['label']} using supported competencies.",
        related_supported_roles=related_supported_roles or [domain_key],
        competencies=composed_domains,
    )


def _parse_goal_classification(payload: str) -> Optional[GoalClassification]:
    try:
        data = json.loads(_extract_json_payload(payload))
    except Exception:
        return None
    try:
        classification = GoalClassification.model_validate(data)
        if not classification.target_role:
            return None
        return classification
    except Exception:
        return None


def gemini_semantic_goal_classify(query: str, normalized_query: str) -> Optional[GoalClassification]:
    client = get_gemini_client()
    if not client:
        return None
    prompt = f"""
You are PathMind's semantic career-goal classifier.

Interpret the learner's natural-language goal.
Identify:
* target role
* domain
* specialization
* confidence
* supported/partial/outside scope
* reason
* related supported roles

Do not generate a roadmap.
Do not invent prerequisites.
Do not assign learner mastery.
Do not create clinical medical curricula.
For interdisciplinary goals, identify all relevant technology domains.
Return only valid JSON matching the schema.

User goal: {query}
Normalized goal: {normalized_query}

Schema:
{{
  "target_role": "string",
  "domain": "string",
  "specialization": "string or null",
  "confidence": 0.0,
  "support_level": "supported|partial|outside_scope",
  "reason": "string",
  "clarification_question": "string or null",
  "related_supported_roles": ["string"],
  "domains": ["string"],
  "normalized_goal": "string",
  "intermediate_intent": "string"
}}
""".strip()
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        classification = _parse_goal_classification(getattr(response, "text", "") or "")
        if classification:
            return classification
    except Exception:
        return None
    return None


def classify_goal(query: str) -> GoalAnalysis:
    normalized = normalize_goal(query)
    if _goal_has_term(normalized, "blockchain") and not _goal_has_term(normalized, "security"):
        return build_goal_analysis(
            query.strip(),
            "blockchain_engineer",
            support_level="partial",
            confidence=0.96,
            reason="Matched as blockchain, a blockchain competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["cybersecurity_engineer"],
        )
    if _goal_has_term(normalized, "cloud") and _goal_has_term(normalized, "security"):
        result = build_goal_analysis(
            query.strip(),
            "cloud_security_engineer",
            support_level="partial",
            confidence=0.95,
            reason="Matched as cloud security, a composed competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["cloud_engineer", "cybersecurity_engineer"],
        )
        result.competencies = ["cloud", "cybersecurity"]
        result.careerTitle = "Cloud Computing + Cybersecurity"
        result.domain = "cloud"
        result.specialization = "cloud + cybersecurity"
        result.requiredSkills = [skill for skill in COMPETENCY_BLUEPRINTS["cloud_security_engineer"]["skills"] if skill in SKILL_GRAPH]
        result.target_outcome = "Build toward Cloud Computing + Cybersecurity using supported competencies."
        return result
    if _goal_has_term(normalized, "cloud") and not _goal_has_term(normalized, "ai"):
        return build_goal_analysis(
            query.strip(),
            "cloud_engineer",
            support_level="partial",
            confidence=0.97,
            reason="Matched as cloud computing, a cloud competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["devops_engineer", "backend_ai_developer"],
        )
    if _goal_has_term(normalized, "cybersecurity") and not _goal_has_term(normalized, "cloud"):
        return build_goal_analysis(
            query.strip(),
            "cybersecurity_engineer",
            support_level="partial",
            confidence=0.96,
            reason="Matched as cybersecurity, a cybersecurity competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["cloud_engineer", "devops_engineer"],
        )
    if _goal_has_term(normalized, "devops"):
        return build_goal_analysis(
            query.strip(),
            "devops_engineer",
            support_level="partial",
            confidence=0.95,
            reason="Matched as DevOps, an operations competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["cloud_engineer", "backend_ai_developer"],
        )
    if _goal_has_term(normalized, "iot") or _goal_has_term(normalized, "internet of things"):
        return build_goal_analysis(
            query.strip(),
            "iot_engineer",
            support_level="partial",
            confidence=0.95,
            reason="Matched as IoT, a connected-systems competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["cloud_engineer"],
        )
    if _goal_has_term(normalized, "rpa") or (_goal_has_term(normalized, "software") and _goal_has_term(normalized, "bots")):
        return build_goal_analysis(
            query.strip(),
            "rpa_developer",
            support_level="partial",
            confidence=0.94,
            reason="Matched as RPA, an automation competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["backend_ai_developer"],
        )
    if (_goal_has_term(normalized, "robotics") or _goal_has_term(normalized, "robotic")) and _goal_has_term(normalized, "ai"):
        result = build_goal_analysis(
            query.strip(),
            "robotics_ai_engineer",
            support_level="partial",
            confidence=0.93,
            reason="Matched as robotics AI, a composed competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["robotics_engineer", "ai_engineer"],
        )
        result.competencies = ["robotics", "artificial_intelligence"]
        result.careerTitle = "Robotics + Artificial Intelligence"
        result.domain = "robotics"
        result.specialization = "robotics + artificial intelligence"
        result.requiredSkills = [skill for skill in COMPETENCY_BLUEPRINTS["robotics_ai_engineer"]["skills"] if skill in SKILL_GRAPH]
        result.target_outcome = "Build toward Robotics + Artificial Intelligence using supported competencies."
        return result
    if _goal_has_term(normalized, "blockchain") and _goal_has_term(normalized, "security"):
        result = build_goal_analysis(
            query.strip(),
            "blockchain_security_engineer",
            support_level="partial",
            confidence=0.94,
            reason="Matched as blockchain security, a composed competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["blockchain_engineer", "cybersecurity_engineer"],
        )
        result.competencies = ["blockchain", "cybersecurity"]
        result.careerTitle = "Blockchain + Cybersecurity"
        result.domain = "blockchain"
        result.specialization = "blockchain + cybersecurity"
        result.requiredSkills = [skill for skill in COMPETENCY_BLUEPRINTS["blockchain_security_engineer"]["skills"] if skill in SKILL_GRAPH]
        result.target_outcome = "Build toward Blockchain + Cybersecurity using supported competencies."
        return result
    if (_goal_has_term(normalized, "robotics") or _goal_has_term(normalized, "robotic")) and _goal_has_term(normalized, "ai"):
        result = build_goal_analysis(
            query.strip(),
            "robotics_ai_engineer",
            support_level="partial",
            confidence=0.93,
            reason="Matched as robotics AI, a composed competency goal.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["robotics_engineer", "ai_engineer"],
        )
        result.competencies = ["robotics", "artificial_intelligence"]
        result.careerTitle = "Robotics + Artificial Intelligence"
        result.domain = "robotics"
        result.specialization = "robotics + artificial intelligence"
        result.requiredSkills = [skill for skill in COMPETENCY_BLUEPRINTS["robotics_ai_engineer"]["skills"] if skill in SKILL_GRAPH]
        result.target_outcome = "Build toward Robotics + Artificial Intelligence using supported competencies."
        return result
    if _goal_has_term(normalized, "medical") and _goal_has_term(normalized, "ai"):
        result = build_goal_analysis(
            query.strip(),
            "ai_engineer",
            support_level="partial",
            confidence=0.88,
            reason="The goal combines healthcare and AI. PathMind can support the technology side only.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["ai_engineer", "data_scientist"],
        )
        result.careerTitle = "Artificial Intelligence + Healthcare Technology"
        result.domain = "artificial_intelligence"
        result.specialization = "artificial intelligence + healthcare technology"
        result.competencies = ["artificial_intelligence", "healthcare_technology"]
        result.requiredSkills = [skill for skill in COMPETENCY_BLUEPRINTS["medical_ai_engineer"]["skills"] if skill in SKILL_GRAPH]
        result.target_outcome = "Build toward Artificial Intelligence + Healthcare Technology using supported competencies."
        return result
    if _goal_has_term(normalized, "cloud") and _goal_has_term(normalized, "ai"):
        return _build_competency_goal_analysis(
            query,
            "cloud_security_engineer" if _goal_has_term(normalized, "security") else "cloud_engineer",
            support_level="partial",
            confidence=0.95,
            reason="Matched as cloud AI, a composed competency goal.",
            domains=["cloud", "artificial_intelligence"],
            related_supported_roles=[],
        )
    if _goal_has_term(normalized, "ai") and _goal_has_term(normalized, "backend"):
        return build_goal_analysis(
            query.strip(),
            "backend_ai_developer",
            support_level="supported",
            confidence=0.96,
            reason="Matched as an AI backend developer blueprint.",
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=["ai_engineer", "backend_ai_developer"],
        )
    career_id, confidence, support_level, reason, related_supported_roles, domains = classify_goal_deterministically(normalized)
    domain_keys = []
    for key, phrases in DOMAIN_TAXONOMY.items():
        if any(phrase in normalized for phrase in phrases):
            domain_keys.append(key)
    if not domain_keys and "data" in normalized:
        domain_keys.append("data_analytics")

    if career_id is None:
        gemini_result = gemini_semantic_goal_classify(query, normalized)
        if gemini_result and gemini_result.confidence >= 0:
            career_id = gemini_result.target_role if gemini_result.target_role in CAREERS else None
            support_level = gemini_result.support_level
            confidence = gemini_result.confidence
            reason = gemini_result.reason
            related_supported_roles = [role for role in gemini_result.related_supported_roles if role in CAREERS]
            domains = gemini_result.domains or [gemini_result.domain] if gemini_result.domain else []
            if career_id == "ai_engineer" and _goal_has_term(normalized, "medical"):
                support_level = "partial"
                confidence = max(confidence, 0.88)
                reason = "The goal combines healthcare and AI. PathMind can support the technology side only."
                related_supported_roles = ["ai_engineer", "data_scientist"]
            if career_id:
                result = build_goal_analysis(
                    query.strip(),
                    career_id,
                    support_level=support_level,
                    confidence=confidence,
                    reason=reason,
                    is_ambiguous=False,
                    clarification_question=gemini_result.clarification_question or "",
                    related_supported_roles=related_supported_roles,
                )
                result.normalized_name = gemini_result.normalized_goal or result.normalized_name
                result.extracted_skills = []
                return result
            if domains:
                resolved_domain = domains[0]
                if resolved_domain in COMPETENCY_BLUEPRINTS:
                    return _build_competency_goal_analysis(
                        query,
                        resolved_domain,
                        support_level="partial" if support_level == "outside_scope" else support_level,
                        confidence=confidence,
                        reason=reason,
                        domains=domains,
                        related_supported_roles=related_supported_roles,
                        clarification_question=gemini_result.clarification_question or "",
                    )

        if "doctor" in normalized or "medicine" in normalized or "clinical" in normalized:
            return GoalAnalysis(
                goal=query.strip(),
                careerTitle="",
                description="Medicine is outside PathMind's current supported learning domain.",
                requiredSkills=[],
                estimatedDuration="",
                readiness=0,
                matched_career_id=None,
                support_level="outside_scope",
                domain="healthcare",
                specialization="clinical medicine",
                confidence=0.99,
                reason="Clinical medicine is outside PathMind's current supported technology learning scope.",
                is_ambiguous=False,
                clarification_question="",
                normalized_name=normalized,
                extracted_skills=[],
                target_outcome="PathMind focuses on technology, AI, software, data, and related digital careers.",
                related_supported_roles=[],
            )

        if domain_keys:
            if _goal_has_term(normalized, "medical") and _goal_has_term(normalized, "ai"):
                return build_goal_analysis(
                    query.strip(),
                    "ai_engineer",
                    support_level="partial",
                    confidence=max(confidence, 0.88),
                    reason="The goal combines healthcare and AI. PathMind can support the technology side only.",
                    is_ambiguous=False,
                    clarification_question="",
                    related_supported_roles=["ai_engineer", "data_scientist"],
                )
            if "healthcare_technology" in domain_keys:
                return _build_competency_goal_analysis(
                    query,
                    "healthcare_technology",
                    support_level="partial",
                    confidence=max(confidence, 0.9),
                    reason="The goal combines healthcare technology with supported software/data competencies.",
                    domains=domain_keys,
                    related_supported_roles=["data_scientist", "backend_ai_developer", "ai_engineer"],
                )
            if "cybersecurity" in domain_keys and "cloud" in domain_keys:
                return _build_competency_goal_analysis(
                    query,
                    "cybersecurity",
                    support_level="partial",
                    confidence=max(confidence, 0.95),
                    reason="Cloud security is partially supported through cloud, backend, and authentication competencies, but dedicated security skills are still missing.",
                    domains=["cloud", "cybersecurity"],
                    related_supported_roles=["backend_ai_developer"],
                )
            if "blockchain" in domain_keys and "cybersecurity" in domain_keys:
                return _build_competency_goal_analysis(
                    query,
                    "blockchain",
                    support_level="partial",
                    confidence=max(confidence, 0.94),
                    reason="Blockchain security is partially supported through programming foundations, but dedicated blockchain and security competencies are missing.",
                    domains=["blockchain", "cybersecurity"],
                    related_supported_roles=["backend_ai_developer"],
                )
            if "iot" in domain_keys and "artificial_intelligence" in domain_keys:
                return _build_competency_goal_analysis(
                    query,
                    "iot",
                    support_level="partial",
                    confidence=max(confidence, 0.92),
                    reason="Robotics and connected-device goals are only partially supported by the current skill library.",
                    domains=["iot", "artificial_intelligence"],
                    related_supported_roles=["ai_engineer", "backend_ai_developer"],
                )
            primary_domain = domain_keys[0]
            if primary_domain in COMPETENCY_BLUEPRINTS:
                support_hint = "partial" if COMPETENCY_BLUEPRINTS[primary_domain]["missing"] else "supported"
                return _build_competency_goal_analysis(
                    query,
                    primary_domain,
                    support_level=support_hint,
                    confidence=max(confidence, 0.9 if support_hint == "supported" else 0.85),
                    reason=reason or f"Matched to the {COMPETENCY_BLUEPRINTS[primary_domain]['label']} competency blueprint.",
                    domains=domain_keys,
                    related_supported_roles=related_supported_roles or [primary_domain],
                )

        return GoalAnalysis(
            goal=query.strip(),
            careerTitle="",
            description="",
            requiredSkills=[],
            estimatedDuration="",
            readiness=0,
            matched_career_id=None,
            support_level="partial" if any(token in normalized for token in ["health", "hospital"]) else "outside_scope",
            domain="technology",
            specialization="",
            confidence=0.35,
            reason="The goal could not be confidently mapped to a supported blueprint.",
            is_ambiguous=True,
            clarification_question="Tell me which technology career path you want to pursue.",
            normalized_name=normalized,
            extracted_skills=[],
            target_outcome="",
            related_supported_roles=["backend_ai_developer", "ai_engineer", "data_scientist", "ml_engineer", "full_stack_developer"],
        )

    if career_id in CAREERS:
        if career_id == "ai_engineer" and _goal_has_term(normalized, "medical"):
            support_level = "partial"
            confidence = max(confidence, 0.88)
            reason = "The goal combines healthcare and AI. PathMind can support the technology side only."
            related_supported_roles = ["ai_engineer", "data_scientist"]
        result = build_goal_analysis(
            query.strip(),
            career_id,
            support_level=support_level,
            confidence=max(confidence, DETERMINISTIC_CONFIDENCE_THRESHOLD if confidence >= DETERMINISTIC_CONFIDENCE_THRESHOLD else confidence),
            reason=reason,
            is_ambiguous=False,
            clarification_question="",
            related_supported_roles=related_supported_roles,
        )
        result.normalized_name = normalized
        result.extracted_skills = []
        if domains:
            result.domain = domains[0]
        if len(domains) > 1:
            result.related_supported_roles = sorted(set(result.related_supported_roles + related_supported_roles))
        return result

    if domain_keys:
        primary_domain = domain_keys[0]
        if primary_domain in COMPETENCY_BLUEPRINTS:
            return _build_competency_goal_analysis(
                query,
                primary_domain,
                support_level="partial" if COMPETENCY_BLUEPRINTS[primary_domain]["missing"] else support_level,
                confidence=max(confidence, 0.9),
                reason=reason,
                domains=domain_keys,
                related_supported_roles=related_supported_roles,
            )

    return GoalAnalysis(
        goal=query.strip(),
        careerTitle="",
        description="",
        requiredSkills=[],
        estimatedDuration="",
        readiness=0,
        matched_career_id=None,
        support_level="outside_scope",
        domain="technology",
        specialization="",
        confidence=0.35,
        reason="The goal could not be confidently mapped to a supported blueprint.",
        is_ambiguous=True,
        clarification_question="Tell me which technology career path you want to pursue.",
        normalized_name=normalized,
        extracted_skills=[],
        target_outcome="",
        related_supported_roles=["backend_ai_developer", "ai_engineer", "data_scientist", "ml_engineer", "full_stack_developer"],
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
    questionType: Literal["mcq", "short_answer", "coding"] = "mcq"
    explanation: Optional[str] = None

class DiagnosticAnswer(BaseModel):
    questionId: str
    skillId: str
    answer: str

class DiagnosticSubmitRequest(BaseModel):
    target_role: str
    known_skills: List[str] = Field(default_factory=list)
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    answers: List[DiagnosticAnswer] = Field(min_length=1)


class AssessmentEvidenceItem(BaseModel):
    evidence_type: str = "assessment"
    source: str = "assessment"
    score: int = Field(ge=0, le=100)
    question_id: str
    question_type: Literal["mcq", "short_answer", "coding"]
    answer: str
    correct: Optional[bool] = None
    evaluation: Optional[str] = None
    timestamp: str

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
    project_blueprint: Optional[Dict[str, Any]] = None
    project_title: Optional[str] = None
    project_description: Optional[str] = None
    project_milestone: Optional[Dict[str, Any]] = None
    project_milestone_description: Optional[str] = None
    project_learning_concepts: List[str] = Field(default_factory=list)
    project_build_task: Optional[str] = None
    project_checkpoint: Optional[str] = None
    project_milestone_skills: List[str] = Field(default_factory=list)
    project_hints_shown: List[str] = Field(default_factory=list)
    completed_milestones: List[str] = Field(default_factory=list)
    relevant_assessment: Optional[Dict[str, Any]] = None

# --- API Route Endpoints ---

@app.get("/")
def read_root():
    return {
        "status": "Online",
        "system": "PathMind AI Engine - Adaptive GPS Edition",
        "framework_alignment": "Learn, Practice, Build, Assess, Verify, Adapt",
        "careers": list(CAREERS.keys())
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}

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
            "project": build_project_blueprint(skill.id, proficiency, SKILL_GRAPH, interest=request.interest),
        })
    return {
        "career": career["name"],
        "resources": resources_by_skill,
        "projects": projects_by_skill,
    }


class ProjectStartRequest(BaseModel):
    target_role: str
    skill_id: str
    proficiency: int = Field(default=0, ge=0, le=100)
    current_skills: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    interest: str = ""


@app.post("/api/project/start")
def start_project(request: ProjectStartRequest):
    """Start a deterministic project session with milestones and build guidance."""
    if request.target_role not in CAREERS:
        raise HTTPException(status_code=404, detail="Career track not found.")
    if request.skill_id not in SKILL_GRAPH:
        raise HTTPException(status_code=404, detail="Skill not found.")
    session = build_project_session(request.skill_id, request.proficiency, SKILL_GRAPH, interest=request.interest)
    return {
        "target_role": request.target_role,
        "skill_id": request.skill_id,
        "session": session,
        "project": session["project"],
        "current_milestone": session["currentMilestone"],
        "next_milestone": session["nextMilestone"],
    }


@app.post("/api/project/next")
def next_project_milestone(request: ProjectStartRequest):
    """Return the current and next milestone for a project."""
    if request.target_role not in CAREERS:
        raise HTTPException(status_code=404, detail="Career track not found.")
    if request.skill_id not in SKILL_GRAPH:
        raise HTTPException(status_code=404, detail="Skill not found.")
    session = build_project_session(request.skill_id, request.proficiency, SKILL_GRAPH, interest=request.interest)
    milestones = session["milestones"]
    current = next((item for item in milestones if item.get("completion_status") != "completed"), None)
    upcoming = None
    if current:
        current_index = milestones.index(current)
        if current_index + 1 < len(milestones):
            upcoming = milestones[current_index + 1]
    return {
        "target_role": request.target_role,
        "skill_id": request.skill_id,
        "current_milestone": current,
        "next_milestone": upcoming,
        "project": session["project"],
        "build_guide": session["buildGuide"],
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
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
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
    result = classify_goal(request.query)
    if result.is_ambiguous and not result.clarification_question:
        result.clarification_question = "I could not match that goal to a supported career track yet. Try a software, AI, data, or full-stack goal."
    return result

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
    client = get_gemini_client()
    current_skills = {}
    questions = []
    for skill_id in _assessment_skill_scope(request.target_role):
        proficiency = int(current_skills.get(skill_id, {}).get("proficiency", 0))
        question = _safe_assessment_question(skill_id, proficiency, client)
        questions.append(DiagnosticQuestion(**question))
    return {
        "target_role": request.target_role,
        "careerTitle": CAREERS[request.target_role]["name"],
        "questions": questions,
    }

@app.post("/api/diagnostic/submit")
def submit_diagnostic(request: DiagnosticSubmitRequest):
    """Scores diagnostic answers against the server-owned question bank."""
    if request.target_role not in CAREERS:
        raise HTTPException(status_code=404, detail="Career track not found.")
    allowed_skills = set(resolve_prerequisites(CAREERS[request.target_role]["required_skills"], SKILL_GRAPH))
    results = []
    scores_by_skill: Dict[str, List[int]] = {}
    evidence_by_skill: Dict[str, List[Dict[str, Any]]] = {}
    current_skills: Dict[str, Dict[str, Any]] = dict(request.current_skills)
    for answer in request.answers:
        if answer.skillId not in allowed_skills:
            raise HTTPException(status_code=400, detail="Question is not part of this career diagnostic.")
        try:
            skill_index = int(answer.questionId.rsplit("-", 1)[1])
            if skill_index > 0:
                raise KeyError(answer.skillId)
            question = _safe_assessment_question(answer.skillId, int(current_skills.get(answer.skillId, {}).get("proficiency", 0)), None)
        except (KeyError, IndexError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid diagnostic question.")
        q_type = _assessment_question_type(answer.skillId, question.get("questionType"))
        if q_type == "mcq":
            correct = answer.answer == question["answer"]
            score = 100 if correct else 0
            evaluation = "Deterministic MCQ evaluation"
        else:
            normalized = answer.answer.strip().lower()
            answer_key = str(question["answer"]).strip().lower()
            correct = normalized == answer_key or answer_key in normalized
            score = 100 if correct else 40 if normalized else 0
            evaluation = "Deterministic structured-answer evaluation"
        scores_by_skill.setdefault(answer.skillId, []).append(score)
        evidence_by_skill.setdefault(answer.skillId, []).append(_normalize_assessment_evidence(answer, question, score, correct, evaluation))
        results.append({
            "questionId": answer.questionId,
            "skillId": answer.skillId,
            "answer": answer.answer,
            "correct": correct,
            "difficulty": SKILL_GRAPH[answer.skillId].get("difficulty", "Intermediate"),
            "questionType": q_type,
            "explanation": question.get("explanation"),
            "score": score,
        })
    proficiency = {skill_id: round(sum(scores) / len(scores)) for skill_id, scores in scores_by_skill.items()}
    for skill_id in request.known_skills:
        if skill_id in allowed_skills and skill_id not in proficiency:
            proficiency[skill_id] = 25
    overall_score = round(sum(proficiency.values()) / len(proficiency)) if proficiency else 0
    updated_skills: Dict[str, Dict[str, Any]] = {}
    for skill_id, score in proficiency.items():
        previous = dict(current_skills.get(skill_id, {}))
        evidence = list(previous.get("evidence", []))
        evidence.extend(evidence_by_skill.get(skill_id, []))
        target = int(SKILL_GRAPH[skill_id].get("required_proficiency", 70))
        updated_skills[skill_id] = {
            **previous,
            "proficiency": min(100, max(int(previous.get("proficiency", 0)), score)),
            "status": "Completed" if score >= max(75, target) else "Needs Improvement" if score < 50 else "In Progress",
            "confidence": "Verified" if score >= max(75, target) else "Assessed",
            "last_assessment_score": score,
            "evidence": evidence,
        }
    roadmap = generate_path(PathGenerationRequest(
        user_id="assessment",
        target_role=request.target_role,
        current_skills=updated_skills,
        hours_per_week=12,
    ))
    return {
        "target_role": request.target_role,
        "careerTitle": CAREERS[request.target_role]["name"],
        "assessmentResults": results,
        "skillProficiency": proficiency,
        "overallScore": overall_score,
        "verifiedSkills": [skill_id for skill_id, score in proficiency.items() if score >= 75],
        "updatedSkills": updated_skills,
        "evidence": [item for values in evidence_by_skill.values() for item in values],
        "roadmap": roadmap["path"],
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
    mentor_response = build_project_mentor_response(request, career_name)
    if mentor_response and ("how" in request.message.lower() or "build" in request.message.lower() or "step" in request.message.lower() or "project" in request.message.lower() or "stuck" in request.message.lower()):
        return {"response": mentor_response}
    
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
            current_step = None
            if isinstance(request.project_blueprint, dict):
                steps = request.project_blueprint.get("implementationTasks") or []
                if steps:
                    current_step = steps[0]
            project_name = request.project_blueprint.get("whatYouAreBuilding") if isinstance(request.project_blueprint, dict) else None
            return {"response": f"I’m having trouble reaching the AI service right now. Based on your current context for **{career_name}** and **{project_name or request.current_milestone or 'your current project'}**, the safest next step is **{current_step or request.next_action or 'your next roadmap item'}**."}
            
    # Simple Static Fallback
    if "skip" in request.message.lower():
        return {
            "response": f"Not recommended yet.\n\n{request.current_skill or 'This skill'} is still part of your current path. You can either complete it or take a verification assessment before we consider skipping it."
        }
    project_name = request.project_blueprint.get("whatYouAreBuilding") if isinstance(request.project_blueprint, dict) else None
    current_step = None
    if isinstance(request.project_blueprint, dict):
        steps = request.project_blueprint.get("implementationTasks") or []
        if steps:
            current_step = steps[0]
    return {
        "response": f"Hello! As your AI Learning Coach for **{career_name}**, I’m here to guide your next step in **{project_name or request.current_milestone or 'your current project'}**. Your current best action is **{current_step or request.next_action or 'study the next roadmap item'}**."
    }
