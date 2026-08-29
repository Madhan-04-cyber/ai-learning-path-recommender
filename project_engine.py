from __future__ import annotations

from typing import Any, Dict, List


def _skill_title(skill_id: str, skill_graph: Dict[str, Dict[str, Any]]) -> str:
    return skill_graph.get(skill_id, {}).get("title", skill_id.replace("_", " ").title())


def _skill_domain(skill_id: str, skill_graph: Dict[str, Dict[str, Any]]) -> str:
    category = skill_graph.get(skill_id, {}).get("category")
    if category:
        return category
    lowered = skill_id.lower()
    if any(token in lowered for token in ["cloud", "deploy", "docker"]):
        return "cloud"
    if any(token in lowered for token in ["security", "auth", "incident"]):
        return "security"
    if any(token in lowered for token in ["sql", "database", "postgres"]):
        return "data"
    if any(token in lowered for token in ["ml", "ai", "rag", "model"]):
        return "ai"
    return "software"


def _stage_from_proficiency(proficiency: int) -> str:
    if proficiency < 45:
        return "foundation"
    if proficiency < 75:
        return "applied"
    return "advanced"


def _template(skill_title: str, stage: str) -> Dict[str, Any]:
    if stage == "foundation":
        return {
            "title": f"{skill_title} REST API",
            "difficulty": "Beginner",
            "estimatedTime": "4-6 hours",
            "goal": "Build a small working project while learning the core competency step by step.",
            "expectedOutput": "A simple working build with validation and a repeatable checkpoint.",
            "evaluationCriteria": ["Works end to end", "Uses validation", "Produces a correct result"],
            "theme": "starter",
        }
    if stage == "applied":
        return {
            "title": f"{skill_title} ML Prediction API",
            "difficulty": "Intermediate",
            "estimatedTime": "6-10 hours",
            "goal": "Build a structured project that connects the target skill to its prerequisite skills.",
            "expectedOutput": "A documented project with a clear implementation sequence and checkpoints.",
            "evaluationCriteria": ["Matches the project contract", "Connects prerequisite skills", "Records evidence"],
            "theme": "guided-build",
        }
    return {
        "title": f"{skill_title} RAG-powered AI Backend",
        "difficulty": "Advanced",
        "estimatedTime": "10-18 hours",
        "goal": "Build a production-style learning environment with milestones, evidence, and verification.",
        "expectedOutput": "A multi-step project with milestone checkpoints and a final assessed outcome.",
        "evaluationCriteria": ["Milestones are completed in order", "Evidence is recorded", "Verification passes"],
        "theme": "production-project",
    }


def _interest_theme(skill_id: str, interest: str) -> Dict[str, str]:
    interest = interest.lower().strip()
    if skill_id in {"data_scientist", "numpy_pandas", "data_visualization", "sql_basics"}:
        if any(token in interest for token in ["cricket", "sports", "ipl"]):
            return {"title": "IPL Player Performance Analytics", "theme": "sports-analytics"}
        if any(token in interest for token in ["finance", "stock", "market"]):
            return {"title": "Financial Market Data Analysis", "theme": "financial-analytics"}
        if any(token in interest for token in ["health", "healthcare", "medical"]):
            return {"title": "Healthcare Data Analytics", "theme": "healthcare-analytics"}
    return {}


