import unittest

from skill_engine import (
    Skill,
    analyze_skill_gaps,
    build_skill_models,
    calculateSkillGap,
    calculateSkillStatus,
    findBottlenecks,
    getAvailableSkills,
)


class SkillEngineTests(unittest.TestCase):
    def test_gap_is_never_negative(self):
        self.assertEqual(calculateSkillGap(80, 45), 35)
        self.assertEqual(calculateSkillGap(80, 95), 0)

    def test_status_requires_verified_evidence_for_completion(self):
        self.assertEqual(calculateSkillStatus(80, 80, {"status": "Completed", "confidence": "Verified"}), "COMPLETED")
        self.assertEqual(calculateSkillStatus(80, 80, {"status": "Completed", "confidence": "Self-reported"}), "CURRENT")
        self.assertEqual(calculateSkillStatus(80, 45, {"status": "Needs Improvement", "confidence": "Assessed"}), "NEEDS_ATTENTION")

    def test_available_skills_respect_prerequisites(self):
        graph = {
            "python": {"title": "Python", "prerequisites": [], "required_proficiency": 80, "estimated_hours": 8},
            "oop": {"title": "OOP", "prerequisites": ["python"], "required_proficiency": 75, "estimated_hours": 6},
        }
        skills = build_skill_models(["python", "oop"], graph, {})
        self.assertEqual(getAvailableSkills(skills), ["python"])
        self.assertEqual(analyze_skill_gaps(skills).blockedSkills, ["oop"])

    def test_bottleneck_ranks_blocked_dependents(self):
        skills = [
            Skill(id="python", name="Python", category="Programming", description="", requiredLevel=80, currentLevel=0, status="AVAILABLE", estimatedHours=8, dependents=["oop"]),
            Skill(id="oop", name="OOP", category="Programming", description="", requiredLevel=75, currentLevel=0, status="LOCKED", estimatedHours=6, prerequisites=["python"], dependents=["api"]),
            Skill(id="api", name="API", category="Backend", description="", requiredLevel=75, currentLevel=0, status="LOCKED", estimatedHours=6, prerequisites=["oop"]),
        ]
        self.assertEqual(findBottlenecks(skills), ["python", "oop"])


if __name__ == "__main__":
    unittest.main()
