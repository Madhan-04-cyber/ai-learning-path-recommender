"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, CircleAlert, CircleDot, Clock3, Compass, Lock, RefreshCw, Sparkles, Target } from "lucide-react";
import { AppShell } from "../components/app-shell";

type RoadmapItem = {
	id: string;
	skillId: string;
	title: string;
	type: "LEARN" | "PRACTICE" | "PROJECT" | "ASSESSMENT" | "REVIEW";
	reason: string;
	prerequisites: string[];
	estimatedTime: string;
	difficulty: string;
	status: string;
	resources: { title?: string; type?: string; url?: string }[];
	assessment: { required?: boolean; skillId?: string };
	project: { title?: string; description?: string; requirements?: string[] };
};

type RoadmapData = {
	items: RoadmapItem[];
	nextBestAction: RoadmapItem | null;
	estimatedDuration: string;
	validation: { valid: boolean; errors: string[] };
};

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string }>;
	dailyLearningMinutes?: number;
	daily_learning_minutes?: number;
	learningPreferences?: string[];
	assessmentResults?: unknown[];
};

type NodeGroup = {
	skillId: string;
	label: string;
	status: string;
	items: RoadmapItem[];
};

const BACKEND_URL = "";

const statusLabel: Record<string, string> = {
	CURRENT: "Current",
	AVAILABLE: "Available",
	NEEDS_ATTENTION: "Needs attention",
	LOCKED: "Locked",
	COMPLETED: "Completed",
};

const skillStageOrder = ["COMPLETED", "CURRENT", "AVAILABLE", "NEEDS_ATTENTION", "LOCKED"];
const typeOrder = ["LEARN", "PROJECT", "ASSESSMENT", "PRACTICE", "REVIEW"];

const makeTitle = (value?: string) => value?.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) || "Untitled skill";

function getStatusRank(status: string) {
	return skillStageOrder.indexOf(status);
}

function getTypeRank(type: RoadmapItem["type"]) {
	return typeOrder.indexOf(type);
}

function getStatusForGroup(items: RoadmapItem[]) {
	for (const status of skillStageOrder) {
		if (items.some((item) => item.status === status)) return status;
	}
	return items[0]?.status || "LOCKED";
}

