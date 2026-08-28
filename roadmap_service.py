import math
from typing import Any, Dict, Iterable, List, Literal, Optional, Set

from pydantic import BaseModel, Field

from skill_engine import Skill, analyze_skill_gaps, build_skill_models, findBottlenecks

RoadmapType = Literal["LEARN", "PRACTICE", "PROJECT", "ASSESSMENT", "REVIEW"]


class RoadmapItem(BaseModel):
    id: str
    skillId: str
    title: str
    type: RoadmapType
    reason: str
    prerequisites: List[str] = Field(default_factory=list)
    estimatedTime: str
    difficulty: str
    status: str
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    assessment: Dict[str, Any] = Field(default_factory=dict)
    project: Dict[str, Any] = Field(default_factory=dict)


class Roadmap(BaseModel):
    items: List[RoadmapItem]
    nextBestAction: Optional[RoadmapItem] = None
    estimatedDuration: str
    validation: Dict[str, Any]


class ReplanResult(BaseModel):
    roadmap: Roadmap
    changed: bool
    explanation: str
    insight: str
    previousNextBestAction: Optional[str] = None
    currentNextBestAction: Optional[str] = None


def validate_skill_graph(skill_ids: Iterable[str], graph: Dict[str, Dict[str, Any]]) -> None:
    """Reject unknown prerequisites and cycles before generating a route."""
    scope = set(skill_ids)
    unknown = scope - set(graph)
    if unknown:
        raise ValueError(f"Unknown skills in career scope: {sorted(unknown)}")
    missing = {
        prerequisite
        for skill_id in scope
        for prerequisite in graph.get(skill_id, {}).get("prerequisites", [])
        if prerequisite not in graph or prerequisite not in scope
    }
    if missing:
        raise ValueError(f"Missing prerequisite skills: {sorted(missing)}")

    visiting: Set[str] = set()
    visited: Set[str] = set()

    def visit(skill_id: str) -> None:
        if skill_id in visiting:
            raise ValueError(f"Circular dependency detected at {skill_id}")
        if skill_id in visited:
            return
        visiting.add(skill_id)
        for prerequisite in graph[skill_id].get("prerequisites", []):
            visit(prerequisite)
        visiting.remove(skill_id)
        visited.add(skill_id)

    for skill_id in sorted(scope):
        visit(skill_id)


