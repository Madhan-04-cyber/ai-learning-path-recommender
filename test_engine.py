import unittest

from main import (
    GoalAnalysisRequest,
    analyze_goal,
    build_contextual_resources,
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


if __name__ == "__main__":
    unittest.main()
