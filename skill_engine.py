from typing import Any, Dict, Iterable, List, Literal, Optional

from pydantic import BaseModel, Field

SkillStatus = Literal["COMPLETED", "CURRENT", "AVAILABLE", "NEEDS_ATTENTION", "LOCKED"]


class Skill(BaseModel):
    id: str
    name: str
    category: str
    description: str
    requiredLevel: int = Field(ge=0, le=100)
    currentLevel: int = Field(ge=0, le=100)
    status: SkillStatus
    prerequisites: List[str] = Field(default_factory=list)
    dependents: List[str] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    estimatedHours: int = Field(ge=0)


class SkillGapSummary(BaseModel):
    missingSkills: List[str] = Field(default_factory=list)
    weakSkills: List[str] = Field(default_factory=list)
    verifiedSkills: List[str] = Field(default_factory=list)
    blockedSkills: List[str] = Field(default_factory=list)
    criticalBottlenecks: List[str] = Field(default_factory=list)


CATEGORY_BY_TOKEN = {
    "python": "Programming",
    "oop": "Programming",
    "javascript": "Programming",
    "react": "Programming",
    "http": "Backend",
    "rest": "Backend",
    "fastapi": "Backend",
    "auth": "Backend",
    "backend": "Backend",
    "sql": "Database",
    "postgres": "Database",
    "database": "Database",
    "numpy": "AI/ML",
    "pandas": "AI/ML",
    "math": "AI/ML",
    "machine": "AI/ML",
    "model": "AI/ML",
    "embedding": "AI/ML",
    "vector": "AI/ML",
    "rag": "AI/ML",
    "docker": "DevOps",
    "cloud": "Cloud",
    "deploy": "Cloud",
    "monitor": "DevOps",
    "git": "Tools",
}


def _category(skill_id: str, metadata: Dict[str, Any]) -> str:
    if metadata.get("category"):
        return metadata["category"]
    for token, category in CATEGORY_BY_TOKEN.items():
        if token in skill_id.lower():
            return category
    return "Tools"


def _level(user_skill: Dict[str, Any]) -> int:
    value = user_skill.get("proficiency", user_skill.get("currentLevel", 0))
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return 0


def calculateSkillGap(requiredLevel: int, currentLevel: int) -> int:
    """Return a non-negative proficiency gap."""
    return max(0, requiredLevel - currentLevel)


def calculateSkillStatus(
    requiredLevel: int,
    currentLevel: int,
    userSkill: Optional[Dict[str, Any]] = None,
    prerequisitesComplete: bool = True,
) -> SkillStatus:
    """Classify a skill using evidence and prerequisite readiness."""
    userSkill = userSkill or {}
    verified = userSkill.get("confidence") in {"Verified", "Assessed"} and currentLevel >= requiredLevel
    if userSkill.get("status") in {"Completed", "Verified"} and verified:
        return "COMPLETED"
    if userSkill.get("status") == "Needs Improvement" or (
        currentLevel > 0 and currentLevel < requiredLevel and userSkill.get("confidence") in {"Assessed", "Verified"}
    ):
        return "NEEDS_ATTENTION"
    if not prerequisitesComplete:
        return "LOCKED"
    if currentLevel > 0:
        return "CURRENT"
    return "AVAILABLE"


def _transitive_dependents(skill_id: str, graph: Dict[str, Dict[str, Any]], scope: set[str]) -> set[str]:
    found: set[str] = set()
    pending = [skill_id]
    while pending:
        current = pending.pop(0)
        for candidate in scope:
            if candidate in found or candidate == current:
                continue
            if current in graph.get(candidate, {}).get("prerequisites", []):
                found.add(candidate)
                pending.append(candidate)
    return found


def findBottlenecks(
    skills: Iterable[Skill],
    graph: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[str]:
    """Rank incomplete skills by the number of blocked downstream skills."""
    skill_list = list(skills)
    skill_map = {skill.id: skill for skill in skill_list}
    source_graph = graph or {
        skill.id: {"prerequisites": skill.prerequisites} for skill in skill_list
    }
    scope = set(skill_map)
    ranked = []
    for skill in skill_list:
        if skill.status == "COMPLETED":
            continue
        dependents = _transitive_dependents(skill.id, source_graph, scope)
        blocked_count = sum(skill_map[item].status == "LOCKED" for item in dependents)
        if blocked_count:
            ranked.append((blocked_count, skill_list.index(skill), skill.id))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked]


def getAvailableSkills(skills: Iterable[Skill]) -> List[str]:
    """Return skills that can be started now."""
    return [skill.id for skill in skills if skill.status == "AVAILABLE"]


def build_skill_models(
    career_skill_ids: Iterable[str],
    skill_graph: Dict[str, Dict[str, Any]],
    current_skills: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Skill]:
    """Normalize the career graph into the public skill model."""
    current_skills = current_skills or {}
    scope = set(career_skill_ids)
    dependents = {skill_id: [] for skill_id in scope}
    for skill_id in scope:
        for prerequisite in skill_graph.get(skill_id, {}).get("prerequisites", []):
            if prerequisite in scope:
                dependents.setdefault(prerequisite, []).append(skill_id)

    models: List[Skill] = []
    for skill_id in career_skill_ids:
        metadata = skill_graph.get(skill_id)
        if not metadata:
            continue
        user_skill = current_skills.get(skill_id, {})
        current_level = _level(user_skill)
        required_level = int(metadata.get("required_proficiency", 70))
        prerequisites = [item for item in metadata.get("prerequisites", []) if item in scope]
        prerequisites_complete = all(
            calculateSkillStatus(
                int(skill_graph[item].get("required_proficiency", 70)),
                _level(current_skills.get(item, {})),
                current_skills.get(item, {}),
                True,
            ) == "COMPLETED"
            for item in prerequisites
        )
        models.append(Skill(
            id=skill_id,
            name=metadata.get("title", skill_id.replace("_", " ").title()),
            category=_category(skill_id, metadata),
            description=metadata.get("description", ""),
            requiredLevel=required_level,
            currentLevel=current_level,
            status=calculateSkillStatus(required_level, current_level, user_skill, prerequisites_complete),
            prerequisites=prerequisites,
            dependents=sorted(dependents.get(skill_id, [])),
            evidence=list(user_skill.get("evidence", [])),
            estimatedHours=int(metadata.get("estimated_hours", 6)),
        ))
    return models


def analyze_skill_gaps(skills: Iterable[Skill]) -> SkillGapSummary:
    skill_list = list(skills)
    missing = [skill.id for skill in skill_list if skill.currentLevel == 0]
    weak = [skill.id for skill in skill_list if skill.status == "NEEDS_ATTENTION"]
    verified = [skill.id for skill in skill_list if skill.status == "COMPLETED"]
    blocked = [skill.id for skill in skill_list if skill.status == "LOCKED"]
    return SkillGapSummary(
        missingSkills=missing,
        weakSkills=weak,
        verifiedSkills=verified,
        blockedSkills=blocked,
        criticalBottlenecks=findBottlenecks(skill_list),
    )


# Snake-case aliases keep the service idiomatic for Python callers.
calculate_skill_gap = calculateSkillGap
calculate_skill_status = calculateSkillStatus
find_bottlenecks = findBottlenecks
get_available_skills = getAvailableSkills
