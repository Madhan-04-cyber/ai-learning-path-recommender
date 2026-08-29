"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, BookOpen, CircleAlert, CheckCircle2, ChevronDown, ChevronUp, Clock3, FolderKanban, RefreshCw, Sparkles, Target } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	target_role?: string;
	interest?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: unknown[] }>;
	assessmentResults?: unknown[];
};

type ProjectMilestone = {
	milestone_id: string;
	title: string;
	description?: string;
	objective: string;
	required_skills: string[];
	concepts: string[];
	learning_concepts?: string[];
	prerequisites: string[];
	build_task?: string;
	learning_tasks: string[];
	practice_tasks: string[];
	implementation_steps: string[];
	checkpoint: string;
	expected_output: string;
	common_mistakes?: string[];
	hints?: string[];
	unlock_conditions?: string[];
	estimated_minutes?: number;
	status?: "LOCKED" | "AVAILABLE" | "IN_PROGRESS" | "COMPLETED";
	completion_status: "locked" | "available" | "completed" | "in_progress";
};

type ProjectData = {
	project_id: string;
	title: string;
	domain: string;
	career: string;
	description: string;
	difficulty: string;
	estimatedTime: string;
	required_skills: string[];
	optional_skills: string[];
	milestones: ProjectMilestone[];
	expected_outcomes: string[];
	assessment: { criteria?: string[]; requires_evidence?: boolean };
	project_theme: string;
	projectBlueprint: {
		whatYouAreBuilding: string;
		requirements: string[];
		techStack: string[];
		architecture: string[];
		setup: string[];
		implementationTasks: string[];
		validationChecks: string[];
		commonMistakes: string[];
		troubleshooting: string[];
		currentStepGuide?: Array<{ title: string; explanation: string }>;
	};
};

type ProjectSessionResponse = {
	target_role: string;
	skill_id: string;
	project: ProjectData;
	current_milestone: ProjectMilestone | null;
	next_milestone: ProjectMilestone | null;
	build_guide: ProjectData["projectBlueprint"];
};

type ResourcesResponse = {
	career: string;
	projects: Array<{
		skillId: string;
		title: string;
		status: string;
		proficiency: number;
		project: ProjectData;
	}>;
};

type SelectionHint = {
	skillId: string;
	title: string;
	project: ProjectData;
	proficiency: number;
	status: string;
};

type ProjectState = {
	skillId?: string;
	projectId?: string;
	completedMilestones?: string[];
	currentMilestoneId?: string;
	inProgressMilestoneId?: string;
	hintsRevealed?: string[];
};

const BACKEND_URL = "";

function safeParse<T>(value: string | null, fallback: T): T {
	if (!value) return fallback;
	try {
		return JSON.parse(value) as T;
	} catch {
		return fallback;
	}
}

function titleize(value?: string | null) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Unknown";
}

function statusLabel(status: ProjectMilestone["completion_status"]) {
	if (status === "completed") return "COMPLETED";
	if (status === "in_progress") return "IN PROGRESS";
	if (status === "available") return "AVAILABLE";
	return "LOCKED";
}

function statusClass(status: ProjectMilestone["completion_status"]) {
	if (status === "completed") return "bg-emerald-400 text-slate-950";
	if (status === "in_progress") return "bg-amber-400 text-slate-950";
	if (status === "available") return "bg-indigo-400 text-white";
	return "bg-slate-800 text-slate-400";
}

function normalizeStatus(status?: ProjectMilestone["status"] | ProjectMilestone["completion_status"]): ProjectMilestone["completion_status"] {
	if (status === "COMPLETED") return "completed";
	if (status === "IN_PROGRESS") return "in_progress";
	if (status === "AVAILABLE") return "available";
	if (status === "LOCKED") return "locked";
	return status || "locked";
}

function normalizeMilestoneState(
	milestone: ProjectMilestone,
	state: ProjectState,
): ProjectMilestone {
	if (state.completedMilestones?.includes(milestone.milestone_id)) {
		return { ...milestone, status: "COMPLETED", completion_status: "completed" };
	}
	if (state.inProgressMilestoneId === milestone.milestone_id || state.currentMilestoneId === milestone.milestone_id) {
		return { ...milestone, status: "IN_PROGRESS", completion_status: "in_progress" };
	}
	if (milestone.completion_status === "available") {
		return { ...milestone, status: "AVAILABLE", completion_status: "available" };
	}
	return { ...milestone, status: "LOCKED", completion_status: "locked" };
}