def dependency_traversal(skill_ids: Iterable[str], graph: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return a stable prerequisite-first order."""
    validate_skill_graph(skill_ids, graph)
    order: List[str] = []
    visited: Set[str] = set()

    def visit(skill_id: str) -> None:
        if skill_id in visited:
            return
        for prerequisite in graph[skill_id].get("prerequisites", []):
            visit(prerequisite)
        visited.add(skill_id)
        order.append(skill_id)

    for skill_id in skill_ids:
        visit(skill_id)
    return order


def _skill_priority(skill: Skill, required: Set[str], bottlenecks: List[str], daily_minutes: int) -> float:
    gap = max(0, skill.requiredLevel - skill.currentLevel)
    dependency_importance = len(skill.dependents) * 10
    bottleneck_bonus = 25 if skill.id in bottlenecks else 0
    career_bonus = 20 if skill.id in required else 8
    time_bonus = max(0, 60 - daily_minutes) / 10
    return gap * 0.6 + dependency_importance + bottleneck_bonus + career_bonus + time_bonus


def _reason(skill: Skill, career_name: str, gap: int) -> str:
    if skill.status == "NEEDS_ATTENTION":
        return f"Your assessed {skill.name} proficiency is {skill.currentLevel}%, below the {skill.requiredLevel}% target for {career_name}. Review this before moving on."
    if skill.prerequisites:
        prerequisites = ", ".join(skill.prerequisites)
        return f"{skill.name} is required for {career_name} and follows {prerequisites}. Your current gap is {gap} points."
    return f"{skill.name} is a foundation for {career_name}. Your current gap is {gap} points."


def _activity(
    skill: Skill,
    activity_type: RoadmapType,
    career_name: str,
    metadata: Dict[str, Any],
    status: str,
    suffix: str,
) -> RoadmapItem:
    project = metadata.get("project", {})
    if skill.id == "capstone_project":
        project = {"title": skill.name, "description": skill.description}
    title_by_type = {
        "LEARN": skill.name,
        "REVIEW": f"Review {skill.name}",
        "PRACTICE": f"Practice {skill.name}",
        "PROJECT": project.get("title", f"Build a {skill.name} project"),
        "ASSESSMENT": f"Assess {skill.name}",
    }
    return RoadmapItem(
        id=f"{skill.id}:{suffix}",
        skillId=skill.id,
        title=title_by_type[activity_type],
        type=activity_type,
        reason=_reason(skill, career_name, max(0, skill.requiredLevel - skill.currentLevel)),
        prerequisites=skill.prerequisites,
        estimatedTime=f"{skill.estimatedHours} hours",
        difficulty=skill.category if activity_type == "PROJECT" else metadata.get("difficulty", "Intermediate"),
        status=status,
        resources=list(metadata.get("resources", [])),
        assessment={"required": activity_type == "ASSESSMENT", "skillId": skill.id},
        project=project,
    )


def generate_roadmap(
    career_name: str,
    required_skill_ids: Iterable[str],
    optional_skill_ids: Iterable[str],
    graph: Dict[str, Dict[str, Any]],
    current_skills: Optional[Dict[str, Dict[str, Any]]] = None,
    daily_learning_minutes: int = 60,
) -> Roadmap:
    """Build a deterministic, prerequisite-aware route from learner evidence."""
    current_skills = current_skills or {}
    scope_ids = list(dict.fromkeys([*required_skill_ids, *optional_skill_ids]))
    ordered_ids = dependency_traversal(scope_ids, graph)
    models = build_skill_models(ordered_ids, graph, current_skills)
    model_by_id = {skill.id: skill for skill in models}
    required = set(required_skill_ids)
    bottlenecks = findBottlenecks(models)

    incomplete = [skill for skill in models if skill.status != "COMPLETED"]
    priority_order = sorted(
        incomplete,
        key=lambda skill: (-_skill_priority(skill, required, bottlenecks, daily_learning_minutes), ordered_ids.index(skill.id)),
    )
    priority_rank = {skill.id: index for index, skill in enumerate(priority_order)}
    route_skills = sorted(incomplete, key=lambda skill: ordered_ids.index(skill.id))

    items: List[RoadmapItem] = []
    for skill in route_skills:
        metadata = graph[skill.id]
        status = skill.status
        if status == "NEEDS_ATTENTION":
            items.append(_activity(skill, "REVIEW", career_name, metadata, "CURRENT", "review"))
        else:
            items.append(_activity(skill, "LEARN", career_name, metadata, "CURRENT" if skill.status in {"CURRENT", "AVAILABLE"} else "LOCKED", "learn"))
            items.append(_activity(skill, "PRACTICE", career_name, metadata, "LOCKED" if skill.status == "LOCKED" else "AVAILABLE", "practice"))
        if metadata.get("project") or skill.id == "capstone_project":
            items.append(_activity(skill, "PROJECT", career_name, metadata, "LOCKED" if skill.status == "LOCKED" else "AVAILABLE", "project"))
        items.append(_activity(skill, "ASSESSMENT", career_name, metadata, "LOCKED" if skill.status == "LOCKED" else "AVAILABLE", "assessment"))

    actionable_skills = sorted(
        [skill for skill in incomplete if skill.status in {"AVAILABLE", "CURRENT", "NEEDS_ATTENTION"}],
        key=lambda skill: (priority_rank.get(skill.id, len(priority_rank)), ordered_ids.index(skill.id)),
    )
    next_action = None
    if actionable_skills:
        next_skill = actionable_skills[0]
        next_action = next((item for item in items if item.skillId == next_skill.id), None)

    total_hours = sum(skill.estimatedHours for skill in incomplete)
    minutes = max(1, daily_learning_minutes)
    weeks = max(1, math.ceil((total_hours * 60) / (minutes * 7)))
    months = max(1, math.ceil(weeks / 4.3))
    validation = validate_roadmap(items, ordered_ids)
    return Roadmap(items=items, nextBestAction=next_action, estimatedDuration=f"{months} month{'s' if months != 1 else ''} estimate", validation=validation)


def validate_roadmap(items: Iterable[RoadmapItem], ordered_skill_ids: List[str]) -> Dict[str, Any]:
    """Validate unique activities and prerequisite-first skill ordering."""
    item_list = list(items)
    errors: List[str] = []
    if len({item.id for item in item_list}) != len(item_list):
        errors.append("Duplicate roadmap item IDs")
    first_position = {}
    for index, item in enumerate(item_list):
        first_position.setdefault(item.skillId, index)
    for item in item_list:
        for prerequisite in item.prerequisites:
            if prerequisite in first_position and first_position[prerequisite] > first_position[item.skillId]:
                errors.append(f"Prerequisite {prerequisite} appears after {item.skillId}")
    return {"valid": not errors, "errors": errors, "skillOrder": ordered_skill_ids}


def _normalized_skill_state(skill_id: str, current_skills: Dict[str, Dict[str, Any]], graph: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    state = dict(current_skills.get(skill_id, {}))
    if "proficiency" not in state and "currentLevel" in state:
        state["proficiency"] = state.get("currentLevel", 0)
    if "status" not in state:
        state["status"] = "Completed" if state.get("proficiency", 0) >= int(graph[skill_id].get("required_proficiency", 70)) else "Current"
    return state


def replan_path(
    career_name: str,
    required_skill_ids: Iterable[str],
    optional_skill_ids: Iterable[str],
    graph: Dict[str, Dict[str, Any]],
    current_skills: Optional[Dict[str, Dict[str, Any]]] = None,
    daily_learning_minutes: int = 60,
    trigger: Optional[Dict[str, Any]] = None,
) -> ReplanResult:
    """Deterministically adapt the roadmap when learner evidence changes."""
    current_skills = current_skills or {}
    trigger = trigger or {}
    trigger_type = str(trigger.get("type", "evidence_update"))
    trigger_skill = trigger.get("skill_id")
    before_roadmap = generate_roadmap(
        career_name=career_name,
        required_skill_ids=required_skill_ids,
        optional_skill_ids=optional_skill_ids,
        graph=graph,
        current_skills=current_skills,
        daily_learning_minutes=daily_learning_minutes,
    )

    next_skills = {skill_id: dict(state) for skill_id, state in current_skills.items()}
    explanation = ""
    insight = ""

    if trigger_type == "assessment_completed" and trigger_skill:
        score = int(trigger.get("score", 0))
        target_level = int(graph[trigger_skill].get("required_proficiency", 70))
        next_skills[trigger_skill] = {
            **_normalized_skill_state(trigger_skill, next_skills, graph),
            "proficiency": max(score, target_level if score >= 75 else score),
            "status": "Completed" if score >= 75 else "Needs Improvement",
            "confidence": "Verified" if score >= 75 else "Assessed",
            "last_test_score": score,
        }
        if score >= 75:
            explanation = f"{graph[trigger_skill]['title']} was verified, so dependent skills were unlocked."
            insight = f"You mastered {graph[trigger_skill]['title']}. The roadmap can now move to the next dependency."
        else:
            explanation = f"Your {graph[trigger_skill]['title']} result is below the level required for the next backend milestone."
            insight = f"We noticed that your {graph[trigger_skill]['title']} accuracy needs reinforcement before moving on."
    elif trigger_type == "repeated_practice_mistakes" and trigger_skill:
        state = _normalized_skill_state(trigger_skill, next_skills, graph)
        current_level = int(state.get("proficiency", 0))
        next_skills[trigger_skill] = {
            **state,
            "proficiency": max(0, current_level - 10),
            "status": "Needs Improvement",
            "confidence": "Practice Review",
        }
        explanation = f"Repeated mistakes lowered confidence in {graph[trigger_skill]['title']}, so extra practice was inserted."
        insight = f"We noticed that your {graph[trigger_skill]['title']} accuracy is strong, but deeper practice is still needed."
    elif trigger_type == "skill_regression" and trigger_skill:
        state = _normalized_skill_state(trigger_skill, next_skills, graph)
        current_level = int(state.get("proficiency", 0))
        next_skills[trigger_skill] = {
            **state,
            "proficiency": max(0, current_level - int(trigger.get("drop", 15))),
            "status": "Needs Improvement",
            "confidence": "Regressed",
        }
        explanation = f"{graph[trigger_skill]['title']} regressed, so the roadmap now reinforces that dependency before unlocking later skills."
        insight = f"Previously: {trigger.get('previous_next', 'next milestone')}. Now: {graph[trigger_skill]['title']}."
    elif trigger_type == "user_skipped_topic" and trigger_skill:
        state = _normalized_skill_state(trigger_skill, next_skills, graph)
        next_skills[trigger_skill] = {
            **state,
            "proficiency": min(int(state.get("proficiency", 0)), int(graph[trigger_skill].get("required_proficiency", 70)) - 1),
            "status": "Needs Improvement",
            "confidence": "Skipped",
        }
        explanation = f"Skipping {graph[trigger_skill]['title']} creates a blocker, so the roadmap inserts practice and reassessment."
        insight = f"The system moved {graph[trigger_skill]['title']} ahead of the next milestone because it is a prerequisite."
    elif trigger_type == "availability_changed":
        minutes = int(trigger.get("daily_learning_minutes", daily_learning_minutes))
        explanation = f"Your available learning time changed to {minutes} minutes per day, so the plan was reprioritized."
        insight = f"Your weekly cadence changed, so the roadmap now emphasizes the highest-impact next action."
        daily_learning_minutes = minutes
    elif trigger_type == "project_performance_changed" and trigger_skill:
        score = int(trigger.get("score", 0))
        state = _normalized_skill_state(trigger_skill, next_skills, graph)
        next_skills[trigger_skill] = {
            **state,
            "proficiency": max(0, max(int(state.get("proficiency", 0)), score)),
            "status": "Completed" if score >= 80 else "Needs Improvement",
            "confidence": "Project Review",
        }
        explanation = f"Project performance updated {graph[trigger_skill]['title']} and changed downstream availability."
        insight = f"Project results now influence the next-best-action instead of relying only on lesson completion."
    elif trigger_type == "learner_feedback" and trigger_skill:
        feedback = str(trigger.get("feedback", "")).lower()
        state = _normalized_skill_state(trigger_skill, next_skills, graph)
        current_level = int(state.get("proficiency", 0))
        next_skills[trigger_skill] = {
            **state,
            "proficiency": max(0, current_level - 5) if "difficult" in feedback else min(100, max(current_level, int(graph[trigger_skill].get("required_proficiency", 70)))),
            "status": "Needs Improvement" if "difficult" in feedback else state.get("status", "Current"),
            "confidence": "Learner Feedback",
        }
        explanation = f"Learner feedback adjusted the path around {graph[trigger_skill]['title']}."
        insight = f"We detected feedback that changes the recommended sequence around {graph[trigger_skill]['title']}."
    else:
        explanation = "New evidence triggered a deterministic roadmap recalculation."
        insight = "The route was recalculated from the current skill graph."

    roadmap = generate_roadmap(
        career_name=career_name,
        required_skill_ids=required_skill_ids,
        optional_skill_ids=optional_skill_ids,
        graph=graph,
        current_skills=next_skills,
        daily_learning_minutes=daily_learning_minutes,
    )
    return ReplanResult(
        roadmap=roadmap,
        changed=before_roadmap.items != roadmap.items or before_roadmap.nextBestAction != roadmap.nextBestAction,
        explanation=explanation,
        insight=insight,
        previousNextBestAction=before_roadmap.nextBestAction.title if before_roadmap.nextBestAction else None,
        currentNextBestAction=roadmap.nextBestAction.title if roadmap.nextBestAction else None,
    )