export default function PathPage() {
	const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
	const [profile, setProfile] = useState<Profile | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [statusFilter, setStatusFilter] = useState<"ALL" | "CURRENT" | "COMPLETED" | "LOCKED">("ALL");
	const [typeFilter, setTypeFilter] = useState<"ALL" | "SKILLS" | "PROJECTS" | "ASSESSMENTS">("ALL");
	const [selectedSkillId, setSelectedSkillId] = useState<string | null>(null);

	const loadRoadmap = async () => {
		setLoading(true);
		setError("");
		try {
			const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
			const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string } | null;
			const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "backend_ai_developer";
			const currentSkills = savedProfile?.user_skills || {};
			setProfile(savedProfile || { target_role: targetRole, user_skills: currentSkills });

			const response = await fetch(`${BACKEND_URL}/api/path/generate`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					target_role: targetRole,
					current_skills: currentSkills,
					daily_learning_minutes: savedProfile?.dailyLearningMinutes || savedProfile?.daily_learning_minutes || 60,
					learning_preferences: savedProfile?.learningPreferences || [],
					assessment_results: savedProfile?.assessmentResults || [],
				}),
			});
			if (!response.ok) throw new Error("We could not build your learning route.");
			const data = (await response.json()) as RoadmapData;
			if (!Array.isArray(data.items)) throw new Error("The roadmap response was invalid.");
			setRoadmap(data);
			const firstSelected = data.nextBestAction?.skillId || data.items.find((item) => item.status === "CURRENT")?.skillId || data.items[0]?.skillId || null;
			setSelectedSkillId(firstSelected);
		} catch (cause) {
			setError(cause instanceof Error ? cause.message : "We could not build your learning route.");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		void loadRoadmap();
	}, []);

	const groupedNodes = useMemo<NodeGroup[]>(() => {
		if (!roadmap?.items) return [];
		const groups = new Map<string, RoadmapItem[]>();
		for (const item of roadmap.items) {
			const bucket = groups.get(item.skillId) || [];
			bucket.push(item);
			groups.set(item.skillId, bucket);
		}
		return Array.from(groups.entries())
			.map(([skillId, items]) => ({
				skillId,
				label: makeTitle(items[0]?.title || skillId),
				status: getStatusForGroup(items),
				items: items.sort((a, b) => getTypeRank(a.type) - getTypeRank(b.type)),
			}))
			.sort((a, b) => {
				const statusDelta = getStatusRank(a.status) - getStatusRank(b.status);
				if (statusDelta !== 0) return statusDelta;
				return roadmap.items.findIndex((item) => item.skillId === a.skillId) - roadmap.items.findIndex((item) => item.skillId === b.skillId);
			});
	}, [roadmap]);

	const selectedGroup = groupedNodes.find((node) => node.skillId === selectedSkillId) || null;
	const selectedNodeItem = selectedGroup?.items.find((item) => item.type === "LEARN") || selectedGroup?.items[0] || null;
	const currentSkill = selectedSkillId ? profile?.user_skills?.[selectedSkillId] : undefined;

	const filteredGroups = useMemo(() => {
		return groupedNodes.filter((group) => {
			const statusMatch =
				statusFilter === "ALL" ||
				(statusFilter === "CURRENT" ? ["CURRENT", "AVAILABLE", "NEEDS_ATTENTION"].includes(group.status) : group.status === statusFilter);
			const typeMatch =
				typeFilter === "ALL" ||
				(typeFilter === "SKILLS" ? group.items.some((item) => item.type === "LEARN" || item.type === "PRACTICE" || item.type === "REVIEW") : typeFilter === "PROJECTS" ? group.items.some((item) => item.type === "PROJECT") : group.items.some((item) => item.type === "ASSESSMENT"));
			return statusMatch && typeMatch;
		});
	}, [groupedNodes, statusFilter, typeFilter]);

	const visibleGroups = filteredGroups.length > 0 ? filteredGroups : groupedNodes;

	if (loading) {
		return (
			<AppShell title="My Path">
				<div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-28 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-40 animate-pulse rounded-2xl bg-slate-800/70" />
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
			<AppShell title="My Path">
				<div className="mx-auto max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Your route is unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
					<button onClick={() => void loadRoadmap()} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950">
						<RefreshCw className="h-4 w-4" /> Retry
					</button>
				</div>
			</AppShell>
		);
	}

	if (!roadmap || roadmap.items.length === 0) {
		return (
			<AppShell title="My Path">
				<div className="mx-auto max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/70 p-8 text-center">
					<Compass className="mx-auto h-10 w-10 text-emerald-400" />
					<h2 className="mt-4 text-2xl font-black text-white">No roadmap yet</h2>
					<p className="mt-2 text-sm text-slate-400">Complete onboarding and diagnostic data so we can build your learning GPS.</p>
				</div>
			</AppShell>
		);
	}

	return (
		<AppShell title="My Path">
			<div className="space-y-5">
				<section className="rounded-2xl border border-slate-800 bg-[linear-gradient(135deg,rgba(15,23,42,0.98),rgba(8,15,28,0.92))] p-5">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Learning GPS</div>
					<div className="mt-4 grid gap-4 lg:grid-cols-[1fr_auto_1fr_auto_1fr_auto_1fr_auto_1fr] lg:items-center">
						{[
							["START", "The route begins here"],
							["â†“", ""],
							["Completed skills", `${groupedNodes.filter((node) => node.status === "COMPLETED").length} verified`],
							["â†“", ""],
							["Current skill", selectedGroup?.label || "Select a node"],
							["â†“", ""],
							["Future skills", `${groupedNodes.filter((node) => ["AVAILABLE", "LOCKED"].includes(node.status)).length} ahead`],
							["â†“", ""],
							["Career Ready", roadmap.estimatedDuration],
						].map(([label, detail], index) => (
							<div key={`${label}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950/60 px-4 py-3 text-center">
								<p className="break-words text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">{label}</p>
								{detail ? <p className="mt-1 text-xs text-slate-500">{detail}</p> : null}
							</div>
						))}
					</div>
				</section>

				<section className="flex flex-col gap-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
					<div className="flex flex-wrap gap-2">
						{(["ALL", "CURRENT", "COMPLETED", "LOCKED"] as const).map((option) => (
							<button
								key={option}
								onClick={() => setStatusFilter(option)}
								className={`rounded-lg border px-3 py-2 text-[10px] font-black uppercase tracking-wide ${
									statusFilter === option ? "border-emerald-400 bg-emerald-400 text-slate-950" : "border-slate-800 text-slate-400 hover:text-white"
								}`}
							>
								{option === "ALL" ? "All" : option === "CURRENT" ? "Current" : option === "COMPLETED" ? "Completed" : "Locked"}
							</button>
						))}
					</div>
					<div className="flex flex-wrap gap-2">
						{(["ALL", "SKILLS", "PROJECTS", "ASSESSMENTS"] as const).map((option) => (
							<button
								key={option}
								onClick={() => setTypeFilter(option)}
								className={`rounded-lg border px-3 py-2 text-[10px] font-black uppercase tracking-wide ${
									typeFilter === option ? "border-indigo-400 bg-indigo-400 text-slate-950" : "border-slate-800 text-slate-500 hover:text-white"
								}`}
							>
								{option === "ALL" ? "All types" : option === "SKILLS" ? "Skills" : option === "PROJECTS" ? "Projects" : "Assessments"}
							</button>
						))}
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-[1fr_1.2fr]">
					<div className="space-y-3">
						{visibleGroups.map((group, index) => {
							const active = group.skillId === selectedSkillId;
							return (
								<button
									key={group.skillId}
									onClick={() => setSelectedSkillId(group.skillId)}
									className={`w-full rounded-2xl border p-4 text-left transition-colors ${
										active ? "border-emerald-400 bg-emerald-400/10" : "border-slate-800 bg-slate-900/70 hover:border-slate-600"
									}`}
								>
									<div className="flex items-start gap-3">
										<div className={`mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-black ${group.status === "COMPLETED" ? "bg-emerald-400 text-slate-950" : "bg-slate-800 text-slate-300"}`}>
											{group.status === "COMPLETED" ? <CircleDot className="h-4 w-4" /> : index + 1}
										</div>
										<div className="min-w-0 flex-1">
											<div className="flex flex-wrap items-center gap-2">
												<h3 className="break-words text-sm font-black leading-tight text-white">{group.label}</h3>
												<span className="rounded-full border border-slate-700 px-2 py-0.5 text-[9px] font-bold uppercase text-slate-400">{statusLabel[group.status] || group.status}</span>
											</div>
											<div className="mt-2 flex flex-wrap gap-2 text-[10px] text-slate-500">
												<span>{group.items.length} milestones</span>
												<span>{group.items.map((item) => item.type).filter((type, itemIndex, array) => array.indexOf(type) === itemIndex).join(" · ")}</span>
											</div>
										</div>
										<ArrowRight className="mt-1 h-4 w-4 shrink-0 text-emerald-400" />
									</div>
								</button>
							);
						})}
					</div>

					<article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-4">
							<div>
								<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Milestone details</p>
								<h2 className="mt-2 break-words text-2xl font-black leading-tight text-white">{selectedGroup?.label || "Select a node"}</h2>
							</div>
							{selectedNodeItem ? <span className="rounded-full border border-slate-700 px-2.5 py-1 text-[10px] font-bold uppercase text-slate-400">{selectedNodeItem.type}</span> : null}
						</div>

						{selectedNodeItem ? (
							<div className="mt-5 space-y-5">
								<div className="grid gap-3 sm:grid-cols-2">
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
										<p className="text-[10px] uppercase text-slate-500">Current proficiency</p>
										<p className="mt-1 text-2xl font-black text-white">{currentSkill?.proficiency ?? 0}%</p>
									</div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
										<p className="text-[10px] uppercase text-slate-500">Target proficiency</p>
										<p className="mt-1 text-2xl font-black text-emerald-400">{selectedGroup?.status === "COMPLETED" ? "Verified" : selectedGroup?.status === "LOCKED" ? "Unlock next" : "70%+"}</p>
									</div>
								</div>

								<div className="grid gap-3 sm:grid-cols-2">
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
										<p className="text-[10px] uppercase text-slate-500">Prerequisites</p>
										<p className="mt-2 text-sm text-slate-300">{selectedNodeItem.prerequisites.length ? selectedNodeItem.prerequisites.join(" · ") : "None"}</p>
									</div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
										<p className="text-[10px] uppercase text-slate-500">Estimated time</p>
										<p className="mt-2 text-sm font-bold text-slate-200">{selectedNodeItem.estimatedTime}</p>
										<p className="mt-1 text-xs text-slate-500">Difficulty: {selectedNodeItem.difficulty}</p>
									</div>
								</div>

								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">Why recommended</p>
									<p className="mt-2 text-sm leading-relaxed text-slate-300">{selectedNodeItem.reason}</p>
								</div>

								<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><BookOpen className="h-3.5 w-3.5" /> Learning resources</div>
									<div className="mt-3 grid gap-2">
										{selectedNodeItem.resources.length ? selectedNodeItem.resources.map((resource, index) => (
											<a key={`${resource.title || "resource"}-${index}`} href={resource.url || "#"} target={resource.url ? "_blank" : undefined} rel="noreferrer" className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/70 px-3 py-2 text-sm text-slate-300 hover:border-slate-600">
												<span className="min-w-0 flex-1 break-words">
													<span className="block break-words font-bold text-white">{resource.title || "Resource"}</span>
													<span className="block text-[10px] uppercase tracking-wide text-slate-500">{resource.type || "Link"}</span>
												</span>
												<ArrowRight className="h-4 w-4 shrink-0 text-slate-500" />
											</a>
										)) : <p className="text-sm text-slate-500">No resources attached to this node.</p>}
									</div>
								</div>

								<div className="grid gap-3 sm:grid-cols-3">
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Practice</p><p className="mt-2 text-sm text-slate-300">{selectedNodeItem.type === "PRACTICE" || selectedNodeItem.type === "REVIEW" || selectedNodeItem.type === "LEARN" ? "Practice is embedded in the route for this node." : "Practice is covered on the skill node."}</p></div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Assessment</p><p className="mt-2 text-sm text-slate-300">{selectedNodeItem.assessment?.required ? "Assessment required to unlock the next step." : "Assessment available on demand."}</p></div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Project</p><p className="mt-2 text-sm text-slate-300">{selectedNodeItem.project?.title || "Project milestone not defined."}</p></div>
								</div>

								{selectedNodeItem.project?.description ? <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">Project</p><p className="mt-2 text-sm leading-relaxed text-slate-300">{selectedNodeItem.project.description}</p></div> : null}
							</div>
						) : (
							<div className="py-16 text-center text-sm text-slate-500">Select a roadmap node to see details.</div>
						)}
					</article>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
						<span className="flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> {roadmap.estimatedDuration}</span>
						<span className="flex items-center gap-1.5"><Target className="h-3.5 w-3.5" /> {roadmap.validation.valid ? "Route validated" : "Route needs review"}</span>
						{roadmap.validation.errors.length ? <span className="break-words text-rose-400">{roadmap.validation.errors.join(" · ")}</span> : null}
					</div>
				</section>
			</div>
		</AppShell>
	);
}

