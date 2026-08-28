"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, BrainCircuit, CalendarDays, CheckCircle2, Compass, Sparkles, Target, TrendingUp, Zap } from "lucide-react";
import { AppShell } from "../components/app-shell";

type RoadmapItem = {
	id: string;
	skillId: string;
	title: string;
	type: "LEARN" | "PRACTICE" | "PROJECT" | "ASSESSMENT" | "REVIEW";
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

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string }>;
	dailyLearningMinutes?: number;
	daily_learning_minutes?: number;
	learningPreferences?: string[];
	learningInsight?: string;
	roadmapChanged?: boolean;
};

const careerLabel = (targetRole?: string) => targetRole?.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) || "Your career goal";

const BACKEND_URL = "";

export default function HomePage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [roadmap, setRoadmap] = useState<RoadmapData | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");

	useEffect(() => {
		const load = async () => {
			setLoading(true);
			setError("");
			try {
				const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
				const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string; careerTitle?: string } | null;
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
						assessment_results: [],
					}),
				});
				if (!response.ok) throw new Error("We could not load your route.");
				const data = (await response.json()) as RoadmapData;
				if (!Array.isArray(data.items) || !data.nextBestAction || typeof data.estimatedDuration !== "string") throw new Error("Roadmap data was invalid.");
				setRoadmap(data);
			} catch (cause) {
				setError(cause instanceof Error ? cause.message : "We could not load your route.");
			} finally {
				setLoading(false);
			}
		};
		void load();
	}, []);

	const careerGoal = careerLabel(profile?.target_role);
	const completedCount = roadmap?.items.filter((item) => item.status === "COMPLETED").length || 0;
	const currentCount = roadmap?.items.filter((item) => ["CURRENT", "AVAILABLE", "NEEDS_ATTENTION"].includes(item.status)).length || 0;
	const lockedCount = roadmap?.items.filter((item) => item.status === "LOCKED").length || 0;
	const readiness = roadmap?.items.length ? Math.round((completedCount / roadmap.items.length) * 100) : 0;
	const weeklyActivity = useMemo(() => {
		const minutes = profile?.dailyLearningMinutes || profile?.daily_learning_minutes || 60;
		const sessions = Math.max(1, Math.round((minutes * 7) / 45));
		return `${sessions} focused sessions`;
	}, [profile]);

	if (loading) {
		return (
			<AppShell title="Home">
				<section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-28 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-8 w-64 animate-pulse rounded bg-slate-800" />
						<div className="mt-6 h-28 animate-pulse rounded-2xl bg-slate-800/70" />
					</div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-40 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-24 animate-pulse rounded-2xl bg-slate-800/70" />
					</div>
				</section>
			</AppShell>
		);
	}

	if (error) {
		return (
			<AppShell title="Home">
				<section className="mx-auto max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<Compass className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Home is unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
				</section>
			</AppShell>
		);
	}

	const nextAction = roadmap?.nextBestAction;
	const insight = profile?.learningInsight || nextAction?.reason || "Your learning path is already adapting around the biggest blocker in front of you.";

	return (
		<AppShell title="Home">
			<div className="space-y-5">
				<section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
					<div className="rounded-2xl border border-emerald-500/20 bg-[radial-gradient(circle_at_top_left,_rgba(82,224,179,0.12),_transparent_35%),linear-gradient(135deg,rgba(15,23,42,0.96),rgba(9,17,31,0.92))] p-6">
						<p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.22em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Hello again</p>
						<h2 className="mt-3 text-3xl font-black tracking-tight text-white sm:text-4xl">{careerGoal}</h2>
						<p className="mt-3 text-sm text-slate-400">We keep your route focused on the skills that unlock the next milestone, not a random course list.</p>
						<div className="mt-6 flex flex-wrap gap-3">
							<div className="rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3"><p className="text-[10px] uppercase text-slate-500">Career readiness</p><p className="mt-1 text-2xl font-black text-emerald-400">{readiness}%</p></div>
							<div className="rounded-xl border border-slate-800 bg-slate-950/70 px-4 py-3"><p className="text-[10px] uppercase text-slate-500">Journey summary</p><p className="mt-1 text-sm font-bold text-white">{roadmap?.estimatedDuration || "Journey loading"}</p></div>
						</div>
					</div>
					<div className="grid gap-4">
						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Target className="h-3.5 w-3.5" /> Next best action</div>
							<h3 className="mt-3 text-2xl font-black text-white">{nextAction?.title || "Waiting for your roadmap"}</h3>
							<p className="mt-2 text-sm leading-relaxed text-slate-400">{insight}</p>
							<div className="mt-5 flex flex-wrap items-center gap-3">
								{nextAction ? <Link href="/path" className="inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950"><ArrowRight className="h-4 w-4" /> Start now</Link> : null}
							</div>
						</div>
						<div className="grid gap-4 sm:grid-cols-3">
							<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><p className="text-[10px] uppercase text-slate-500">Completed</p><p className="mt-2 text-2xl font-black text-emerald-400">{completedCount}</p></div>
							<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><p className="text-[10px] uppercase text-slate-500">In motion</p><p className="mt-2 text-2xl font-black text-indigo-400">{currentCount}</p></div>
							<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4"><p className="text-[10px] uppercase text-slate-500">Locked</p><p className="mt-2 text-2xl font-black text-slate-300">{lockedCount}</p></div>
						</div>
					</div>
				</section>

				<section className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><BrainCircuit className="h-3.5 w-3.5" /> AI learning insight</div>
						<p className="mt-3 text-sm leading-relaxed text-slate-300">{nextAction?.reason || "Your roadmap will surface the best next step as soon as the backend path is available."}</p>
						{profile?.roadmapChanged ? <p className="mt-3 text-xs font-bold text-emerald-400">Your roadmap changed after new evidence was recorded.</p> : null}
					</div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><CalendarDays className="h-3.5 w-3.5" /> Weekly activity</div>
						<p className="mt-3 text-3xl font-black text-white">{weeklyActivity}</p>
						<p className="mt-2 text-sm text-slate-400">Keep a short, repeatable cadence. The route will continue to adapt as you verify skills.</p>
					</div>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><TrendingUp className="h-3.5 w-3.5" /> Career readiness</div>
					<div className="mt-4 h-2 rounded-full bg-slate-800">
						<div className="h-2 rounded-full bg-emerald-400" style={{ width: `${readiness}%` }} />
					</div>
					<p className="mt-3 text-xs text-slate-500">{roadmap?.items.length || 0} roadmap nodes tracked from the live backend route.</p>
				</section>
			</div>
		</AppShell>
	);
}
