"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, CircleAlert, CircleCheckBig, CircleDot, Compass, Layers3, Lock, RefreshCw, Search, Sparkles, Target } from "lucide-react";
import { AppShell } from "../components/app-shell";

type SkillRecord = {
	id: string;
	name: string;
	category: string;
	description: string;
	requiredLevel: number;
	currentLevel: number;
	status: "COMPLETED" | "CURRENT" | "AVAILABLE" | "NEEDS_ATTENTION" | "LOCKED";
	prerequisites: string[];
	dependents: string[];
	evidence: Array<{ label?: string; value?: string } | string>;
	estimatedHours: number;
};

type SkillAnalysisResponse = {
	target_role: string;
	skills: SkillRecord[];
	gaps: {
		missingSkills: string[];
		weakSkills: string[];
		verifiedSkills: string[];
		blockedSkills: string[];
		criticalBottlenecks: string[];
	};
};

type RoadmapResponse = {
	items: Array<{ skillId: string; title: string; status: string; type: string; reason: string }>;
	nextBestAction: { skillId: string; title: string; reason: string } | null;
};

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: unknown[]; last_test_score?: number }>;
	assessmentResults?: Array<{ skillId: string; answer: string; correct: boolean }>;
	practiceHistory?: Array<{ skillId: string; correct: boolean; question: string; answer: string; difficulty: string; timestamp: string }>;
	learningInsight?: string;
};

type SkillNode = SkillRecord & { roadmapStatus?: string; roadmapReason?: string };

const BACKEND_URL = "";

const CATEGORIES = ["Programming", "Backend", "Database", "AI/ML", "Cloud", "DevOps", "Tools"];
const GRAPH_GROUPS = ["Programming", "Backend", "Database", "AI/ML", "Cloud", "DevOps", "Tools"];

