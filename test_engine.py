import unittest
from unittest.mock import patch

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
        self.assertEqual(result.goal, "I want to become a data analyst")

    def test_coach_greeting_is_deterministic(self):
        request = ChatRequest(
            message="hi",
            history=[],
            target_role="data_scientist",
            user_skills={},
            project_blueprint={"whatYouAreBuilding": "Internal Blueprint"},
        )
        with patch("main.get_gemini_client") as get_client:
            response = chat_assistant(request)
        get_client.assert_not_called()
        self.assertIn("Hi! I'm your PathMind learning coach.", response["response"])
        self.assertNotIn("Internal Blueprint", response["response"])

    def test_coach_fallback_when_gemini_unavailable_does_not_leak_context(self):
        request = ChatRequest(
            message="what should I learn next?",
            history=[],
            target_role="data_scientist",
            user_skills={},
            current_skill="numpy_pandas",
            current_milestone="Internal Milestone",
            next_action="Practice arrays",
            project_blueprint={"whatYouAreBuilding": "Internal Blueprint", "implementationTasks": ["SECRET STEP"]},
        )
        with patch("main.get_gemini_client", return_value=None):
            response = chat_assistant(request)
        self.assertIn("Your next focus is Practice arrays", response["response"])
        self.assertNotIn("Internal Blueprint", response["response"])
        self.assertNotIn("SECRET STEP", response["response"])
        self.assertNotIn("trouble reaching", response["response"].lower())

    def test_coach_malformed_gemini_response_uses_safe_fallback(self):
        class EmptyResponse:
            text = ""

        class FakeModels:
            def generate_content(self, **kwargs):
                return EmptyResponse()

        class FakeClient:
            models = FakeModels()

        request = ChatRequest(
            message="explain this",
            history=[],
            target_role="data_scientist",
            user_skills={},
            current_skill="numpy_pandas",
            project_blueprint={"whatYouAreBuilding": "Internal Blueprint"},
        )
        with patch("main.get_gemini_client", return_value=FakeClient()):
            response = chat_assistant(request)
        self.assertIn("I can explain numpy_pandas step by step", response["response"])
        self.assertNotIn("Internal Blueprint", response["response"])

    def test_project_mentor_context_is_not_used_by_unavailable_fallback(self):
        request = ChatRequest(
            message="I am stuck and getting an error.",
            history=[],
            target_role="cloud_engineer",
            user_skills={},
            current_skill="docker",
            current_milestone="Infrastructure Setup",
            project_blueprint={"whatYouAreBuilding": "Cloud Deployment Sandbox", "implementationTasks": ["Set up Docker"]},
        )
        with patch("main.get_gemini_client", return_value=None):
            response = chat_assistant(request)
        self.assertNotIn("Cloud Deployment Sandbox", response["response"])
        self.assertNotIn("Set up Docker", response["response"])
        self.assertNotIn("current context", response["response"].lower())

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
        with patch("main.get_gemini_client", return_value=None):
            mentor_response = chat_assistant(fallback_request)
        self.assertNotIn("Cloud Deployment Sandbox", mentor_response["response"])
        self.assertNotIn("Set up Docker", mentor_response["response"])

        generic_request = ChatRequest(
            message="Why am I learning this?",
            history=[],
            target_role="ai_engineer",
            user_skills={},
        )
        generic_response = chat_assistant(generic_request)
        self.assertIn("learning path", generic_response["response"])

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

    def test_cloud_assessment_questions_have_valid_unique_ids(self):
        data = start_diagnostic(DiagnosticStartRequest(target_role="cloud_engineer"))
        questions = data["questions"]
        self.assertEqual(len(questions), len({question.questionId for question in questions}))
        self.assertTrue(all(question.questionId == f"{question.skillId}-0" for question in questions))
        self.assertIn("infrastructure", {question.skillId for question in questions})

    def test_cloud_assessment_submission_scores_evidence_updates_and_roadmap(self):
        started = start_diagnostic(DiagnosticStartRequest(target_role="cloud_engineer"))
        result = submit_diagnostic(DiagnosticSubmitRequest(
            target_role="cloud_engineer",
            answers=[DiagnosticAnswer(questionId=question.questionId, skillId=question.skillId, answer=question.options[0]) for question in started["questions"]],
        ))
        self.assertEqual(result["target_role"], "cloud_engineer")
        self.assertEqual(len(result["assessmentResults"]), len(started["questions"]))
        self.assertTrue(result["evidence"])
        self.assertIn("cloud_fundamentals", result["updatedSkills"])
        self.assertIn("roadmap", result)

    def test_supported_career_assessment_submissions_work(self):
        for role in ("data_scientist", "cybersecurity_engineer"):
            started = start_diagnostic(DiagnosticStartRequest(target_role=role))
            result = submit_diagnostic(DiagnosticSubmitRequest(
                target_role=role,
                answers=[DiagnosticAnswer(questionId=question.questionId, skillId=question.skillId, answer=question.options[0]) for question in started["questions"]],
            ))
            self.assertTrue(result["assessmentResults"])
            self.assertTrue(result["evidence"])
            self.assertTrue(result["roadmap"])

    def test_invalid_gemini_question_uses_deterministic_fallback(self):
        class InvalidResponse:
            text = '{"question": "", "options": ["only one"], "questionType": "unknown"}'

        class FakeModels:
            def generate_content(self, **kwargs):
                return InvalidResponse()

        class FakeClient:
            models = FakeModels()

        with patch("main.get_gemini_client", return_value=FakeClient()):
            question = start_diagnostic(DiagnosticStartRequest(target_role="cloud_engineer"))["questions"][0]
        self.assertTrue(question.question)
        self.assertEqual(len(question.options), 4)
        self.assertEqual(question.questionType, "mcq")

    def test_duplicate_or_mismatched_question_ids_are_rejected(self):
        with self.assertRaises(Exception):
            submit_diagnostic(DiagnosticSubmitRequest(
                target_role="cloud_engineer",
                answers=[DiagnosticAnswer(questionId="linux-0", skillId="linux", answer="x"), DiagnosticAnswer(questionId="linux-0", skillId="linux", answer="x")],
            ))
        with self.assertRaises(Exception):
            submit_diagnostic(DiagnosticSubmitRequest(
                target_role="cloud_engineer",
                answers=[DiagnosticAnswer(questionId="linux-1", skillId="linux", answer="x")],
            ))

    def test_invalid_answer_payload_is_rejected(self):
        with self.assertRaises(Exception):
            submit_diagnostic(DiagnosticSubmitRequest(
                target_role="cloud_engineer",
                answers=[DiagnosticAnswer(questionId="not-a-question", skillId="linux", answer="x")],
            ))

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