def build_project_blueprint(skill_id: str, proficiency: int, skill_graph: Dict[str, Dict[str, Any]], interest: str = "") -> Dict[str, Any]:
    skill_title = _skill_title(skill_id, skill_graph)
    metadata = skill_graph.get(skill_id, {})
    prerequisites = list(metadata.get("prerequisites", []))
    stage = _stage_from_proficiency(proficiency)
    template = _template(skill_title, stage)
    domain = _skill_domain(skill_id, skill_graph)
    themed = _interest_theme(skill_id, interest)
    if themed.get("title"):
        template["title"] = themed["title"]
        template["theme"] = themed.get("theme", template["theme"])

    setup = [
        "Create the project folder and baseline files.",
        "Install the required runtime and dependencies.",
        "Define the input and output contract for the milestone.",
        "Run a first verification check before building more logic.",
    ]
    if stage == "advanced":
        setup.append("Prepare a review checklist for milestone evidence and validation.")

    milestone_plan: List[Dict[str, Any]] = [
        {
            "milestone_id": f"{skill_id}:plan",
            "title": "Plan the scope",
            "description": f"Understand what the {skill_title} project must demonstrate before building.",
            "objective": f"Understand what the {skill_title} project must demonstrate.",
            "required_skills": [skill_id, *prerequisites[:1]],
            "concepts": [skill_title],
            "learning_concepts": [skill_title, "Scope definition", "Success criteria"],
            "prerequisites": prerequisites[:1],
            "build_task": "Write the project brief and acceptance criteria.",
            "learning_tasks": [f"Review the {skill_title} concept and its role in the project."],
            "practice_tasks": ["Outline the desired output and success criteria."],
            "implementation_steps": ["Write the project brief and acceptance criteria."],
            "checkpoint": "A concise project scope is written and reviewed.",
            "expected_output": "A written project plan.",
            "common_mistakes": ["Skipping the project brief", "Trying to build before defining success criteria"],
            "hints": ["Think about the problem before the code.", "A clear scope prevents rework."],
            "unlock_conditions": ["Project objective is written"],
            "estimated_minutes": 20,
            "status": "AVAILABLE",
            "completion_status": "available",
        },
        {
            "milestone_id": f"{skill_id}:build",
            "title": "Implement the core flow",
            "description": "Build the first working version of the project.",
            "objective": "Build the first working version of the project.",
            "required_skills": [skill_id, *prerequisites[:2]],
            "concepts": [skill_title, *[_skill_title(item, skill_graph) for item in prerequisites[:2]]],
            "learning_concepts": [skill_title, *[_skill_title(item, skill_graph) for item in prerequisites[:2]], "Implementation order"],
            "prerequisites": [f"{skill_id}:plan"],
            "build_task": "Implement the smallest end-to-end working path.",
            "learning_tasks": ["Learn the minimum concepts needed for this step."],
            "practice_tasks": ["Solve a small focused exercise before coding the milestone."],
            "implementation_steps": ["Implement the smallest end-to-end working path."],
            "checkpoint": "The core path runs once without errors.",
            "expected_output": "A working milestone with visible output.",
            "common_mistakes": ["Skipping validation", "Overengineering the first pass"],
            "hints": ["Start with one input and one output.", "Build the smallest thing that can work."],
            "unlock_conditions": ["Plan milestone completed"],
            "estimated_minutes": 40,
            "status": "LOCKED" if stage == "foundation" else "AVAILABLE",
            "completion_status": "locked" if stage == "foundation" else "available",
        },
        {
            "milestone_id": f"{skill_id}:verify",
            "title": "Checkpoint and verify",
            "description": "Validate the implementation and capture evidence.",
            "objective": "Validate the implementation and capture evidence.",
            "required_skills": [skill_id],
            "concepts": [skill_title],
            "learning_concepts": [skill_title, "Verification", "Evidence"],
            "prerequisites": [f"{skill_id}:build"],
            "build_task": "Submit the milestone evidence and assessment.",
            "learning_tasks": ["Review the verification criteria."],
            "practice_tasks": ["Run the checks and fix the failures."],
            "implementation_steps": ["Submit the milestone evidence and assessment."],
            "checkpoint": "Assessment and evidence are recorded successfully.",
            "expected_output": "A completed, verified milestone with evidence.",
            "common_mistakes": ["Treating the checkpoint as a formality", "Submitting without testing"],
            "hints": ["Use the checkpoint to prove the build works.", "Evidence should show what you built."],
            "unlock_conditions": ["Core flow implemented"],
            "estimated_minutes": 30,
            "status": "LOCKED" if stage == "foundation" else "AVAILABLE",
            "completion_status": "locked" if stage == "foundation" else "available",
        },
    ]

    if stage == "advanced":
        milestone_plan.insert(
            2,
            {
                "milestone_id": f"{skill_id}:integrate",
                "title": "Integrate the full workflow",
                "description": "Connect the core flow to the wider project outcome.",
                "objective": "Connect the core flow to the wider project outcome.",
                "required_skills": [skill_id, *prerequisites],
                "concepts": [skill_title, *[_skill_title(item, skill_graph) for item in prerequisites]],
                "learning_concepts": [skill_title, *[_skill_title(item, skill_graph) for item in prerequisites], "End-to-end flow"],
                "prerequisites": [f"{skill_id}:build"],
                "build_task": "Integrate the project pieces and remove placeholder logic.",
                "learning_tasks": ["Understand how the project step connects to the final outcome."],
                "practice_tasks": ["Extend the implementation to handle the full workflow."],
                "implementation_steps": ["Integrate the project pieces and remove placeholder logic."],
                "checkpoint": "The integrated workflow passes the configured checks.",
                "expected_output": "A complete project flow ready for assessment.",
                "common_mistakes": ["Leaving placeholder logic", "Not connecting the workflow end to end"],
                "hints": ["Connect each completed part to the next.", "Make sure the final output is visible."],
                "unlock_conditions": ["Core flow completed"],
                "estimated_minutes": 45,
                "status": "LOCKED",
                "completion_status": "locked",
            },
        )

    if stage == "foundation" and milestone_plan:
        milestone_plan[0]["completion_status"] = "available"

    return {
        "project_id": f"{skill_id}:{stage}",
        "title": template["title"],
        "domain": domain,
        "career": skill_title,
        "description": template["goal"],
        "difficulty": template["difficulty"],
        "estimatedTime": template["estimatedTime"],
        "required_skills": [skill_id, *prerequisites],
        "optional_skills": [],
        "milestones": milestone_plan,
        "expected_outcomes": [template["expectedOutput"]],
        "assessment": {
            "type": "project_checkpoints",
            "criteria": template["evaluationCriteria"],
            "requires_evidence": True,
        },
        "project_theme": template["theme"],
        "projectBlueprint": {
            "whatYouAreBuilding": template["goal"],
            "requirements": [_skill_title(skill_id, skill_graph), *[_skill_title(item, skill_graph) for item in prerequisites[:2]]],
            "techStack": [_skill_title(skill_id, skill_graph), "Validation", "Evidence"],
            "architecture": ["Project brief", "Milestone build", "Checkpoint", "Evidence"],
            "setup": setup,
            "implementationTasks": [
                "Plan the milestone and define success criteria.",
                "Build the smallest working version.",
                "Verify the result and record evidence.",
            ],
            "validationChecks": ["Milestone runs", "Evidence is recorded", "Prerequisites remain intact"],
            "commonMistakes": ["Skipping checks", "Jumping to the final build too soon", "Treating the project like a static assignment"],
            "troubleshooting": ["Check the milestone contract first.", "Reduce the problem to the smallest working step.", "Verify prerequisites before expanding the build."],
            "currentStepGuide": [
                {"title": "Start small", "explanation": "Focus on one working step before expanding."},
                {"title": "Inspect output", "explanation": "Confirm the result matches the expected output."},
                {"title": "Record evidence", "explanation": "Write down what worked and what you verified."},
            ],
        },
    }


def build_project_session(skill_id: str, proficiency: int, skill_graph: Dict[str, Dict[str, Any]], interest: str = "") -> Dict[str, Any]:
    project = build_project_blueprint(skill_id, proficiency, skill_graph, interest=interest)
    milestones = project["milestones"]
    next_milestone = next((item for item in milestones if item["status"] != "COMPLETED"), milestones[-1] if milestones else None)
    return {
        "project": project,
        "milestones": milestones,
        "currentMilestone": next_milestone,
        "nextMilestone": next_milestone,
        "buildGuide": project["projectBlueprint"],
    }
