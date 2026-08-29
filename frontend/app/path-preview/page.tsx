"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowRight, Compass, Sparkles, Target } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string }>;
	dailyLearningMinutes?: number;
	daily_learning_minutes?: number;
	learningPreferences?: string[];
	assessmentResults?: unknown[];
	interest?: string;
};

type RoadmapItem = {
	id: string;
	skillId: string;
	title: string;
	type: string;
	reason: string;
	status: string;
	estimatedTime: string;
};

type RoadmapData = {
	items: RoadmapItem[];
	nextBestAction: RoadmapItem | null;
	estimatedDuration: string;
	validation: { valid: boolean; errors: string[] };
};

type ProjectSummary = { projects?: Array<{ project?: { title?: string; project_theme?: string } }> };

const BACKEND_URL = "";

function titleize(value?: string | null) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Your career goal";
}

export default function PathPreviewPage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [analysis, setAnalysis] = useState<{ matched_career_id?: string; careerTitle?: string; goal?: string } | null>(null);
	const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [projectTitle, setProjectTitle] = useState("");

	useEffect(() => {
		const load = async () => {
			setLoading(true);
			setError("");
			try {
				const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
				const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as typeof analysis;
				const savedOnboarding = JSON.parse(window.localStorage.getItem("pathmind_onboarding") || "null") as { goal?: string } | null;
				const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "";
				if (!targetRole) throw new Error("Start with a career goal before opening the path preview.");

				setProfile(savedProfile || { target_role: targetRole, user_skills: {} });
				setAnalysis(savedAnalysis || { goal: savedOnboarding?.goal, matched_career_id: targetRole, careerTitle: titleize(targetRole) });
				const interest = savedProfile?.interest || "";

				const response = await fetch(`${BACKEND_URL}/api/generate-path`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({
						user_id: "pathmind-local-user",
						target_role: targetRole,
						current_skills: savedProfile?.user_skills || {},
						hours_per_week: Math.max(1, Math.round((savedProfile?.dailyLearningMinutes || savedProfile?.daily_learning_minutes || 60) * 7 / 60)),
						learning_style: savedProfile?.learningPreferences?.join(", ") || "Prefer Videos",
					}),
				});
				if (!response.ok) throw new Error("We could not preview your route.");
				const raw = (await response.json()) as { path?: Array<Record<string, unknown>>; next_action?: Record<string, unknown>; validation?: RoadmapData["validation"] };
				const data: RoadmapData = {
					items: (raw.path || []).map((item) => ({ id: String(item.id || ""), skillId: String(item.skill || ""), title: String(item.title || ""), type: "LEARN", reason: String(item.why_recommended || ""), status: String(item.status || ""), estimatedTime: `${item.estimated_hours || 0} hours` })),
					nextBestAction: raw.next_action ? { id: String(raw.next_action.skill_id || ""), skillId: String(raw.next_action.skill_id || ""), title: String(raw.next_action.title || ""), type: "LEARN", reason: String(raw.next_action.reason || ""), status: String(raw.next_action.status || ""), estimatedTime: `${raw.next_action.estimated_hours || 0} hours` } : null,
					estimatedDuration: "Adaptive route",
					validation: raw.validation || { valid: true, errors: [] },
				};
				if (!data.items.length || !data.nextBestAction) throw new Error("Roadmap preview was invalid.");
				setRoadmap(data);

				const projectResponse = await fetch(`${BACKEND_URL}/api/resources/summary`, {
					method: "POST",
					headers: { "Content-Type": "application/json" },
					body: JSON.stringify({ target_role: targetRole, current_skills: savedProfile?.user_skills || {}, interest }),
				});
				if (projectResponse.ok) {
					const projectData = (await projectResponse.json()) as ProjectSummary;
					const normalizedInterest = interest.toLowerCase();
					const selected = (projectData.projects || []).find((item) => {
						const title = item.project?.title?.toLowerCase() || "";
						const theme = item.project?.project_theme?.toLowerCase() || "";
						return normalizedInterest && (title.includes(normalizedInterest) || theme.includes(normalizedInterest) || (normalizedInterest.includes("cricket") && title.includes("ipl")));
					}) || (projectData.projects || []).find((item) => item.project?.title);
					const title = selected?.project?.title || "";
					setProjectTitle(title);
					if (title) window.localStorage.setItem("pathmind_project_title", title);
				}
			} catch (cause) {
				setError(cause instanceof Error ? cause.message : "We could not preview your route.");
			} finally {
				setLoading(false);
			}
		};
		void load();
	}, []);

	if (loading) {
		return (
			<AppShell title="Your path preview">
				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-8">
					<div className="h-4 w-28 animate-pulse rounded bg-slate-800" />
					<div className="mt-4 h-8 w-64 animate-pulse rounded bg-slate-800" />
				</section>
			</AppShell>
		);
	}

	if (error || !roadmap) {
		return (
			<AppShell title="Your path preview">
				<section className="mx-auto max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<Compass className="mx-auto h-10 w-10 text-rose-400" />
					<h1 className="mt-4 text-2xl font-black text-white">Path preview unavailable</h1>
					<p className="mt-2 text-sm text-slate-400">{error || "We could not load your route preview."}</p>
					<Link href="/analysis" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">
						Review analysis <ArrowRight className="h-4 w-4" />
					</Link>
				</section>
			</AppShell>
		);
	}

	const careerTitle = analysis?.careerTitle || titleize(profile?.target_role);
	const nextAction = roadmap.nextBestAction;

	return (
		<AppShell title="Your path preview">
			<div className="space-y-5">
				<section className="rounded-2xl border border-emerald-500/20 bg-[radial-gradient(circle_at_top_left,_rgba(82,224,179,0.12),_transparent_35%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(9,17,31,0.92))] p-6">
					<p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Path preview</p>
					<h1 className="mt-3 text-3xl font-black text-white">Your first route for {careerTitle}</h1>
					<p className="mt-3 text-sm text-slate-400">This preview uses your active learner state, including assessment evidence, to show the next route before you continue.</p>
				</section>

				<section className="grid gap-4 lg:grid-cols-[1fr_0.9fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Target className="h-3.5 w-3.5" /> Next best action</div>
						<h2 className="mt-3 text-2xl font-black text-white">{nextAction?.title || "Route ready"}</h2>
						<p className="mt-2 text-sm leading-relaxed text-slate-400">{nextAction?.reason || "Your roadmap preview is ready."}</p>
						{projectTitle ? <p className="mt-4 text-sm font-bold text-emerald-300">Project: {projectTitle}</p> : null}
						<p className="mt-5 text-xs text-slate-500">{roadmap.estimatedDuration}</p>
					</div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400">Roadmap status</p>
						<p className="mt-3 text-3xl font-black text-white">{roadmap.items.length} nodes</p>
						<p className="mt-2 text-sm text-slate-400">{roadmap.validation.valid ? "The route is validated." : roadmap.validation.errors.join(" · ") || "The route needs review."}</p>
						<Link href="/home" className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase text-slate-950">
							Continue to Home <ArrowRight className="h-4 w-4" />
						</Link>
					</div>
				</section>
			</div>
		</AppShell>
	);
}
