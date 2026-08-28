"use client";

import { useEffect, useState } from "react";
import { ArrowRight, BarChart3, BookOpen, CircleAlert, Compass, Flame, Medal, RefreshCw, Sparkles, Target, TrendingUp } from "lucide-react";
import { AppShell } from "../components/app-shell";

type Profile = {
	target_role?: string;
	user_skills?: Record<string, { proficiency?: number; status?: string; confidence?: string; evidence?: unknown[]; last_test_score?: number }>;
	assessmentResults?: Array<{ skillId: string; answer: string; correct: boolean }>;
	practiceHistory?: Array<{ skillId: string; question: string; answer: string; correct: boolean; difficulty: string; timestamp: string }>;
	learningInsight?: string;
};

type SummaryResponse = {
	career: string;
	readiness: {
		score: number;
		completedSkills: number;
		totalSkills: number;
		biggestGap: string | null;
		biggestBlocker: string | null;
		nextAction: string | null;
	};
	skillGrowth: Record<string, { current: number; target: number; skills: number; average: number; target_average: number }>;
	weeklyActivity: { learningSessions: number; practice: number; projects: number; assessments: number };
	milestones: { completed: number; available: number; locked: number };
	assessments: Array<{ skillId: string; answer: string; correct: boolean }>;
	projects: string[];
	nextBestAction?: { title?: string; reason?: string } | null;
	biggestGap?: string | null;
	biggestBlocker?: string | null;
	nextAction?: string | null;
};

const BACKEND_URL = "";

const categories = ["Programming", "Backend", "Database", "AI/ML", "Cloud", "DevOps", "Tools"];

function titleize(value?: string | null) {
	return value ? value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase()) : "Unavailable";
}

