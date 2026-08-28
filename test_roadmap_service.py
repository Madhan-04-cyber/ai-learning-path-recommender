import unittest

from roadmap_service import dependency_traversal, generate_roadmap, replan_path
from main import build_contextual_resources, select_adaptive_project


GRAPH = {
    "python": {"title": "Python", "description": "", "prerequisites": [], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Beginner", "resources": [], "project": {"title": "Python project"}},
    "sql": {"title": "SQL", "description": "", "prerequisites": [], "required_proficiency": 70, "estimated_hours": 6, "difficulty": "Beginner", "resources": [], "project": {}},
    "oop": {"title": "OOP", "description": "", "prerequisites": ["python"], "required_proficiency": 75, "estimated_hours": 6, "difficulty": "Intermediate", "resources": [], "project": {}},
    "api": {"title": "API", "description": "", "prerequisites": ["oop", "sql"], "required_proficiency": 80, "estimated_hours": 10, "difficulty": "Advanced", "resources": [], "project": {}},
}


class RoadmapServiceTests(unittest.TestCase):
    def test_dependency_order_is_prerequisite_first(self):
        order = dependency_traversal(["api", "python", "sql", "oop"], GRAPH)
        self.assertLess(order.index("python"), order.index("oop"))
        self.assertLess(order.index("oop"), order.index("api"))
        self.assertLess(order.index("sql"), order.index("api"))

    def test_mastered_skill_is_skipped(self):
        roadmap = generate_roadmap("Backend", ["python", "oop"], [], GRAPH, {"python": {"proficiency": 90, "status": "Completed", "confidence": "Verified"}})
        self.assertFalse(any(item.skillId == "python" for item in roadmap.items))
        self.assertTrue(any(item.skillId == "oop" for item in roadmap.items))

    def test_blocked_skill_is_not_current(self):
        roadmap = generate_roadmap("Backend", ["python", "sql", "oop", "api"], [], GRAPH, {})
        api_items = [item for item in roadmap.items if item.skillId == "api"]
        self.assertTrue(api_items)
        self.assertTrue(all(item.status == "LOCKED" for item in api_items))

    def test_bottleneck_gets_next_action_priority(self):
        roadmap = generate_roadmap("Backend", ["python", "sql", "oop", "api"], [], GRAPH, {})
        self.assertIsNotNone(roadmap.nextBestAction)
        self.assertEqual(roadmap.nextBestAction.skillId, "python")
        self.assertTrue(roadmap.nextBestAction.reason)

    def test_invalid_graph_is_rejected(self):
        with self.assertRaises(ValueError):
            dependency_traversal(["unknown"], GRAPH)
        missing = {"api": {"title": "API", "prerequisites": ["missing"]}}
        with self.assertRaises(ValueError):
            dependency_traversal(["api"], missing)
        cyclic = {"a": {"prerequisites": ["b"]}, "b": {"prerequisites": ["a"]}}
        with self.assertRaises(ValueError):
            dependency_traversal(["a", "b"], cyclic)

    def test_skill_improvement_unlocks_next_skill(self):
        graph = {
            "sql_basics": {"title": "SQL Basics", "description": "", "prerequisites": [], "required_proficiency": 70, "estimated_hours": 6, "difficulty": "Beginner", "resources": [], "project": {}},
            "postgresql": {"title": "PostgreSQL", "description": "", "prerequisites": ["sql_basics"], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Intermediate", "resources": [], "project": {}},
            "fastapi": {"title": "FastAPI", "description": "", "prerequisites": ["postgresql"], "required_proficiency": 80, "estimated_hours": 10, "difficulty": "Intermediate", "resources": [], "project": {}},
        }
        result = replan_path(
            career_name="Backend",
            required_skill_ids=["sql_basics", "postgresql", "fastapi"],
            optional_skill_ids=[],
            graph=graph,
            current_skills={"sql_basics": {"proficiency": 80, "status": "Completed", "confidence": "Verified"}},
            trigger={"type": "assessment_completed", "skill_id": "postgresql", "score": 86},
        )
        roadmap = result.roadmap
        self.assertTrue(result.changed)
        self.assertIn("verified", result.explanation.lower())
        self.assertTrue(any(item.skillId == "fastapi" for item in roadmap.items))
        self.assertEqual(roadmap.nextBestAction.skillId, "fastapi")

    def test_skill_regression_introduces_reinforcement(self):
        graph = {
            "sql_basics": {"title": "SQL Basics", "description": "", "prerequisites": [], "required_proficiency": 70, "estimated_hours": 6, "difficulty": "Beginner", "resources": [], "project": {}},
            "postgresql": {"title": "PostgreSQL", "description": "", "prerequisites": ["sql_basics"], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Intermediate", "resources": [], "project": {}},
            "fastapi": {"title": "FastAPI", "description": "", "prerequisites": ["postgresql"], "required_proficiency": 80, "estimated_hours": 10, "difficulty": "Intermediate", "resources": [], "project": {}},
        }
        result = replan_path(
            career_name="Backend",
            required_skill_ids=["sql_basics", "postgresql", "fastapi"],
            optional_skill_ids=[],
            graph=graph,
            current_skills={"sql_basics": {"proficiency": 80, "status": "Completed", "confidence": "Verified"}, "postgresql": {"proficiency": 78, "status": "Completed", "confidence": "Verified"}},
            trigger={"type": "skill_regression", "skill_id": "postgresql", "drop": 25},
        )
        self.assertIn("regressed", result.explanation.lower())
        self.assertEqual(result.roadmap.nextBestAction.skillId, "postgresql")
        self.assertTrue(any(item.skillId == "fastapi" and item.status == "LOCKED" for item in result.roadmap.items))

    def test_learning_time_change_replans_priorities(self):
        graph = {
            "python": {"title": "Python", "description": "", "prerequisites": [], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Beginner", "resources": [], "project": {}},
            "git": {"title": "Git", "description": "", "prerequisites": [], "required_proficiency": 70, "estimated_hours": 4, "difficulty": "Beginner", "resources": [], "project": {}},
        }
        result = replan_path(
            career_name="Backend",
            required_skill_ids=["python", "git"],
            optional_skill_ids=[],
            graph=graph,
            current_skills={},
            daily_learning_minutes=15,
            trigger={"type": "availability_changed", "daily_learning_minutes": 15},
        )
        self.assertIn("minutes", result.explanation.lower())
        self.assertIsNotNone(result.roadmap.nextBestAction)
        self.assertEqual(result.roadmap.validation["valid"], True)

    def test_replan_is_safe_without_ai(self):
        result = replan_path(
            career_name="Backend",
            required_skill_ids=["python"],
            optional_skill_ids=[],
            graph={"python": {"title": "Python", "description": "", "prerequisites": [], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Beginner", "resources": [], "project": {}}},
            current_skills={},
            trigger={"type": "learner_feedback", "skill_id": "python", "feedback": "This was difficult"},
        )
        self.assertTrue(result.roadmap.items)
        self.assertIsNotNone(result.insight)

    def test_adaptive_projects_change_with_level(self):
        graph = {
            "fastapi": {"title": "FastAPI", "resources": [], "prerequisites": [], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Intermediate"},
        }
        beginner = select_adaptive_project("fastapi", 20, graph)
        advanced = select_adaptive_project("fastapi", 90, graph)
        self.assertIn("REST API", beginner["title"])
        self.assertIn("RAG-powered AI Backend", advanced["title"])

    def test_contextual_resources_attach_reason_and_skill(self):
        graph = {
            "fastapi": {"title": "FastAPI", "resources": [{"title": "FastAPI docs", "type": "Documentation", "url": "https://fastapi.tiangolo.com/"}], "prerequisites": [], "required_proficiency": 80, "estimated_hours": 8, "difficulty": "Intermediate"},
        }
        resources = build_contextual_resources("fastapi", graph, 60)
        self.assertTrue(resources)
        self.assertEqual(resources[0]["skill"], "fastapi")
        self.assertIn("recommended", resources[0]["reason"].lower())


if __name__ == "__main__":
    unittest.main()