function titleize(value: string) {
	return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function skillLabel(skill: SkillRecord) {
	return `${skill.name} ${skill.currentLevel}% ${skill.status}`;
}

function evidenceLabel(item: SkillRecord["evidence"][number]) {
	if (typeof item === "string") return item;
	if (item && typeof item === "object") return item.label ? `${item.label}: ${item.value || ""}`.trim() : item.value || "Evidence";
	return "Evidence";
}

function getProgress(skill: SkillRecord) {
	return Math.max(0, Math.min(100, skill.requiredLevel ? Math.round((skill.currentLevel / skill.requiredLevel) * 100) : skill.currentLevel));
}

function graphColor(status: SkillRecord["status"]) {
	if (status === "COMPLETED") return "bg-emerald-400 text-slate-950 border-emerald-300";
	if (status === "NEEDS_ATTENTION") return "bg-amber-400 text-slate-950 border-amber-300";
	if (status === "CURRENT" || status === "AVAILABLE") return "bg-indigo-500 text-white border-indigo-300";
	return "bg-slate-900 text-slate-300 border-slate-700";
}

export default function SkillsPage() {
	const [analysis, setAnalysis] = useState<SkillAnalysisResponse | null>(null);
	const [roadmap, setRoadmap] = useState<RoadmapResponse | null>(null);
	const [profile, setProfile] = useState<Profile | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [selectedCategory, setSelectedCategory] = useState<string>("All");
	const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);
	const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({ Programming: true, Backend: true });
	const [zoom, setZoom] = useState(1);

	const loadSkills = async () => {
		setLoading(true);
		setError("");
		try {
			const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
			const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string } | null;
			const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "backend_ai_developer";
			const currentSkills = savedProfile?.user_skills || {};

			const [skillResponse, roadmapResponse] = await Promise.all([
				fetch(`${BACKEND_URL}/api/skills/analyze`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ target_role: targetRole, current_skills: currentSkills }),
				}),
				fetch(`${BACKEND_URL}/api/path/generate`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						target_role: targetRole,
						current_skills: currentSkills,
						daily_learning_minutes: 60,
						learning_preferences: [],
						assessment_results: savedProfile?.assessmentResults || [],
					}),
				}),
			]);

			if (!skillResponse.ok) throw new Error("Could not load skill analysis.");
			if (!roadmapResponse.ok) throw new Error("Could not load roadmap.");

			const skillData = (await skillResponse.json()) as SkillAnalysisResponse;
			const roadmapData = (await roadmapResponse.json()) as RoadmapResponse;
			if (!Array.isArray(skillData.skills)) throw new Error("Skill analysis was invalid.");
			setAnalysis(skillData);
			setRoadmap(roadmapData);
			setProfile(savedProfile || { target_role: targetRole, user_skills: currentSkills });
			setSelectedSkillId(skillData.skills.find((skill) => skill.status !== "LOCKED")?.id || skillData.skills[0]?.id || null);
		} catch (cause) {
			setError(cause instanceof Error ? cause.message : "Could not load skills.");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		void loadSkills();
	}, []);

	const skills = useMemo<SkillNode[]>(() => {
		const roadmapLookup = new Map((roadmap?.items || []).map((item) => [item.skillId, item]));
		return (analysis?.skills || []).map((skill) => ({
			...skill,
			roadmapStatus: roadmapLookup.get(skill.id)?.status,
			roadmapReason: roadmapLookup.get(skill.id)?.reason,
		}));
	}, [analysis, roadmap]);

	const selectedSkill = skills.find((skill) => skill.id === selectedSkillId) || skills[0] || null;
	const categorySkills = selectedCategory === "All" ? skills : skills.filter((skill) => skill.category === selectedCategory);
	const groupedByCategory = useMemo(() => {
		const groups = new Map<string, SkillNode[]>();
		for (const skill of skills) {
			const bucket = groups.get(skill.category) || [];
			bucket.push(skill);
			groups.set(skill.category, bucket);
		}
		return GRAPH_GROUPS.map((category) => ({ category, skills: groups.get(category) || [] })).filter((group) => group.skills.length > 0);
	}, [skills]);

	const graphRows = useMemo(() => {
		return groupedByCategory.filter((group) => selectedCategory === "All" || group.category === selectedCategory || expandedCategories[group.category]);
	}, [expandedCategories, groupedByCategory, selectedCategory]);

	const updateProfileFromSelection = (nextSkillId: string) => {
		setSelectedSkillId(nextSkillId);
	};

	if (loading) {
		return (
			<AppShell title="Skills">
				<div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-28 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-56 animate-pulse rounded-2xl bg-slate-800/70" />
					</div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-40 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-72 animate-pulse rounded-2xl bg-slate-800/70" />
					</div>
				</div>
			</AppShell>
		);
	}

	if (error) {
		return (
			<AppShell title="Skills">
				<div className="mx-auto max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Skills unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
					<button onClick={() => void loadSkills()} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950">
						<RefreshCw className="h-4 w-4" /> Retry
					</button>
				</div>
			</AppShell>
		);
	}

	if (!analysis || skills.length === 0) {
		return (
			<AppShell title="Skills">
				<div className="mx-auto max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center">
					<Compass className="mx-auto h-10 w-10 text-emerald-400" />
					<h2 className="mt-4 text-2xl font-black text-white">No skill data yet</h2>
					<p className="mt-2 text-sm text-slate-400">We need learner evidence before we can render the skill graph.</p>
				</div>
			</AppShell>
		);
	}

	const weakAreas = selectedSkill
		? [
				selectedSkill.currentLevel < selectedSkill.requiredLevel ? `Gap of ${selectedSkill.requiredLevel - selectedSkill.currentLevel} points` : "On track",
				selectedSkill.status === "NEEDS_ATTENTION" ? "Needs focused practice" : "No major issue",
				selectedSkill.prerequisites.length ? `Prerequisites: ${selectedSkill.prerequisites.map(titleize).join(", ")}` : "No prerequisites",
		  ]
		: [];

	return (
		<AppShell title="Skills">
			<div className="space-y-5">
				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex flex-wrap items-center justify-between gap-3">
						<div>
							<p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
								<Sparkles className="h-3.5 w-3.5" /> Skill engine
							</p>
							<h2 className="mt-3 text-3xl font-black text-white">Skills and dependency graph</h2>
							<p className="mt-2 text-sm text-slate-400">Built from the central learner state and the deterministic skill engine.</p>
						</div>
						<div className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2">
							<Search className="h-4 w-4 text-slate-400" />
							<select value={selectedCategory} onChange={(event) => setSelectedCategory(event.target.value)} className="bg-transparent text-sm text-slate-200 outline-none">
								<option value="All">All categories</option>
								{CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
							</select>
						</div>
					</div>
					<div className="mt-5 flex flex-wrap gap-2">
						{CATEGORIES.map((category) => (
							<button
								key={category}
								onClick={() => setSelectedCategory((current) => (current === category ? "All" : category))}
								className={`rounded-lg border px-3 py-2 text-[10px] font-black uppercase tracking-wide ${selectedCategory === category ? "border-emerald-400 bg-emerald-400 text-slate-950" : "border-slate-800 text-slate-400 hover:text-white"}`}
							>
								{category}
							</button>
						))}
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
					<div className="space-y-4">
						{categorySkills.map((skill) => (
							<button
								key={skill.id}
								onClick={() => updateProfileFromSelection(skill.id)}
								className={`w-full rounded-2xl border p-4 text-left transition-colors ${selectedSkill?.id === skill.id ? "border-emerald-400 bg-emerald-400/10" : "border-slate-800 bg-slate-900/70 hover:border-slate-600"}`}
							>
								<div className="flex items-start justify-between gap-3">
									<div className="min-w-0">
										<p className="break-words text-sm font-black leading-tight text-white">{skill.name}</p>
										<p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">{skill.category}</p>
									</div>
									<div className={`rounded-full border px-2.5 py-1 text-[10px] font-black uppercase ${skill.status === "COMPLETED" ? "border-emerald-400 bg-emerald-400 text-slate-950" : skill.status === "NEEDS_ATTENTION" ? "border-amber-400 bg-amber-400 text-slate-950" : skill.status === "LOCKED" ? "border-slate-700 text-slate-400" : "border-indigo-400 bg-indigo-400 text-white"}`}>
										{skill.status}
									</div>
								</div>
								<div className="mt-4 grid gap-2 sm:grid-cols-3">
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
										<p className="text-[10px] uppercase text-slate-500">Current</p>
										<p className="mt-1 text-lg font-black text-white">{skill.currentLevel}%</p>
									</div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
										<p className="text-[10px] uppercase text-slate-500">Target</p>
										<p className="mt-1 text-lg font-black text-white">{skill.requiredLevel}%</p>
									</div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
										<p className="text-[10px] uppercase text-slate-500">Progress</p>
										<p className="mt-1 text-lg font-black text-emerald-400">{getProgress(skill)}%</p>
									</div>
								</div>
								<div className="mt-4">
									<div className="h-2 rounded-full bg-slate-800">
										<div className={`h-2 rounded-full ${skill.status === "COMPLETED" ? "bg-emerald-400" : skill.status === "NEEDS_ATTENTION" ? "bg-amber-400" : "bg-indigo-400"}`} style={{ width: `${getProgress(skill)}%` }} />
									</div>
								</div>
								<div className="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-500">
									<span className="flex items-center gap-1"><CircleCheckBig className="h-3.5 w-3.5 text-emerald-400" /> {skill.evidence.length} evidence items</span>
									<span>{skill.dependents.length} dependent skills</span>
								</div>
							</button>
						))}
					</div>

					<div className="space-y-5">
						<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex flex-wrap items-center justify-between gap-3">
								<div>
									<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Skill details</p>
									<h3 className="mt-2 break-words text-2xl font-black leading-tight text-white">{selectedSkill?.name}</h3>
									<p className="mt-2 text-sm text-slate-400">{selectedSkill?.description}</p>
								</div>
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 px-3 py-2 text-xs text-slate-300">{roadmap?.nextBestAction?.skillId === selectedSkill?.id ? "Next best action" : selectedSkill?.roadmapStatus || selectedSkill?.status}</div>
							</div>

							<div className="mt-5 grid gap-3 sm:grid-cols-3">
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] uppercase text-slate-500">Current level</p>
									<p className="mt-1 text-2xl font-black text-white">{selectedSkill?.currentLevel}%</p>
								</div>
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] uppercase text-slate-500">Target level</p>
									<p className="mt-1 text-2xl font-black text-white">{selectedSkill?.requiredLevel}%</p>
								</div>
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] uppercase text-slate-500">Gap</p>
									<p className="mt-1 text-2xl font-black text-amber-400">{selectedSkill ? Math.max(0, selectedSkill.requiredLevel - selectedSkill.currentLevel) : 0}</p>
								</div>
							</div>

							<div className="mt-5 grid gap-3 sm:grid-cols-2">
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] font-bold uppercase tracking-wide text-emerald-400">Evidence</p>
									<div className="mt-3 space-y-2">
										{selectedSkill?.evidence.length ? selectedSkill.evidence.map((item, index) => (
											<div key={index} className="rounded-lg border border-slate-800 px-3 py-2 text-sm text-slate-300">
												{evidenceLabel(item)}
											</div>
										)) : <p className="text-sm text-slate-500">No evidence recorded yet.</p>}
									</div>
								</div>
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] font-bold uppercase tracking-wide text-indigo-400">Weak areas</p>
									<div className="mt-3 space-y-2 text-sm text-slate-300">
										{weakAreas.map((item) => <div key={item} className="rounded-lg border border-slate-800 px-3 py-2">{item}</div>)}
									</div>
								</div>
							</div>

							<div className="mt-5 grid gap-3 sm:grid-cols-2">
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Prerequisites</p>
									<p className="mt-2 text-sm text-slate-300">{selectedSkill?.prerequisites.length ? selectedSkill.prerequisites.map(titleize).join(", ") : "None"}</p>
								</div>
								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] font-bold uppercase tracking-wide text-slate-400">Dependent skills</p>
									<p className="mt-2 text-sm text-slate-300">{selectedSkill?.dependents.length ? selectedSkill.dependents.map(titleize).join(", ") : "None"}</p>
								</div>
							</div>

							<div className="mt-5 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
								<p className="text-[10px] font-bold uppercase tracking-wide text-emerald-400">Recommended action</p>
								<p className="mt-2 text-sm leading-relaxed text-slate-300">
									{selectedSkill?.status === "COMPLETED"
										? "This skill is verified. Continue to the next dependent node."
										: selectedSkill?.status === "NEEDS_ATTENTION"
											? "Focus on reinforcement practice and a fresh assessment before moving forward."
											: selectedSkill?.status === "LOCKED"
												? "Complete the prerequisites to unlock this skill."
												: "Work through the learning, practice, and assessment loop for this skill."}
								</p>
							</div>
						</section>

						<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex flex-wrap items-center justify-between gap-3">
								<div>
									<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">Dependency graph</p>
									<h3 className="mt-2 text-xl font-black text-white">Grouped, readable, and expandable</h3>
								</div>
								<div className="flex items-center gap-2">
									<button onClick={() => setZoom((current) => Math.max(0.7, Math.round((current - 0.1) * 10) / 10))} className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-bold text-slate-300">-</button>
									<span className="min-w-14 text-center text-xs text-slate-500">{Math.round(zoom * 100)}%</span>
									<button onClick={() => setZoom((current) => Math.min(1.5, Math.round((current + 0.1) * 10) / 10))} className="rounded-lg border border-slate-800 px-3 py-2 text-xs font-bold text-slate-300">+</button>
								</div>
							</div>

							<div className="mt-4 overflow-x-auto">
								<div className="min-w-[760px] space-y-6" style={{ transform: `scale(${zoom})`, transformOrigin: "top left" }}>
									{graphRows.map((group) => {
										const expanded = expandedCategories[group.category] ?? true;
										return (
											<div key={group.category} className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
												<button
													onClick={() => setExpandedCategories((current) => ({ ...current, [group.category]: !expanded }))}
													className="flex w-full items-center justify-between text-left"
												>
													<div>
														<p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{group.category}</p>
														<p className="mt-1 text-sm text-slate-400">{group.skills.length} nodes</p>
													</div>
													<span className="text-xs text-slate-400">{expanded ? "Collapse" : "Expand"}</span>
												</button>
												{expanded ? (
													<div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
														{group.skills.map((skill, index) => (
															<div key={skill.id} className="relative rounded-xl border border-slate-800 bg-slate-900/90 p-4">
																{index < group.skills.length - 1 ? <div className="absolute left-1/2 top-full h-6 w-px bg-slate-700" /> : null}
																<div className="flex items-start justify-between gap-3">
																	<div className="min-w-0">
																		<p className="break-words text-sm font-black leading-tight text-white">{skill.name}</p>
																		<p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">{skill.category}</p>
																	</div>
																	<div className={`rounded-full border px-2 py-1 text-[9px] font-black uppercase ${graphColor(skill.status)}`}>
																		{skill.status}
																	</div>
																</div>
																<div className="mt-3 flex items-center gap-2 text-[10px] text-slate-500">
																	<span>{skill.currentLevel}%</span>
																	<span>{"->"}</span>
																	<span>{skill.requiredLevel}%</span>
																</div>
																<div className="mt-3 h-2 rounded-full bg-slate-800">
																	<div className="h-2 rounded-full bg-emerald-400" style={{ width: `${getProgress(skill)}%` }} />
																</div>
																<div className="mt-3 flex flex-wrap gap-2 text-[10px] text-slate-400">
																	{skill.prerequisites.slice(0, 2).map((prereq) => <span key={prereq} className="rounded-full border border-slate-700 px-2 py-1">{titleize(prereq)}</span>)}
																</div>
																<button onClick={() => updateProfileFromSelection(skill.id)} className="mt-4 inline-flex items-center gap-2 text-xs font-bold text-emerald-400">
																	View details <ArrowRight className="h-3.5 w-3.5" />
																</button>
															</div>
														))}
													</div>
												) : null}
											</div>
										);
									})}
								</div>
							</div>
						</section>

						<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
								<span className="flex items-center gap-1.5"><Layers3 className="h-3.5 w-3.5" /> {skills.length} total skills</span>
								<span className="flex items-center gap-1.5"><Lock className="h-3.5 w-3.5" /> {analysis.gaps.blockedSkills.length} locked</span>
								<span className="flex items-center gap-1.5"><BookOpen className="h-3.5 w-3.5" /> {analysis.gaps.verifiedSkills.length} verified</span>
								{roadmap?.nextBestAction ? <span className="flex items-center gap-1.5 text-emerald-400"><Target className="h-3.5 w-3.5" /> Next: {titleize(roadmap.nextBestAction.skillId)}</span> : null}
							</div>
						</section>
					</div>
				</section>
			</div>
		</AppShell>
	);
}