export default function ProjectPage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [summary, setSummary] = useState<ResourcesResponse | null>(null);
	const [session, setSession] = useState<ProjectSessionResponse | null>(null);
	const [projectState, setProjectState] = useState<ProjectState>({});
	const [selectedSkillId, setSelectedSkillId] = useState("");
	const [selectedMilestoneId, setSelectedMilestoneId] = useState("");
	const [loading, setLoading] = useState(true);
	const [sessionLoading, setSessionLoading] = useState(false);
	const [completing, setCompleting] = useState(false);
	const [aiLoading, setAiLoading] = useState(false);
	const [error, setError] = useState("");
	const [message, setMessage] = useState("");
	const [coachReply, setCoachReply] = useState("");
	const [mentorPrompt, setMentorPrompt] = useState("");
	const [showHints, setShowHints] = useState(false);
	const [expandedSteps, setExpandedSteps] = useState<number[]>([0]);
	const [checkpointChecks, setCheckpointChecks] = useState<Record<string, boolean>>({});
	const [implementationNotes, setImplementationNotes] = useState("");
	const [implementationResult, setImplementationResult] = useState("");
	const [codeSnippet, setCodeSnippet] = useState("");
	const [score, setScore] = useState(80);

	const persistProjectState = (next: ProjectState) => {
		setProjectState(next);
		window.localStorage.setItem("pathmind_project_state", JSON.stringify(next));
	};

	const chooseProject = (projects: ResourcesResponse["projects"], interest: string): SelectionHint | null => {
		if (!projects.length) return null;
		const normalizedInterest = interest.toLowerCase();
		const themed = projects.find((item) => {
			const title = item.project.title.toLowerCase();
			const theme = item.project.project_theme.toLowerCase();
			return normalizedInterest && (title.includes(normalizedInterest) || theme.includes(normalizedInterest) || (normalizedInterest.includes("cricket") && title.includes("ipl")));
		});
		const unlocked = projects.find((item) => item.status !== "LOCKED");
		const selected = themed || unlocked || projects[0];
		return selected ? { ...selected } : null;
	};

	const applyProjectSession = (data: ProjectSessionResponse, nextState: ProjectState) => {
		const mergedMilestones = data.project.milestones.map((milestone) => normalizeMilestoneState(milestone, nextState));
		const current = mergedMilestones.find((item) => item.status === "AVAILABLE" || item.status === "IN_PROGRESS") || mergedMilestones.find((item) => item.status !== "LOCKED") || mergedMilestones[0] || null;
		const mergedProject = { ...data.project, milestones: mergedMilestones };
		const mergedSession = {
			...data,
			project: mergedProject,
			current_milestone: current,
			next_milestone: mergedMilestones.find((item) => item.status === "LOCKED") || null,
		};
		setSession(mergedSession);
		setSelectedMilestoneId(current?.milestone_id || mergedMilestones[0]?.milestone_id || "");
		if (current) {
			persistProjectState({
				...nextState,
				skillId: data.skill_id,
				projectId: data.project.project_id,
				currentMilestoneId: current.milestone_id,
			});
		}
	};

	const startProject = async (targetRole: string, skillId: string, proficiency: number, interest = "", learnerSkills: Profile["user_skills"] = profile?.user_skills || {}, state: ProjectState = projectState) => {
		setSessionLoading(true);
		setError("");
		try {
			const response = await fetch(`${BACKEND_URL}/api/project/start`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ target_role: targetRole, skill_id: skillId, proficiency, current_skills: learnerSkills || {}, interest }),
			});
			if (!response.ok) throw new Error("No active project yet.");
			const data = (await response.json()) as ProjectSessionResponse;
			applyProjectSession(data, state);
		} catch (cause) {
			setError(cause instanceof Error ? cause.message : "Project workspace unavailable.");
		} finally {
			setSessionLoading(false);
		}
	};

	const loadPage = async () => {
		setLoading(true);
		setError("");
		try {
			const savedProfile = safeParse<Profile | null>(window.localStorage.getItem("pathmind_profile"), null);
			const savedAnalysis = safeParse<{ matched_career_id?: string } | null>(window.localStorage.getItem("pathmind_analysis"), null);
			const savedProjectState = safeParse<ProjectState | null>(window.localStorage.getItem("pathmind_project_state"), null) || {};
			const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "";
			if (!targetRole) throw new Error("Start with a career goal before opening Project.");
			const currentSkills = savedProfile?.user_skills || {};
			setProfile(savedProfile || { target_role: targetRole, user_skills: currentSkills });
			setProjectState(savedProjectState);

			const resourcesResponse = await fetch(`${BACKEND_URL}/api/resources/summary`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ target_role: targetRole, current_skills: currentSkills, interest: savedProfile?.interest || "" }),
			});
			if (!resourcesResponse.ok) throw new Error("No active project yet.");
			const resourcesData = (await resourcesResponse.json()) as ResourcesResponse;
			setSummary(resourcesData);
			const chosenProject = chooseProject(resourcesData.projects, savedProfile?.interest || "");
			if (chosenProject) {
				setSelectedSkillId(chosenProject.skillId);
				await startProject(targetRole, chosenProject.skillId, currentSkills[chosenProject.skillId]?.proficiency ?? 0, savedProfile?.interest || "", currentSkills, savedProjectState);
			}
		} catch (cause) {
			setError(cause instanceof Error ? cause.message : "Project workspace unavailable.");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		void loadPage();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	useEffect(() => {
		window.localStorage.setItem("pathmind_project_state", JSON.stringify(projectState));
	}, [projectState]);

	const milestones = session?.project.milestones || [];
	const activeMilestone = useMemo(
		() => milestones.find((item) => item.milestone_id === selectedMilestoneId) || session?.current_milestone || milestones[0] || null,
		[milestones, selectedMilestoneId, session],
	);
	const completedCount = milestones.filter((item) => item.status === "COMPLETED").length;
	const availableCount = milestones.filter((item) => item.status === "AVAILABLE").length;
	const lockedCount = milestones.filter((item) => item.status === "LOCKED").length;
	const currentSkillId = session?.skill_id || selectedSkillId || "";
	const currentSkillProfile = currentSkillId ? profile?.user_skills?.[currentSkillId] : undefined;
	const nextBestAction = activeMilestone?.status === "AVAILABLE" ? `Start ${activeMilestone.title}` : session?.project.projectBlueprint?.implementationTasks?.[0] || session?.project.title || "Continue your project";
	const hintsForMilestone = activeMilestone?.hints || [];
	const steps = activeMilestone?.implementation_steps || [];
	const isHintVisible = !!activeMilestone && showHints;

	const startMilestone = (milestoneId: string) => {
		setSelectedMilestoneId(milestoneId);
		persistProjectState({
			...projectState,
			currentMilestoneId: milestoneId,
			inProgressMilestoneId: milestoneId,
			skillId: currentSkillId,
			projectId: session?.project.project_id,
		});
		setMessage("");
	};

	const toggleStep = (index: number) => {
		setExpandedSteps((current) => (current.includes(index) ? current.filter((item) => item !== index) : [...current, index]));
	};

	const toggleCheckpoint = (label: string) => {
		setCheckpointChecks((current) => ({ ...current, [label]: !current[label] }));
	};

	const completeMilestone = async () => {
		if (!session || !profile?.target_role || !currentSkillId || !activeMilestone) return;
		if (activeMilestone.status === "LOCKED") {
			setMessage("This milestone is locked.");
			return;
		}
		setCompleting(true);
		setMessage("");
		try {
			const required = activeMilestone.prerequisites || [];
			const prereqsSatisfied = required.every((item) => (projectState.completedMilestones || []).some((value) => value.startsWith(item.replace(":plan", "")) || value === item));
			if (!prereqsSatisfied && activeMilestone.status !== "AVAILABLE" && activeMilestone.status !== "IN_PROGRESS") {
				throw new Error("Prerequisites are not yet satisfied.");
			}
			const checkpointSatisfied = Object.values(checkpointChecks).some(Boolean) || implementationNotes.trim().length > 0 || implementationResult.trim().length > 0 || codeSnippet.trim().length > 0;
			if (!checkpointSatisfied) throw new Error("Please complete the checkpoint or add milestone evidence first.");
			const response = await fetch(`${BACKEND_URL}/api/project/complete`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					target_role: profile.target_role,
					skill_id: currentSkillId,
					project_title: session.project.title,
					score,
					user_skills: profile.user_skills || {},
					evidence_summary: [
						implementationNotes,
						implementationResult,
						codeSnippet ? `Code: ${codeSnippet}` : "",
					].filter(Boolean).join(" | "),
				}),
			});
			if (!response.ok) throw new Error("Project completion failed.");
			const data = (await response.json()) as { updated_skills?: Profile["user_skills"]; verification_status?: string; evidence?: unknown[] };
			const nextProfile: Profile = { ...(profile || {}), user_skills: data.updated_skills || profile.user_skills };
			setProfile(nextProfile);
			window.localStorage.setItem("pathmind_profile", JSON.stringify(nextProfile));
			const completed = Array.from(new Set([...(projectState.completedMilestones || []), activeMilestone.milestone_id]));
			const nextMilestone = milestones.find((item) => !completed.includes(item.milestone_id) && item.status !== "LOCKED");
			persistProjectState({
				...projectState,
				skillId: currentSkillId,
				projectId: session.project.project_id,
				completedMilestones: completed,
				currentMilestoneId: nextMilestone?.milestone_id,
				inProgressMilestoneId: undefined,
				hintsRevealed: projectState.hintsRevealed,
			});
			setMessage(data.verification_status || "Milestone completed.");
			setCheckpointChecks({});
			setImplementationNotes("");
			setImplementationResult("");
			setCodeSnippet("");
			await loadPage();
		} catch (cause) {
			setMessage(cause instanceof Error ? cause.message : "Could not complete milestone.");
		} finally {
			setCompleting(false);
		}
	};

	const askCoach = async () => {
		if (!session || !activeMilestone) return;
		setAiLoading(true);
		setCoachReply("");
		try {
			const milestoneBlueprint = session.project.milestones.find((item) => item.milestone_id === activeMilestone.milestone_id) || activeMilestone;
			const completedMilestones = (projectState.completedMilestones || [])
				.map((milestoneId) => session.project.milestones.find((item) => item.milestone_id === milestoneId)?.title)
				.filter((value): value is string => Boolean(value));
			const mentorMessage = mentorPrompt.trim() || `I don't understand ${activeMilestone.title}. Can you help me with the current step?`;
			const response = await fetch(`${BACKEND_URL}/api/chat`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					message: mentorMessage,
					history: [],
					target_role: profile?.target_role || session.target_role,
					user_skills: profile?.user_skills || {},
					current_page: "Project",
					current_milestone: activeMilestone.title,
					current_skill: currentSkillId,
					skill_proficiency: currentSkillProfile?.proficiency,
					weak_areas: [],
					roadmap: [],
					next_action: nextBestAction,
					project_blueprint: session.build_guide,
					project_title: session.project.title,
					project_description: session.project.description,
					project_milestone: milestoneBlueprint,
					project_milestone_description: milestoneBlueprint.description || milestoneBlueprint.objective,
					project_learning_concepts: milestoneBlueprint.learning_concepts || milestoneBlueprint.concepts || [],
					project_build_task: milestoneBlueprint.build_task || milestoneBlueprint.objective,
					project_checkpoint: milestoneBlueprint.checkpoint,
					project_milestone_skills: milestoneBlueprint.required_skills,
					project_hints_shown: projectState.hintsRevealed || [],
					completed_milestones: completedMilestones,
					relevant_assessment: profile?.assessmentResults?.at(-1) ? { last_assessment: profile.assessmentResults.at(-1) } : undefined,
				}),
			});
			if (!response.ok) throw new Error("AI coach unavailable.");
			const data = (await response.json()) as { response?: string };
			setCoachReply(data.response || "No response available.");
		} catch (cause) {
			setCoachReply(cause instanceof Error ? cause.message : "AI coach unavailable. Continue using the structured build steps and hints.");
		} finally {
			setAiLoading(false);
			setMentorPrompt("");
		}
	};

	const buildProjectGuidance = session?.project.projectBlueprint?.whatYouAreBuilding || "This project is structured as a guided learning environment built from the skill graph.";
	const stepGuide = session?.project.projectBlueprint?.currentStepGuide || [];

	if (loading) {
		return (
			<AppShell title="Project Workspace">
				<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
					<div className="h-4 w-44 animate-pulse rounded bg-slate-800" />
					<div className="mt-4 h-80 animate-pulse rounded-2xl bg-slate-800/70" />
				</div>
			</AppShell>
		);
	}

	if (error && !session) {
		return (
			<AppShell title="Project Workspace">
				<div className="mx-auto max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">No active project yet</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
					<div className="mt-6 flex flex-wrap justify-center gap-3">
						<Link href="/resources" className="rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">Go to Resources</Link>
						<Link href="/path" className="rounded-xl border border-slate-700 px-4 py-3 text-xs font-black uppercase text-slate-200">Back to Path</Link>
					</div>
				</div>
			</AppShell>
		);
	}

	return (
		<AppShell title="Project Workspace">
			<div className="space-y-5">
				<section className="rounded-2xl border border-slate-800 bg-[linear-gradient(135deg,rgba(15,23,42,0.98),rgba(8,15,28,0.92))] p-5">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
						<FolderKanban className="h-3.5 w-3.5" /> Workspace overview
					</div>
					<div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_0.7fr]">
						<div className="space-y-2">
							<h2 className="break-words text-3xl font-black text-white">{session?.project.title || "No active project yet"}</h2>
							<p className="text-sm text-slate-400">Career: {session?.project.career || titleize(profile?.target_role)}</p>
							<p className="text-sm text-slate-300">{session?.project.description}</p>
						</div>
						<div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
							<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
								<p className="text-[10px] uppercase text-slate-500">Progress</p>
								<p className="mt-1 text-2xl font-black text-white">{completedCount} / {milestones.length || 0} milestones completed</p>
							</div>
							<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
								<p className="text-[10px] uppercase text-slate-500">Milestone status</p>
								<p className="mt-1 text-lg font-black text-emerald-400">{activeMilestone?.title || "None"}</p>
							</div>
						</div>
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
					<div className="space-y-3">
						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
								<Sparkles className="h-3.5 w-3.5" /> Milestones
							</div>
							<div className="mt-4 space-y-3">
								{milestones.map((milestone, index) => (
									<button
										key={milestone.milestone_id}
										onClick={() => startMilestone(milestone.milestone_id)}
										className={`w-full rounded-xl border p-4 text-left ${activeMilestone?.milestone_id === milestone.milestone_id ? "border-emerald-400 bg-emerald-400/10" : "border-slate-800 bg-slate-950/60"}`}
									>
										<div className="flex items-start justify-between gap-3">
											<div className="min-w-0">
												<p className="text-[10px] uppercase tracking-[0.2em] text-slate-500">Milestone {index + 1}</p>
												<h3 className="break-words text-sm font-black text-white">{milestone.title}</h3>
											</div>
											{(() => {
												const normalized = normalizeStatus(milestone.status || milestone.completion_status);
												return <span className={`rounded-full px-2 py-1 text-[9px] font-black uppercase ${statusClass(normalized)}`}>{statusLabel(normalized)}</span>;
											})()}
										</div>
										<p className="mt-2 text-xs text-slate-400">{milestone.objective}</p>
									</button>
								))}
							</div>
						</div>
					</div>

					<div className="space-y-4">
						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Target className="h-3.5 w-3.5" /> Current milestone</div>
							{activeMilestone ? (
								<div className="mt-4 space-y-4">
									<div>
										<h3 className="text-2xl font-black text-white">{activeMilestone.title}</h3>
										<p className="mt-2 text-sm text-slate-300">{activeMilestone.description || activeMilestone.objective}</p>
										<p className="mt-2 text-xs text-slate-500">Why this matters: {activeMilestone.objective}</p>
									</div>
									<div className="grid gap-3 sm:grid-cols-2">
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Required skills</p>
											<p className="mt-1 text-sm text-slate-300">{activeMilestone.required_skills.map(titleize).join(" · ") || "None"}</p>
										</div>
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Prerequisites</p>
											<p className="mt-1 text-sm text-slate-300">{activeMilestone.prerequisites.map(titleize).join(" · ") || "None"}</p>
										</div>
									</div>
									<div className="grid gap-3 sm:grid-cols-2">
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Estimated time</p>
											<p className="mt-1 text-sm text-slate-300">{activeMilestone.estimated_minutes ? `${activeMilestone.estimated_minutes} minutes` : session?.project.estimatedTime || "Unavailable"}</p>
										</div>
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Expected outcome</p>
											<p className="mt-1 text-sm text-slate-300">{activeMilestone.expected_output}</p>
										</div>
									</div>
								</div>
							) : (
								<p className="mt-4 text-sm text-slate-500">Select a milestone to view details.</p>
							)}
						</div>

						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center justify-between gap-3">
								<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400">
									<BookOpen className="h-3.5 w-3.5" /> What you need to learn
								</div>
								<button onClick={() => setShowHints((value) => !value)} className="rounded-full border border-slate-700 px-3 py-1 text-[10px] font-black uppercase text-slate-300">
									{showHints ? "Hide Hints" : "Show Hints"}
								</button>
							</div>
							<ul className="mt-4 space-y-2 text-sm text-slate-300">
								{(activeMilestone?.learning_concepts || activeMilestone?.concepts || []).length ? (activeMilestone?.learning_concepts || activeMilestone?.concepts || []).map((item, index) => (
									<li key={`${item}-${index}`} className="flex gap-2">
										<span className="text-emerald-400">•</span>
										<span>{item}</span>
									</li>
								)) : <li className="text-slate-500">No concepts available.</li>}
							</ul>
							{showHints && activeMilestone ? (
								<div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
									<p className="text-[10px] uppercase text-slate-500">Hints</p>
									<div className="mt-3 space-y-2">
										{hintsForMilestone.length ? hintsForMilestone.map((hint, index) => (
											<p key={`${hint}-${index}`} className="text-sm text-slate-300">Hint {index + 1}: {hint}</p>
										)) : <p className="text-sm text-slate-500">No hints available.</p>}
									</div>
								</div>
							) : null}
						</div>

						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">
								<RefreshCw className="h-3.5 w-3.5" /> Ask AI Mentor
							</div>
							<p className="mt-3 text-sm text-slate-400">Ask for a hint, explanation, test idea, or debugging help. The mentor stays tied to this milestone.</p>
							<textarea
								value={mentorPrompt}
								onChange={(event) => setMentorPrompt(event.target.value)}
								className="mt-4 min-h-24 w-full rounded-xl border border-slate-800 bg-slate-950/70 px-3 py-2 text-sm text-white outline-none placeholder:text-slate-600"
								placeholder="I’m stuck. Explain this step or give me a hint."
							/>
							<div className="mt-3 flex flex-wrap gap-2">
								{["How do I start this milestone?", "Give me a hint.", "Why do I need this?", "How do I test this?"].map((prompt) => (
									<button
										key={prompt}
										type="button"
										onClick={() => setMentorPrompt(prompt)}
										className="rounded-full border border-slate-700 px-3 py-1 text-[10px] font-black uppercase text-slate-300"
									>
										{prompt}
									</button>
								))}
							</div>
						</div>

						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><ArrowRight className="h-3.5 w-3.5" /> Build this</div>
							<p className="mt-3 text-sm leading-relaxed text-slate-300">{buildProjectGuidance}</p>
							<div className="mt-4 space-y-3">
								{session?.project.projectBlueprint?.implementationTasks?.length ? session.project.projectBlueprint.implementationTasks.map((step, index) => {
									const expanded = expandedSteps.includes(index);
									return (
										<div key={`${step}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<button className="flex w-full items-center justify-between gap-3 text-left" onClick={() => toggleStep(index)}>
												<div>
													<p className="text-[10px] uppercase text-slate-500">Step {index + 1}</p>
													<p className="mt-1 text-sm font-bold text-white">{step}</p>
												</div>
												{expanded ? <ChevronUp className="h-4 w-4 text-slate-400" /> : <ChevronDown className="h-4 w-4 text-slate-400" />}
											</button>
											{expanded ? (
												<p className="mt-3 text-sm text-slate-300">{stepGuide[index]?.explanation || "Focus on the smallest working version and verify the output."}</p>
											) : null}
										</div>
									);
								}) : <p className="text-sm text-slate-500">No build guidance available.</p>}
							</div>
						</div>

						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Clock3 className="h-3.5 w-3.5" /> Checkpoint</div>
							<p className="mt-3 text-sm text-slate-300">{activeMilestone?.checkpoint || "No checkpoint available."}</p>
							<div className="mt-4 space-y-3 rounded-xl border border-dashed border-slate-700 bg-slate-950/60 p-4 text-sm text-slate-400">
								{["Dataset loads successfully", "Expected output is visible", "Evidence is written"].map((label) => (
									<label key={label} className="flex items-center gap-2">
										<input
											type="checkbox"
											checked={!!checkpointChecks[label]}
											onChange={() => toggleCheckpoint(label)}
											className="h-4 w-4 rounded border-slate-600 bg-slate-900"
										/>
										<span>{label}</span>
									</label>
								))}
								<div>
									<p className="font-bold text-white">Implementation notes</p>
									<textarea value={implementationNotes} onChange={(event) => setImplementationNotes(event.target.value)} className="mt-2 min-h-20 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white outline-none" placeholder="What did you build?" />
								</div>
								<div>
									<p className="font-bold text-white">What result did you get?</p>
									<textarea value={implementationResult} onChange={(event) => setImplementationResult(event.target.value)} className="mt-2 min-h-20 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white outline-none" placeholder="Describe the output you observed." />
								</div>
								<div>
									<p className="font-bold text-white">Relevant code</p>
									<textarea value={codeSnippet} onChange={(event) => setCodeSnippet(event.target.value)} className="mt-2 min-h-20 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white outline-none" placeholder="Paste the relevant snippet." />
								</div>
							</div>
							<div className="mt-4 flex flex-wrap gap-3">
								<button onClick={() => void completeMilestone()} disabled={completing || !activeMilestone || activeMilestone.status === "LOCKED"} className="rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 disabled:opacity-50">
									{completing ? "Completing..." : "Submit Checkpoint"}
								</button>
								<button onClick={() => void askCoach()} disabled={aiLoading} className="rounded-xl border border-slate-700 px-4 py-3 text-xs font-black uppercase text-slate-200 disabled:opacity-50">
									{aiLoading ? "Asking..." : mentorPrompt.trim() ? "Ask AI Mentor" : "Ask AI Coach"}
								</button>
								<button onClick={() => startMilestone(activeMilestone?.milestone_id || "")} className="rounded-xl border border-slate-700 px-4 py-3 text-xs font-black uppercase text-slate-200">
									Start Milestone
								</button>
							</div>
							{message ? <p className="mt-3 text-sm text-slate-300">{message}</p> : null}
							{coachReply ? <p className="mt-3 whitespace-pre-wrap rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300">{coachReply}</p> : null}
						</div>
					</div>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="grid gap-3 md:grid-cols-3">
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
							<p className="text-[10px] uppercase text-slate-500">Next best action</p>
							<p className="mt-1 text-sm text-slate-300">{nextBestAction}</p>
						</div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
							<p className="text-[10px] uppercase text-slate-500">Learner level</p>
							<p className="mt-1 text-sm text-slate-300">{currentSkillProfile?.status || "Unknown"} · {currentSkillProfile?.proficiency ?? 0}%</p>
						</div>
						<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
							<p className="text-[10px] uppercase text-slate-500">Project status</p>
							<p className="mt-1 text-sm text-slate-300">{session?.project.project_theme || "Unspecified"} · {completedCount === milestones.length && milestones.length > 0 ? "Completed" : "In progress"}</p>
						</div>
					</div>
					<div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-500">
						<span className="flex items-center gap-1.5"><CheckCircle2 className="h-3.5 w-3.5" /> {completedCount} completed</span>
						<span className="flex items-center gap-1.5"><Target className="h-3.5 w-3.5" /> {availableCount} available</span>
						<span className="flex items-center gap-1.5"><RefreshCw className="h-3.5 w-3.5" /> {lockedCount} locked</span>
					</div>
				</section>
			</div>
		</AppShell>
	);
}
