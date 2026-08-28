"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BookOpen, CircleAlert, Clock3, Layers3, Lock, Medal, Sparkles, Target, X } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: unknown[] }>;
};

type ResourceItem = {
	title: string;
	type: "Video" | "Documentation" | "Article" | "Practice" | "Project" | string;
	skill: string;
	difficulty: string;
	estimatedTime: string;
	reason: string;
	url?: string | null;
	contentReference?: unknown;
};

type ProjectItem = {
	title: string;
	goal: string;
	skills: string[];
	prerequisites: string[];
	difficulty: string;
	estimatedTime: string;
	expectedOutput: string;
	evaluationCriteria: string[];
};

type SkillBucket = {
	skillId: string;
	title: string;
	status: string;
	proficiency: number;
	resources: ResourceItem[];
	project: ProjectItem;
	weakAreas: string[];
};

type ResourcesResponse = {
	career: string;
	resources: SkillBucket[];
	projects: SkillBucket[];
};

const BACKEND_URL = "";

function titleize(value?: string | null) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Unavailable";
}

function projectStage(status: string, proficiency: number) {
	if (status === "LOCKED" || proficiency < 35) return "locked";
	if (status === "COMPLETED") return "completed";
	return "available";
}

export default function ResourcesPage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [summary, setSummary] = useState<ResourcesResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [selectedProject, setSelectedProject] = useState<SkillBucket | null>(null);
	const [projectScore, setProjectScore] = useState(80);
	const [projectEvidence, setProjectEvidence] = useState("");
	const [projectMessage, setProjectMessage] = useState("");
	const [completing, setCompleting] = useState(false);

	const loadResources = async () => {
		setLoading(true);
		setError("");
		try {
			const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
			const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string } | null;
			const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "backend_ai_developer";
			const currentSkills = savedProfile?.user_skills || {};
			setProfile(savedProfile || { target_role: targetRole, user_skills: currentSkills });

			const response = await fetch(`${BACKEND_URL}/api/resources/summary`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ target_role: targetRole, current_skills: currentSkills }),
			});
			if (!response.ok) throw new Error("Could not load resources.");
			const data = (await response.json()) as ResourcesResponse;
			setSummary(data);
			setSelectedProject(data.projects.find((item) => item.status !== "LOCKED") || data.projects[0] || null);
		} catch (cause) {
			setError(cause instanceof Error ? cause.message : "Could not load resources.");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		void loadResources();
	}, []);

	const visibleResources = useMemo(() => summary?.resources || [], [summary]);
	const visibleProjects = useMemo(() => summary?.projects || [], [summary]);

	const completeProject = async () => {
		if (!selectedProject || !profile?.target_role) return;
		setCompleting(true);
		setProjectMessage("");
		try {
			const response = await fetch(`${BACKEND_URL}/api/project/complete`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					target_role: profile.target_role,
					skill_id: selectedProject.skillId,
					project_title: selectedProject.project.title,
					score: projectScore,
					user_skills: profile.user_skills || {},
					evidence_summary: projectEvidence,
				}),
			});
			if (!response.ok) throw new Error("Project evaluation failed.");
			const data = (await response.json()) as { updated_skills?: Profile["user_skills"]; evidence?: unknown[]; verification_status?: string };
			if (!data.updated_skills) throw new Error("Project response was invalid.");
			const nextProfile: Profile = { ...(profile || {}), user_skills: data.updated_skills };
			setProfile(nextProfile);
			window.localStorage.setItem("pathmind_profile", JSON.stringify(nextProfile));
			setProjectMessage(data.verification_status || "Project recorded.");
		} catch (cause) {
			setProjectMessage(cause instanceof Error ? cause.message : "Project evaluation failed.");
		} finally {
			setCompleting(false);
		}
	};

	if (loading) {
		return (
			<AppShell title="Resources">
				<div className="grid gap-5 lg:grid-cols-[1fr_0.95fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-36 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-72 animate-pulse rounded-2xl bg-slate-800/70" />
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
			<AppShell title="Resources">
				<div className="mx-auto max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Resources unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
				</div>
			</AppShell>
		);
	}

	return (
		<AppShell title="Resources">
			<div className="space-y-5">
				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Contextual resources</div>
					<h2 className="mt-3 text-3xl font-black text-white">{summary?.career || titleize(profile?.target_role)}</h2>
					<p className="mt-2 text-sm text-slate-400">Every resource belongs to a skill or milestone and includes a reason for recommendation.</p>
				</section>

				<section className="grid gap-5 lg:grid-cols-[1fr_0.95fr]">
					<div className="space-y-4">
						{visibleResources.map((bucket) => (
							<div key={bucket.skillId} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
								<div className="flex items-center justify-between gap-3">
									<div>
										<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">{bucket.title}</p>
										<h3 className="mt-2 text-xl font-black text-white">{bucket.skillId.replaceAll("_", " ")}</h3>
									</div>
									<div className="rounded-full border border-slate-700 px-2.5 py-1 text-[10px] font-bold uppercase text-slate-400">{bucket.status}</div>
								</div>
								<div className="mt-4 space-y-3">
									{bucket.resources.map((resource, index) => (
										<div key={`${resource.title}-${index}`} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<div className="flex items-start justify-between gap-3">
												<div className="min-w-0">
													<p className="break-words text-sm font-bold leading-tight text-white">{resource.title}</p>
													<p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">{resource.type} · {resource.difficulty}</p>
												</div>
												{resource.url ? <a href={resource.url} target="_blank" rel="noreferrer" className="text-xs font-bold text-emerald-400">Open</a> : <span className="text-xs text-slate-500">Reference</span>}
											</div>
											<p className="mt-3 text-sm text-slate-300">Why this is recommended: {resource.reason}</p>
											<p className="mt-2 text-xs text-slate-500">Estimated time: {resource.estimatedTime}</p>
										</div>
									))}
									{!bucket.resources.length ? <p className="text-sm text-slate-500">No resources available for this skill.</p> : null}
								</div>
							</div>
						))}
					</div>

					<div className="space-y-4">
						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Target className="h-3.5 w-3.5" /> Adaptive projects</div>
							<div className="mt-4 space-y-3">
								{visibleProjects.map((bucket) => {
									const stage = projectStage(bucket.status, bucket.proficiency);
									return (
										<button key={bucket.skillId} onClick={() => setSelectedProject(bucket)} className={`w-full rounded-xl border p-4 text-left ${selectedProject?.skillId === bucket.skillId ? "border-emerald-400 bg-emerald-400/10" : "border-slate-800 bg-slate-950/60"}`}>
											<div className="flex items-center justify-between gap-3">
												<div className="min-w-0">
													<p className="break-words text-sm font-bold leading-tight text-white">{bucket.project.title}</p>
													<p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">{bucket.title}</p>
												</div>
												<div className={`rounded-full border px-2 py-1 text-[9px] font-bold uppercase ${stage === "locked" ? "border-slate-700 text-slate-400" : stage === "completed" ? "border-emerald-400 bg-emerald-400 text-slate-950" : "border-indigo-400 bg-indigo-400 text-white"}`}>
													{stage}
												</div>
											</div>
											<p className="mt-3 text-sm text-slate-300">{bucket.project.goal}</p>
											<p className="mt-2 text-xs text-slate-500">Difficulty: {bucket.project.difficulty} · {bucket.project.estimatedTime}</p>
										</button>
									);
								})}
							</div>
						</div>

						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><Layers3 className="h-3.5 w-3.5" /> Project detail</div>
							{selectedProject ? (
								<div className="mt-4 space-y-4">
									<h3 className="text-2xl font-black text-white">{selectedProject.project.title}</h3>
									<p className="text-sm text-slate-400">{selectedProject.project.goal}</p>
									<div className="grid gap-3 sm:grid-cols-2">
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Skills</p>
											<p className="mt-1 text-sm text-slate-300">{selectedProject.project.skills.map(titleize).join(", ")}</p>
										</div>
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Prerequisites</p>
											<p className="mt-1 text-sm text-slate-300">{selectedProject.project.prerequisites.length ? selectedProject.project.prerequisites.map(titleize).join(", ") : "None"}</p>
										</div>
									</div>
									<div className="grid gap-3 sm:grid-cols-2">
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Expected output</p>
											<p className="mt-1 text-sm text-slate-300">{selectedProject.project.expectedOutput}</p>
										</div>
										<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Evaluation</p>
											<p className="mt-1 text-sm text-slate-300">{selectedProject.project.evaluationCriteria.join("; ")}</p>
										</div>
									</div>
									<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
										<p className="text-[10px] uppercase text-slate-500">Completion evidence</p>
										<p className="mt-1 text-sm text-slate-300">Project completion will only create evidence after evaluation through the completion endpoint.</p>
									</div>
									<div className="grid gap-3 sm:grid-cols-[0.8fr_1.2fr]">
										<label className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Score</p>
											<input type="range" min="0" max="100" value={projectScore} onChange={(event) => setProjectScore(Number(event.target.value))} className="mt-3 w-full" />
											<p className="mt-2 text-sm font-bold text-white">{projectScore}%</p>
										</label>
										<label className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
											<p className="text-[10px] uppercase text-slate-500">Evidence summary</p>
											<textarea value={projectEvidence} onChange={(event) => setProjectEvidence(event.target.value)} className="mt-3 min-h-24 w-full rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-white outline-none" placeholder="Describe what the learner built..." />
										</label>
									</div>
									<button onClick={() => void completeProject()} disabled={completing} className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950 disabled:opacity-50">
										{completing ? "Evaluating..." : "Submit project evaluation"}
									</button>
									{projectMessage ? <p className="text-sm text-slate-300">{projectMessage}</p> : null}
								</div>
							) : (
								<div className="py-12 text-center text-sm text-slate-500">Select a project to see its details.</div>
							)}
						</div>
					</div>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
						<span className="flex items-center gap-1.5"><Medal className="h-3.5 w-3.5" /> Projects appear at the right roadmap stage</span>
						<span className="flex items-center gap-1.5"><Lock className="h-3.5 w-3.5" /> Locked projects remain unavailable until prerequisites are met</span>
						<span className="flex items-center gap-1.5"><Clock3 className="h-3.5 w-3.5" /> Evidence is recorded only after evaluation</span>
					</div>
				</section>
			</div>
		</AppShell>
	);
}