export default function ProgressPage() {
	const [profile, setProfile] = useState<Profile | null>(null);
	const [summary, setSummary] = useState<SummaryResponse | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState("");
	const [trend, setTrend] = useState<number | null>(null);

	const loadSummary = async () => {
		setLoading(true);
		setError("");
		try {
			const savedProfile = JSON.parse(window.localStorage.getItem("pathmind_profile") || "null") as Profile | null;
			const savedAnalysis = JSON.parse(window.localStorage.getItem("pathmind_analysis") || "null") as { matched_career_id?: string } | null;
			const targetRole = savedProfile?.target_role || savedAnalysis?.matched_career_id || "backend_ai_developer";
			const currentSkills = savedProfile?.user_skills || {};
			setProfile(savedProfile || { target_role: targetRole, user_skills: currentSkills });

			const response = await fetch(`${BACKEND_URL}/api/progress/summary`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({
					target_role: targetRole,
					current_skills: currentSkills,
					daily_learning_minutes: savedProfile?.practiceHistory?.length ? 60 : 0,
					assessment_results: savedProfile?.assessmentResults || [],
					practice_history: savedProfile?.practiceHistory || [],
				}),
			});
			if (!response.ok) throw new Error("Could not load progress summary.");
			const data = (await response.json()) as SummaryResponse;
			setSummary(data);
			const snapshot = JSON.parse(window.localStorage.getItem("pathmind_progress_last") || "null") as { score?: number } | null;
			if (snapshot?.score !== undefined) {
				setTrend(data.readiness.score - snapshot.score);
			} else {
				setTrend(null);
			}
			window.localStorage.setItem("pathmind_progress_last", JSON.stringify({ score: data.readiness.score, updatedAt: new Date().toISOString() }));
		} catch (cause) {
			setError(cause instanceof Error ? cause.message : "Could not load progress summary.");
		} finally {
			setLoading(false);
		}
	};

	useEffect(() => {
		void loadSummary();
	}, []);

	const skillGrowth = summary?.skillGrowth || {};
	const weeklyActivity = summary?.weeklyActivity || { learningSessions: 0, practice: 0, projects: 0, assessments: 0 };
	const milestones = summary?.milestones || { completed: 0, available: 0, locked: 0 };
	const readiness = summary?.readiness?.score ?? 0;
	const hasActivity = weeklyActivity.learningSessions + weeklyActivity.practice + weeklyActivity.projects + weeklyActivity.assessments > 0;

	if (loading) {
		return (
			<AppShell title="Progress">
				<div className="grid gap-5 lg:grid-cols-[1fr_0.95fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-36 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-64 animate-pulse rounded-2xl bg-slate-800/70" />
					</div>
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
						<div className="h-4 w-40 animate-pulse rounded bg-slate-800" />
						<div className="mt-4 h-80 animate-pulse rounded-2xl bg-slate-800/70" />
					</div>
				</div>
			</AppShell>
		);
	}

	if (error) {
		return (
			<AppShell title="Progress">
				<div className="mx-auto max-w-xl rounded-2xl border border-slate-800 bg-slate-900/70 p-6 text-center">
					<CircleAlert className="mx-auto h-10 w-10 text-rose-400" />
					<h2 className="mt-4 text-2xl font-black text-white">Progress unavailable</h2>
					<p className="mt-2 text-sm text-slate-400">{error}</p>
					<button onClick={() => void loadSummary()} className="mt-6 inline-flex items-center gap-2 rounded-xl bg-emerald-400 px-4 py-3 text-xs font-black uppercase tracking-wide text-slate-950">
						<RefreshCw className="h-4 w-4" /> Retry
					</button>
				</div>
			</AppShell>
		);
	}

	return (
		<AppShell title="Progress">
			<div className="space-y-5">
				<section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
					<div className="rounded-2xl border border-slate-800 bg-[linear-gradient(135deg,rgba(15,23,42,0.96),rgba(10,16,30,0.92))] p-6">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Sparkles className="h-3.5 w-3.5" /> Career readiness</div>
						<h2 className="mt-3 text-3xl font-black text-white">{summary?.career || titleize(profile?.target_role)}</h2>
						<p className="mt-2 text-sm text-slate-400">Weighted by critical skills, prerequisites, evidence, projects, and assessments.</p>
						<div className="mt-6 flex items-end gap-3">
							<p className="text-5xl font-black text-emerald-400">{readiness}%</p>
							<p className="pb-1 text-sm text-slate-400">Career Ready</p>
						</div>
						<div className="mt-5 h-2 rounded-full bg-slate-800">
							<div className="h-2 rounded-full bg-emerald-400" style={{ width: `${readiness}%` }} />
						</div>
						<div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-400">
							<span className="rounded-full border border-slate-800 px-3 py-2">Biggest gap: {titleize(summary?.biggestGap)}</span>
							<span className="rounded-full border border-slate-800 px-3 py-2">Biggest blocker: {titleize(summary?.biggestBlocker)}</span>
							<span className="rounded-full border border-slate-800 px-3 py-2">Next action: {summary?.readiness?.nextAction || "Unavailable"}</span>
						</div>
						{trend !== null ? <p className="mt-4 text-sm font-bold text-emerald-400">{trend >= 0 ? "+" : ""}{trend}% this month</p> : <p className="mt-4 text-sm text-slate-500">Monthly trend unavailable until a previous snapshot exists.</p>}
					</div>

					<div className="grid gap-4">
						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><BarChart3 className="h-3.5 w-3.5" /> Skill growth</div>
							<div className="mt-4 space-y-3">
								{categories.map((category) => {
									const bucket = skillGrowth[category];
									const current = bucket?.average ?? 0;
									const target = bucket?.target_average ?? 0;
									const width = target ? Math.min(100, Math.round((current / target) * 100)) : current;
									return (
										<div key={category}>
											<div className="mb-1 flex items-center justify-between text-xs">
												<span className="font-bold text-slate-300">{category}</span>
												<span className="text-slate-500">{bucket ? `${current}% / ${target}%` : "No data"}</span>
											</div>
											<div className="h-2 rounded-full bg-slate-800">
												<div className="h-2 rounded-full bg-indigo-400" style={{ width: `${bucket ? width : 0}%` }} />
											</div>
										</div>
									);
								})}
							</div>
						</div>

						<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
							<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><TrendingUp className="h-3.5 w-3.5" /> Weekly activity</div>
							<div className="mt-4 grid grid-cols-2 gap-3">
								{[
									["Learning sessions", weeklyActivity.learningSessions],
									["Practice", weeklyActivity.practice],
									["Projects", weeklyActivity.projects],
									["Assessments", weeklyActivity.assessments],
								].map(([label, value]) => (
									<div key={label as string} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
										<p className="text-[10px] uppercase text-slate-500">{label as string}</p>
										<p className="mt-1 text-2xl font-black text-white">{value as number}</p>
									</div>
								))}
							</div>
						</div>
					</div>
				</section>

				<section className="grid gap-5 lg:grid-cols-[0.95fr_1.05fr]">
					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Medal className="h-3.5 w-3.5" /> Milestones</div>
						<div className="mt-4 grid grid-cols-3 gap-3">
							<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Completed</p><p className="mt-1 text-2xl font-black text-emerald-400">{milestones.completed}</p></div>
							<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Available</p><p className="mt-1 text-2xl font-black text-indigo-400">{milestones.available}</p></div>
							<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4"><p className="text-[10px] uppercase text-slate-500">Locked</p><p className="mt-1 text-2xl font-black text-slate-300">{milestones.locked}</p></div>
						</div>
					</div>

					<div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-400"><BookOpen className="h-3.5 w-3.5" /> AI insights</div>
						<p className="mt-3 text-sm leading-relaxed text-slate-300">{profile?.learningInsight || summary?.nextBestAction?.reason || "No AI insight is available yet."}</p>
						<div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-4">
							<p className="text-[10px] uppercase text-slate-500">Next action</p>
							<p className="mt-1 text-sm font-bold text-white">{summary?.nextAction || summary?.readiness?.nextAction || "Unavailable"}</p>
							{summary?.nextBestAction?.title ? <p className="mt-2 text-sm text-slate-400">Previously recommended: {summary.nextBestAction.title}</p> : null}
						</div>
						<div className="mt-4 flex flex-wrap gap-2">
							{summary?.nextAction ? <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-2 text-xs text-emerald-300">{summary.nextAction}</span> : null}
							{summary?.biggestBlocker ? <span className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-2 text-xs text-amber-300">Blocker: {summary.biggestBlocker}</span> : null}
						</div>
					</div>
				</section>

				<section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
					<div className="flex items-center justify-between gap-3">
						<div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-400"><Flame className="h-3.5 w-3.5" /> Session activity</div>
						<div className="text-xs text-slate-500">{hasActivity ? "Actual activity recorded" : "No activity recorded yet"}</div>
					</div>
					<div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
						{[
							{ label: "Learning sessions", value: weeklyActivity.learningSessions },
							{ label: "Practice entries", value: weeklyActivity.practice },
							{ label: "Projects", value: weeklyActivity.projects },
							{ label: "Assessments", value: weeklyActivity.assessments },
						].map((item) => (
							<div key={item.label} className="rounded-xl border border-slate-800 bg-slate-950/60 p-4">
								<p className="text-[10px] uppercase text-slate-500">{item.label}</p>
								<p className="mt-1 text-2xl font-black text-white">{item.value}</p>
							</div>
						))}
					</div>
					{!hasActivity ? <p className="mt-4 text-sm text-slate-500">No activity has been recorded in the current session yet.</p> : null}
				</section>
			</div>
		</AppShell>
	);
}
