import unittest

from main import (
    ChatRequest,
    DiagnosticAnswer,
    DiagnosticStartRequest,
    DiagnosticSubmitRequest,
    GoalAnalysisRequest,
    analyze_goal,
    build_contextual_resources,
    build_project_mentor_response,
    chat_assistant,
    start_diagnostic,
    submit_diagnostic,
    PathGenerationRequest,
    calculateCareerReadiness,
    isCareerReady,
    generate_path,
    resolve_prerequisites,
    topological_sort,
    select_adaptive_project,
)


class LearningEngineTests(unittest.TestCase):
    def test_topological_order_places_prerequisites_first(self):
        skills = resolve_prerequisites(["fastapi"], __import__("main").SKILL_GRAPH)
        ordered = topological_sort(skills, __import__("main").SKILL_GRAPH)
        self.assertLess(ordered.index("python"), ordered.index("fastapi"))
        self.assertLess(ordered.index("http_fundamentals"), ordered.index("rest_apis"))

    def test_verified_skills_make_paths_different(self):
        beginner = generate_path(
            PathGenerationRequest(
                user_id="beginner",
                target_role="backend_ai_developer",
                current_skills={},
                hours_per_week=12,
            )
        )
        experienced = generate_path(
            PathGenerationRequest(
                user_id="experienced",
                target_role="backend_ai_developer",
                current_skills={
                    "python": {"proficiency": 90, "status": "Completed", "confidence": "Verified"},
                    "git": {"proficiency": 80, "status": "Completed", "confidence": "Verified"},
                    "sql_basics": {"proficiency": 80, "status": "Completed", "confidence": "Verified"},
                },
                hours_per_week=12,
            )
        )
        beginner_statuses = {item["id"]: item["status"] for item in beginner["path"]}
        experienced_statuses = {item["id"]: item["status"] for item in experienced["path"]}
        self.assertEqual(beginner_statuses["python"], "Available")
        self.assertEqual(experienced_statuses["python"], "Completed")
        self.assertGreater(experienced["readiness_score"], beginner["readiness_score"])

    def test_practice_feedback_changes_milestone(self):
        result = generate_path(
            PathGenerationRequest(
                user_id="learner",
                target_role="backend_ai_developer",
                current_skills={},
                hours_per_week=12,
                feedback=[{"skill_id": "python", "feedback_type": "Need more practice"}],
            )
        )
        item = next(item for item in result["path"] if item["id"] == "python")
        self.assertGreater(len(item["practice"]), len(__import__("main").SKILL_GRAPH["python"]["practice"]))

    def test_weighted_readiness_prefers_critical_dependencies(self):
        graph = {
            "model_evaluation": {"title": "Model Evaluation", "required_proficiency": 80, "prerequisites": [], "estimated_hours": 6},
            "fastapi": {"title": "FastAPI", "required_proficiency": 80, "prerequisites": ["model_evaluation"], "estimated_hours": 8},
        }
        result = calculateCareerReadiness(["model_evaluation", "fastapi"], {"model_evaluation": {"proficiency": 40, "status": "Needs Improvement"}}, graph)
        self.assertLess(result["score"], 60)
        self.assertEqual(result["biggestGap"], "Model Evaluation")
        self.assertEqual(result["biggestBlocker"], "Model Evaluation")
        self.assertIn("Model Evaluation", result["nextAction"])

    def test_career_ready_gate_requires_critical_completion(self):
        graph = {
            "python": {"title": "Python", "required_proficiency": 80, "prerequisites": []},
            "fastapi": {"title": "FastAPI", "required_proficiency": 80, "prerequisites": ["python"]},
            "postgresql": {"title": "PostgreSQL", "required_proficiency": 75, "prerequisites": ["python"]},
        }
        incomplete = isCareerReady(["python", "fastapi", "postgresql"], {"python": {"proficiency": 95, "status": "Completed"}}, graph)
        complete = isCareerReady(
            ["python", "fastapi", "postgresql"],
            {
                "python": {"proficiency": 95, "status": "Completed"},
                "fastapi": {"proficiency": 90, "status": "Completed"},
                "postgresql": {"proficiency": 85, "status": "Completed"},
            },
            graph,
        )
        self.assertFalse(incomplete["ready"])
        self.assertTrue(complete["ready"])

    def test_goal_analysis_classifies_data_analyst_as_supported(self):
        result = analyze_goal(GoalAnalysisRequest(query="I want to become a data analyst"))
        self.assertEqual(result.matched_career_id, "data_scientist")
        self.assertEqual(result.support_level, "supported")
        self.assertFalse(result.is_ambiguous)
        self.assertIn("Data Scientist", result.careerTitle)

    def test_goal_analysis_marks_doctor_out_of_scope(self):
        result = analyze_goal(GoalAnalysisRequest(query="I want to become a doctor"))
        self.assertEqual(result.support_level, "outside_scope")
        self.assertFalse(result.is_ambiguous)
        self.assertEqual(result.matched_career_id, None)

    def test_goal_analysis_marks_medical_ai_engineer_partial(self):
        result = analyze_goal(GoalAnalysisRequest(query="I want to become a medical AI engineer"))
        self.assertEqual(result.support_level, "partial")
        self.assertEqual(result.matched_career_id, "ai_engineer")

    def test_project_blueprint_has_milestones_and_guide(self):
        graph = {
            "fastapi": {"title": "FastAPI", "prerequisites": ["python"], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Intermediate", "resources": []},
            "python": {"title": "Python", "prerequisites": [], "required_proficiency": 70, "estimated_hours": 6, "difficulty": "Beginner", "resources": []},
        }
        project = select_adaptive_project("fastapi", 40, graph)
        self.assertIn("milestones", project)
        self.assertGreaterEqual(len(project["milestones"]), 3)
        self.assertIn("projectBlueprint", project)
        self.assertIn("whatYouAreBuilding", project["projectBlueprint"])

    def test_contextual_resources_include_project_reference(self):
        graph = {
            "python": {"title": "Python", "prerequisites": [], "required_proficiency": 70, "estimated_hours": 6, "difficulty": "Beginner", "resources": []},
        }
        resources = build_contextual_resources("python", graph, 10)
        self.assertTrue(any(item["type"] == "Project" for item in resources))

    def test_interest_personalizes_data_analyst_project(self):
        graph = __import__("main").SKILL_GRAPH
        project = __import__("main").build_project_blueprint("data_scientist", 20, graph, interest="cricket")
        self.assertIn("IPL", project["title"])
        self.assertEqual(project["project_theme"], "sports-analytics")

    def test_project_mentor_includes_project_and_milestone_context(self):
        request = ChatRequest(
            message="How do I start this milestone?",
            history=[],
            target_role="data_scientist",
            user_skills={"python": {"proficiency": 80, "status": "Completed"}},
            current_page="Project",
            current_milestone="Data Collection",
            current_skill="python",
            project_title="IPL Player Performance Analytics",
            project_description="Analyze IPL player data.",
            project_milestone={
                "title": "Data Collection",
                "description": "Collect match and player data.",
                "learning_concepts": ["data sourcing", "CSV ingestion"],
                "build_task": "Load IPL data",
                "checkpoint": "Data loads successfully.",
                "required_skills": ["python", "sql_basics"],
            },
            project_blueprint={
                "whatYouAreBuilding": "IPL Player Performance Analytics",
                "setup": ["Find a data source"],
                "implementationTasks": ["Load the IPL data", "Clean the records"],
                "validationChecks": ["Dataset loads successfully"],
                "troubleshooting": ["Check file paths"],
            },
            project_learning_concepts=["data sourcing", "CSV ingestion"],
            project_build_task="Load IPL data",
            project_checkpoint="Data loads successfully.",
            project_milestone_skills=["python", "sql_basics"],
            completed_milestones=["Setup"],
            relevant_assessment={"last_assessment": {"skillId": "python", "correct": True}},
        )
        response = build_project_mentor_response(request, "Data Scientist")
        self.assertIsNotNone(response)
        self.assertIn("IPL Player Performance Analytics", response)
        self.assertIn("Data Collection", response)
        self.assertIn("Data Scientist", response)
        self.assertIn("data sourcing", response)
        self.assertIn("python", response)

    def test_project_mentor_fallback_and_chat_still_work(self):
        fallback_request = ChatRequest(
            message="I am stuck and getting an error.",
            history=[],
            target_role="cloud_engineer",
            user_skills={},
            current_page="Project",
            current_milestone="Infrastructure Setup",
            current_skill="docker",
            project_title="Cloud Deployment Sandbox",
            project_blueprint={"whatYouAreBuilding": "Cloud Deployment Sandbox", "implementationTasks": ["Set up Docker"]},
        )
        mentor_response = chat_assistant(fallback_request)
        self.assertIn("Cloud Engineer", mentor_response["response"])
        self.assertIn("Cloud Deployment Sandbox", mentor_response["response"])
        self.assertIn("Set up Docker", mentor_response["response"])

        generic_request = ChatRequest(
            message="Why am I learning this?",
            history=[],
            target_role="ai_engineer",
            user_skills={},
        )
        generic_response = chat_assistant(generic_request)
        self.assertIn("AI Learning Coach", generic_response["response"])
        self.assertIn("AI Engineer", generic_response["response"])

    def test_assessment_loads_correct_learner_goal(self):
        result = start_diagnostic(DiagnosticStartRequest(target_role="data_scientist"))
        self.assertEqual(result["target_role"], "data_scientist")
        self.assertEqual(result["careerTitle"], "Data Scientist")
        self.assertTrue(result["questions"])

    def test_assessment_generates_skill_appropriate_questions(self):
        data = start_diagnostic(DiagnosticStartRequest(target_role="cloud_engineer"))
        skill_ids = {question.skillId for question in data["questions"]}
        self.assertIn("containers", skill_ids)
        self.assertIn("cloud_fundamentals", skill_ids)

    def test_assessment_scoring_and_evidence(self):
        submit = DiagnosticSubmitRequest(
            target_role="data_scientist",
            known_skills=["python"],
            current_skills={"python": {"proficiency": 20, "status": "Needs Improvement", "evidence": []}},
            answers=[DiagnosticAnswer(questionId="python-0", skillId="python", answer="Understand the core purpose of Python Programming")],
        )
        result = submit_diagnostic(submit)
        self.assertTrue(result["assessmentResults"][0]["correct"])
        self.assertIn("evidence", result)
        self.assertTrue(result["updatedSkills"]["python"]["evidence"])
        self.assertGreaterEqual(result["updatedSkills"]["python"]["proficiency"], 20)
        self.assertIn("roadmap", result)

    def test_assessment_rejects_unrelated_skill(self):
        with self.assertRaises(Exception):
            submit_diagnostic(DiagnosticSubmitRequest(
                target_role="data_scientist",
                known_skills=[],
                current_skills={},
                answers=[DiagnosticAnswer(questionId="cybersecurity-0", skillId="cybersecurity", answer="x")],
            ))


if __name__ == "__main__":
    unittest.main()
